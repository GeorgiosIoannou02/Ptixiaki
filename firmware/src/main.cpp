#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <MQTT.h>
#include <esp_sntp.h>
#include <atomic>
#include <ctime>
#include "telemetry.h"
#if __has_include("config.h")
#include "config.h"
#else
#error "Copy include/config.example.h to include/config.h and configure this device."
#endif

static_assert(SAMPLE_INTERVAL_MS >= 1000 && SAMPLE_INTERVAL_MS <= 3600000,
              "Sample interval must be 1 second to 1 hour");
static_assert(SENSOR_I2C_ADDRESS == 0 || SENSOR_I2C_ADDRESS == 0x76 || SENSOR_I2C_ADDRESS == 0x77,
              "BME280 I2C address must be 0, 0x76 or 0x77");
class BoundedWiFiClient : public WiFiClient {
 public:
  int connect(IPAddress ip, uint16_t port) override {
    return WiFiClient::connect(ip, port, 2000);
  }
  int connect(const char *host, uint16_t port) override {
    return WiFiClient::connect(host, port, 2000);
  }
};
BoundedWiFiClient transport;
MQTTClient mqtt(512);
Adafruit_BME280 bme;
std::atomic<bool> clockReady{false};
std::atomic<uint32_t> clockSyncMs{0};
uint32_t wifiAttempt = 0, mqttAttempt = 0, sensorAttempt = 0, sampleAt = 0;
uint32_t mqttBackoff = 1000;
bool sensorReady = false, configured = false;
char pending[384] = {};
time_t lastAcquisition = 0;
uint32_t observedSync = 0;
bool clockExpired = false;

void onTimeSync(struct timeval *) {
  clockSyncMs.store(millis());
  clockReady.store(true);
}

void setup() {
  Serial.begin(115200);
  configured = telemetry::validDevice(DEVICE_ID) && strlen(WIFI_SSID) &&
      strcmp(WIFI_SSID, "YOUR_2_4_GHZ_SSID") && strlen(MQTT_HOST) &&
      strlen(MQTT_TOPIC) && strlen(MQTT_TOPIC) <= 128 &&
      !strpbrk(MQTT_TOPIC, "#+") && MQTT_PORT > 0 && MQTT_PORT <= 65535 &&
      (!strlen(MQTT_PASSWORD) || strlen(MQTT_USERNAME));
  if (!configured) {
    Serial.println("Invalid configuration; check config.h. Publishing disabled.");
    return;
  }
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setTimeOut(100);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  transport.setTimeout(2);
  mqtt.begin(MQTT_HOST, MQTT_PORT, transport);
  mqtt.setOptions(30, true, 2000);
  sntp_set_time_sync_notification_cb(onTimeSync);
  configTime(0, 0, NTP_SERVER);
  sensorAttempt = millis() - 10000;
  sampleAt = millis() - SAMPLE_INTERVAL_MS;
  Serial.println("Starting one BME280; waiting for network and synchronized UTC.");
}

void loop() {
  delay(10);
  if (!configured) return;
  const uint32_t now = millis();
  if (!sensorReady && telemetry::due(now, sensorAttempt, 10000)) {
    sensorAttempt = now;
    sensorReady = SENSOR_I2C_ADDRESS ? bme.begin(SENSOR_I2C_ADDRESS, &Wire) :
        (bme.begin(0x76, &Wire) || bme.begin(0x77, &Wire));
    Serial.println(sensorReady ? "BME280 ready." : "BME280 unavailable; retry in 10 seconds.");
  }
  if (WiFi.status() != WL_CONNECTED) {
    if (mqtt.connected()) mqtt.disconnect();
    if (telemetry::due(now, wifiAttempt, 15000)) {
      wifiAttempt = now;
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      Serial.println("Retrying Wi-Fi.");
    }
    return;
  }
  // Refuse new acquisitions until SNTP succeeds; expire clock trust after 24h.
  if (!clockReady.load()) return;
  const uint32_t syncedAt = clockSyncMs.load();
  if (syncedAt != observedSync) {
    observedSync = syncedAt;
    clockExpired = false;
  }
  // Read millis after the callback timestamp to avoid unsigned underflow.
  if (telemetry::due(millis(), syncedAt, 86400000UL)) clockExpired = true;
  if (clockExpired) return; // Remains expired across wrap until another sync.
  if (!mqtt.connected()) {
    if (!telemetry::due(now, mqttAttempt, mqttBackoff)) return;
    mqttAttempt = now;
    const bool connected = strlen(MQTT_USERNAME) ?
        mqtt.connect(DEVICE_ID, MQTT_USERNAME, MQTT_PASSWORD) : mqtt.connect(DEVICE_ID);
    if (!connected) {
      mqttBackoff = min<uint32_t>(mqttBackoff * 2, 30000);
      Serial.println("MQTT unavailable; retry scheduled.");
      return;
    }
    mqttBackoff = 1000;
    Serial.println("MQTT connected.");
  }
  mqtt.loop();
  if (!mqtt.connected()) return;
  if (!pending[0] && sensorReady && telemetry::due(now, sampleAt, SAMPLE_INTERVAL_MS)) {
    sampleAt = now;
    const time_t acquired = time(nullptr);
    // Prevent duplicate timestamps after a backward clock adjustment.
    if (acquired < 1704067200 || acquired <= lastAcquisition) return;
    const float t = bme.readTemperature();
    const float h = bme.readHumidity();
    const float p = bme.readPressure();
    struct tm utc;
    gmtime_r(&acquired, &utc);
    char timestamp[24];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
    if (!telemetry::encode(pending, sizeof(pending), DEVICE_ID, timestamp, t, h, p)) {
      pending[0] = '\0';
      sensorReady = false;
      sensorAttempt = now;
      Serial.println("Invalid sensor reading; skipped, sensor will be reinitialized.");
      return;
    }
    lastAcquisition = acquired;
  }
  if (pending[0]) {
    // QoS 1 waits for PUBACK. Retain identical bytes/time on failure.
    if (mqtt.publish(MQTT_TOPIC, pending, false, 1)) {
      Serial.println("Sensor reading acknowledged by broker (not storage confirmation).");
      pending[0] = '\0';
    } else {
      mqtt.disconnect();
      transport.stop();
      mqttAttempt = millis();
      Serial.println("Publish failed; retaining one reading in RAM for retry.");
    }
  }
}

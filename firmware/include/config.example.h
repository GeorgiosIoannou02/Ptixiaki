#pragma once
// Copy to config.h (ignored by Git). Never commit actual credentials.
#define WIFI_SSID "YOUR_2_4_GHZ_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
// Reachable broker LAN address, NOT localhost or Docker service name.
#define MQTT_HOST "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""
#define MQTT_TOPIC "iot-monitor/equipment-space-01/telemetry"
#define DEVICE_ID "esp32-rack-01"
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
// Use 0 for auto-probe (0x76 then 0x77); otherwise 0x76 or 0x77.
#define SENSOR_I2C_ADDRESS 0
#define SAMPLE_INTERVAL_MS 30000UL
#define NTP_SERVER "pool.ntp.org"

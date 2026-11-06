# ESP32 + Grove BME280 firmware

PlatformIO firmware for **one ESP32-WROOM-32 development board and one Seeed
Grove BME280**, with preinstalled headers and a Grove-to-female-Dupont cable.
The `esp32dev` target is an assumption until the exact board is confirmed; it is
not appropriate for ESP32-C3/S3 boards without a board/pin configuration change.
No physical board has been flashed or verified by the automated checks.

## Wiring (power disconnected)

| Grove module signal | ESP32 |
| --- | --- |
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

Verify actual connector labels/pinout; do not infer signals from wire colors.
Use 3.3 V logic, not 5 V. Auto-probe checks 0x76 and 0x77 and accepts a BME280,
not a BMP280 (which cannot measure humidity). No second sensor is needed.

## CachyOS installation and configuration

Run these commands from the repository root in Bash (or Kitty running Bash).
Python, a compiler for host tests, curl, and a USB **data** cable are required.
If packages are missing, install `python`, `gcc`, and `curl` through CachyOS's
package manager. Use a virtual environment, not system-wide pip:

```bash
python3 -m venv firmware/.venv
firmware/.venv/bin/pip install platformio==6.1.18
cp firmware/include/config.example.h firmware/include/config.h
```

Edit `config.h` before flashing. It is ignored by Git, as are build outputs:

- `WIFI_SSID`/`WIFI_PASSWORD`: 2.4 GHz Wi-Fi credentials.
- `MQTT_HOST`: reachable broker LAN IPv4 address, **not** localhost or `mqtt`.
- `MQTT_PORT`, username/password: match the broker; the optional lab setup below
  uses 1883 and authentication. This firmware uses plain TCP, not TLS.
- `MQTT_TOPIC` and `DEVICE_ID`: must exactly match the worker's `.env` values.
  Existing installations may retain different topic values. Client ID is the
  device ID; never use the worker's `MQTT_CLIENT_ID` on the ESP32.
- SDA/SCL and optional fixed `SENSOR_I2C_ADDRESS`: match the purchased board.
- `SAMPLE_INTERVAL_MS`: 30 seconds by default, configurable from 1 second to
  1 hour. This is a development setting. If sampling slower than 120 seconds,
  increase backend `DEVICE_OFFLINE_SECONDS` accordingly.
- `NTP_SERVER`: reachable NTP service; allow DNS and UDP 123 on the lab network.

PlatformIO installs the pinned Espressif32 6.10.0 platform (Arduino ESP32
2.0.17), Adafruit BME280 2.2.4, Unified Sensor 1.1.15, BusIO 1.17.0, and
256dpi MQTT 2.5.2 dependencies from `platformio.ini` automatically. The MQTT
library supports QoS 1 publishing; no Arduino IDE or separate library installation
is needed. Firmware images contain the configured credentials: keep them private.

## Make the broker reachable from the ESP32

The default Compose setup deliberately binds MQTT to loopback; an ESP32 cannot
reach it. An **opt-in lab override** is provided, leaving normal demo behavior
unchanged. Use only a trusted, isolated LAN. Port 1883 sends credentials and data
without encryption. Restrict inbound TCP 1883 to the ESP32 with the host/network
firewall; Docker's published-port rules must be accounted for. Do not forward it
on your router. Production deployment still needs TLS, per-client ACLs and a
reviewed network configuration; this shared lab account has no topic ACLs.

Requires Compose >= 2.24.4 (`ports: !override`). Run from the repository root:

1. Preserve the existing `.env` and `data/`. Add `MQTT_BIND_IP` set to the
   computer's LAN IPv4, `MQTT_USERNAME` set to `sensorlab`, and a new
   `MQTT_PASSWORD`. Use a dedicated lab password; put the same credentials in
   `firmware/include/config.h`. Do not change initialized database credentials.
2. Create the ignored broker password file interactively. Use the same password:

   ```bash
   docker compose run --rm --no-deps --user root \
     -v "$PWD/infrastructure:/setup" mqtt \
     mosquitto_passwd -c /setup/mqtt-passwords sensorlab
   docker compose run --rm --no-deps --user root \
     -v "$PWD/infrastructure:/setup" mqtt \
     sh -c 'chown mosquitto:mosquitto /setup/mqtt-passwords && chmod 600 /setup/mqtt-passwords'
   ```

   `-c` creates/replaces the file: use it only for initial setup. The password is
   stored hashed in this file; `.env` and firmware config contain plaintext.
3. Start broker, worker, API and dashboard using the override:

   ```bash
   docker compose -f compose.yaml -f infrastructure/compose.hardware.yaml up -d --wait
   ```

   The same override must be supplied on subsequent Compose changes while using
   hardware mode. The simulator is optional and still marked synthetic. Worker
   authentication and the broker health check use the credentials from `.env`.
   The dashboard/API/database remain loopback-only. The worker must be subscribed
   before starting the ESP32. To return to the local anonymous demo, run normal
   `docker compose --profile demo up -d --wait`; remove MQTT username/password
   from firmware if using a separate anonymous broker.

## USB permissions, build, flash, monitor

Install the official PlatformIO udev rules (inspect the downloaded file first):

```bash
curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core/develop/platformio/assets/system/99-platformio-udev.rules -o /tmp/99-platformio-udev.rules
less /tmp/99-platformio-udev.rules
sudo install -m 644 /tmp/99-platformio-udev.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug/reconnect the ESP32, then identify its port:

```bash
firmware/.venv/bin/pio device list
ls -l /dev/ttyUSB0  # use the actual port, possibly /dev/ttyACM0
```

If access is still denied, check the actual port's owning group. On CachyOS/Arch
this is commonly `uucp`: `sudo usermod -aG uucp "$USER"`, then log out and back in.
Do not run PlatformIO as root or make the serial device world-writable.

```bash
firmware/.venv/bin/pio run -d firmware
firmware/.venv/bin/pio run -d firmware -t upload --upload-port /dev/ttyUSB0
firmware/.venv/bin/pio device monitor -b 115200 -p /dev/ttyUSB0
```

Close other serial monitors before uploading. If automatic bootloader entry fails,
hold BOOT while upload starts, release once connected, then press EN/reset after
upload. Verify board selection, USB data cable and port before changing drivers.

## Behavior and hardware acceptance checks

- Only actual BME280 measurements are serialized, with `synthetic: false`.
  Pressure is converted from Pa to hPa. Invalid/non-finite/out-of-range values
  are skipped and trigger sensor reinitialization every 10 seconds.
- SNTP synchronization is required before acquisition. UTC timestamps use second
  precision and `Z`; a backward clock correction pauses acquisition until time
  passes the previous reading. Clock trust expires 24 hours after the last sync.
- Wi-Fi retry attempts occur every 15 seconds; MQTT reconnect backoff grows from
  1 to 30 seconds. Network operations have bounded timeouts, but are synchronous.
- Publish is QoS 1, not retained. One unacknowledged payload is held in RAM and
  retried byte-for-byte with its original timestamp. Broker PUBACK does not prove
  database storage. Power loss loses that pending payload. While disconnected or
  waiting on a pending reading, new acquisitions are skipped: there is no durable
  backlog and gaps must be recorded in research logs.
- Serial output reports connection/sensor status without printing credentials.

After flashing, open the dashboard at http://localhost:8080 and select **Sensor**.
Check all three measurements against plausible ambient conditions and verify the
UTC timestamp and `synthetic: false` via
`/api/readings/latest?source=sensor`. Keep simulated and real data separate.

Physically test: Wi-Fi off/on; broker stop/start; wrong broker password; boot with
NTP blocked (no new readings); unplug/reconnect the sensor with power off; reboot.
Confirm recovery and distinguish gaps from successful storage. These acceptance
checks require hardware and are not implied by compilation or host tests.

## References

- [PlatformIO ESP32 board target](https://docs.platformio.org/en/stable/boards/espressif32/esp32dev.html)
- [PlatformIO Linux USB permissions](https://docs.platformio.org/en/latest/core/installation/udev-rules.html)
- [MQTT library and QoS API](https://github.com/256dpi/arduino-mqtt)
- [Adafruit BME280 driver](https://github.com/adafruit/Adafruit_BME280_Library)

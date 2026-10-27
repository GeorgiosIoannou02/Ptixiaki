# Telemetry contract

This contract supports one configured device and one BME280 module. Default topic: `ptixiaki/equipment-space-01/telemetry`; default device ID: `esp32-rack-01`. Both are configurable through environment variables.

Example **synthetic** message:

```json
{
  "device_id": "esp32-rack-01",
  "timestamp_utc": "2026-10-27T12:00:00Z",
  "temperature_c": 25.4,
  "relative_humidity_pct": 48.2,
  "pressure_hpa": 1012.7,
  "synthetic": true
}
```

`synthetic` is required. Only a future real hardware publisher should use `false`; the simulator always uses `true`. Firmware must synchronize its clock and include a timezone-aware ISO 8601 acquisition timestamp, not merely the time a server receives the message. Offset timestamps are normalized to UTC. Timestamps before the Unix epoch or more than two minutes in the future are rejected. API history selects measurements up to the current server time; readings within the allowed future clock skew become visible when their timestamps are reached.

## Validation

| Field | Unit / requirement |
| --- | --- |
| `device_id` | Exact configured single-device ID; lowercase identifier, maximum 64 characters |
| `timestamp_utc` | ISO 8601 timestamp with timezone |
| `temperature_c` | Finite JSON number, −40 to 85 °C |
| `relative_humidity_pct` | Finite JSON number, 0 to 100 %RH |
| `pressure_hpa` | Finite JSON number, 300 to 1100 hPa |
| `synthetic` | JSON boolean, explicitly supplied |

These numeric limits are broad sensor plausibility limits, **not environmental alert thresholds**. Actual alert ranges and acquisition frequency remain open project decisions. Numeric strings, booleans used as measurements, non-finite numbers, unknown fields, unknown devices, and payloads larger than 4,096 bytes are rejected.

## Delivery and storage

Publish with MQTT **QoS 1** and no retained flag. Run exactly one ingestion worker with its stable `MQTT_CLIENT_ID`. The worker uses a persistent broker session, re-subscribes on connection, and acknowledges valid input only after a synchronous InfluxDB write succeeds. Invalid input is intentionally acknowledged and discarded without logging its payload. A transient write failure retries with backoff from one to thirty seconds; broker reconnects/redelivery may occur during a prolonged outage.

InfluxDB measurement `environment` uses `device_id` and `source` (`synthetic` or `sensor`) tags. Timestamp precision is microseconds. The identity `(device_id, source, timestamp)` is idempotent: redelivery of the same point does not create another row. A conflicting payload with the same identity overwrites the previous field values; this is not an immutable raw-message archive. Avoid timestamps closer than one microsecond and preserve timestamps when retrying a reading.

Mosquitto persistence retains established subscriptions and queued QoS 1 messages across orderly restarts. Queues are bounded to 10,000 messages and persisted periodically; this is not a guarantee against every crash or extended outage. The first worker subscription must exist before broker queuing can protect it. The simulator waits for broker acknowledgements but does not provide durable publisher-side storage. Device-side buffering and power-loss recovery remain future firmware work.

## Read API

History returns up to the newest 1,000 raw points in the chosen window, sorted oldest first. The UI reports truncation; no aggregation or imputation is hidden. Latest readings are selected by acquisition timestamp, so a delayed old message does not replace a newer measurement. Sensor and synthetic modes use separate queries.

The configured offline threshold defaults to 120 seconds for this prototype. It is a development default, not an experimentally established acquisition policy. API readiness checks database access; worker health is demonstrated by the full MQTT-to-HTTP integration check. Data validation, uptime, and successful transport do not validate anomaly detectors or provide deployment authorization.

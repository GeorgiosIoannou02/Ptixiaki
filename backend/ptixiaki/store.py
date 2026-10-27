"""InfluxDB persistence with separate synthetic/sensor series."""

from dataclasses import dataclass
import json

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import Settings
from .models import Source, Telemetry, Window


MEASUREMENT = "environment"
FIELDS = ("temperature_c", "relative_humidity_pct", "pressure_hpa")
HISTORY_LIMIT = 1000


@dataclass
class HistoryResult:
    readings: list[Telemetry]
    truncated: bool = False


class InfluxStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
            timeout=10_000,
        )
        self.writer = self.client.write_api(write_options=SYNCHRONOUS)

    def close(self):
        self.writer.close()
        self.client.close()

    def ping(self) -> bool:
        # /ping is unauthenticated and cannot establish that the configured
        # token, organization and bucket work. An empty authenticated query can.
        query = f'''from(bucket: {json.dumps(self.settings.influxdb_bucket)})
  |> range(start: -1s)
  |> limit(n: 1)'''
        self.client.query_api().query(query)
        return True

    def write(self, reading: Telemetry):
        # Influx point identity is measurement + tags + timestamp. MQTT QoS1
        # redelivery therefore overwrites the same point instead of duplicating it.
        point = (
            Point(MEASUREMENT)
            .tag("device_id", reading.device_id)
            .tag("source", reading.source)
            .time(reading.timestamp_utc, WritePrecision.US)
        )
        for field in FIELDS:
            point.field(field, getattr(reading, field))
        self.writer.write(bucket=self.settings.influxdb_bucket, record=point)

    def _query(self, source: Source, window: Window | None, limit: int) -> list[Telemetry]:
        if source not in ("synthetic", "sensor"):
            raise ValueError("unknown source")
        if window is not None and window not in ("1h", "6h", "24h"):
            raise ValueError("unknown history window")
        start = f"-{window}" if window else "0"
        query = f'''from(bucket: {json.dumps(self.settings.influxdb_bucket)})
  |> range(start: {start})
  |> filter(fn: (r) => r._measurement == {json.dumps(MEASUREMENT)})
  |> filter(fn: (r) => r.device_id == {json.dumps(self.settings.device_id)} and r.source == {json.dumps(source)})
  |> filter(fn: (r) => contains(value: r._field, set: {json.dumps(FIELDS)}))
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})'''
        readings = []
        for record in self.client.query_api().query_stream(query):
            readings.append(Telemetry(
                device_id=record.values["device_id"],
                timestamp_utc=record.get_time(),
                synthetic=record.values["source"] == "synthetic",
                **{field: record.values[field] for field in FIELDS},
            ))
        return readings

    def latest(self, source: Source) -> Telemetry | None:
        readings = self._query(source, None, 1)
        return readings[0] if readings else None

    def history(self, source: Source, window: Window) -> HistoryResult:
        readings = self._query(source, window, HISTORY_LIMIT + 1)
        return HistoryResult(
            readings=list(reversed(readings[:HISTORY_LIMIT])),
            truncated=len(readings) > HISTORY_LIMIT,
        )

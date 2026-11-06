"""Export a bounded, complete source-specific interval for offline research."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from influxdb_client import InfluxDBClient

from .config import Settings
from .models import Source, Telemetry
from .store import FIELDS, MEASUREMENT


CSV_FIELDS = ("device_id", "timestamp_utc", "source", "synthetic", *FIELDS)
MAX_INTERVAL = timedelta(days=42)


def parse_timestamp(value: str) -> datetime:
    """Reject ambiguous times and precision that Python would silently discard."""
    try:
        if "T" not in value or re.search(r"[.,]\d{7,}", value):
            raise ValueError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise argparse.ArgumentTypeError(
            "use an ISO 8601 timestamp with timezone and at most six fractional digits"
        ) from None


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_interval(start: datetime, end: datetime, now: datetime) -> None:
    if any(value.utcoffset() is None for value in (start, end, now)):
        raise ValueError("export timestamps must include timezones")
    if start < datetime(1970, 1, 1, tzinfo=timezone.utc):
        raise ValueError("export must start on or after the Unix epoch")
    if not start < end <= now:
        raise ValueError("export requires start < end <= current time")
    if end - start > MAX_INTERVAL:
        raise ValueError("export interval must not exceed 42 days")


def export_csv(client, settings: Settings, *, source: Source, start: datetime,
               end: datetime, output: Path, now: datetime | None = None) -> int:
    """Publish a private CSV atomically only after every streamed row validates.

    A hard link installs the finished temporary file without replacing any
    existing output, including one created concurrently. Failures leave no CSV.
    """
    if source not in ("sensor", "synthetic"):
        raise ValueError("select exactly one export source")
    validate_interval(start, end, now or datetime.now(timezone.utc))
    if output.exists() or output.is_symlink():
        raise FileExistsError("export output already exists")
    query = f'''from(bucket: {json.dumps(settings.influxdb_bucket)})
  |> range(start: time(v: {json.dumps(utc_text(start))}), stop: time(v: {json.dumps(utc_text(end))}))
  |> filter(fn: (r) => r._measurement == {json.dumps(MEASUREMENT)})
  |> filter(fn: (r) => r.device_id == {json.dumps(settings.device_id)} and r.source == {json.dumps(source)})
  |> filter(fn: (r) => contains(value: r._field, set: {json.dumps(FIELDS)}))
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group()
  |> sort(columns: ["_time"], desc: false)'''
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    stream = None
    try:
        # NamedTemporaryFile uses 0600, including when the process umask is lax.
        with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8",
                                         dir=output.parent, prefix=".iot-monitor-export-",
                                         suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            stream = client.query_api().query_stream(query)
            count = 0
            previous = None
            for record in stream:
                if record.values["source"] != source or record.values["device_id"] != settings.device_id:
                    raise ValueError("export row has unexpected source or device")
                reading = Telemetry(
                    device_id=record.values["device_id"],
                    timestamp_utc=record.get_time(),
                    synthetic=source == "synthetic",
                    **{field: record.values[field] for field in FIELDS},
                )
                timestamp = reading.timestamp_utc
                if not start <= timestamp < end:
                    raise ValueError("export row is outside the requested interval")
                if previous is not None and timestamp <= previous:
                    raise ValueError("export rows must have unique ascending timestamps")
                writer.writerow({
                    "device_id": reading.device_id,
                    "timestamp_utc": utc_text(timestamp),
                    "source": reading.source,
                    "synthetic": str(reading.synthetic).lower(),
                    **{field: getattr(reading, field) for field in FIELDS},
                })
                previous = timestamp
                count += 1
            handle.flush()
            os.fsync(handle.fileno())
        if stream is not None and hasattr(stream, "close"):
            stream.close()
        stream = None
        os.link(temporary, output)
        return count
    finally:
        try:
            if stream is not None and hasattr(stream, "close"):
                stream.close()
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("sensor", "synthetic"), required=True)
    parser.add_argument("--start", type=parse_timestamp, required=True,
                        help="inclusive acquisition timestamp")
    parser.add_argument("--end", type=parse_timestamp, required=True,
                        help="exclusive acquisition timestamp; maximum interval 42 days")
    parser.add_argument("--output", type=Path, required=True,
                        help="new CSV path; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        # Fail invalid ranges before contacting the database.
        validate_interval(args.start, args.end, datetime.now(timezone.utc))
        settings = Settings.from_env()
        with InfluxDBClient(url=settings.influxdb_url, token=settings.influxdb_token,
                            org=settings.influxdb_org, timeout=60_000) as client:
            count = export_csv(client, settings, source=args.source, start=args.start,
                               end=args.end, output=args.output)
    except KeyboardInterrupt:
        print("Export interrupted; no incomplete CSV was published.", file=sys.stderr)
        return 130
    except Exception as error:
        # Database exceptions can contain URLs, tokens and raw query values.
        print(f"Export failed ({type(error).__name__}). Check the time range, configuration, "
              "database access, and that the output is a new writable path.", file=sys.stderr)
        return 1
    print(f"Exported {count} {args.source} readings in UTC to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

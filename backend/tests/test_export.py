"""Research exports must be complete, source-specific and safe to retry."""

import argparse
import csv
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from iot_monitor.config import Settings
from iot_monitor.export import export_csv, main, parse_timestamp, validate_interval


START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = START + timedelta(days=1)
SETTINGS = Settings(influxdb_token="private-token")


def record(seconds=0, **changes):
    values = dict(device_id=SETTINGS.device_id, source="synthetic",
                  temperature_c=23.5, relative_humidity_pct=45.0, pressure_hpa=1012.0)
    values.update(changes)
    return SimpleNamespace(values=values, get_time=lambda: START + timedelta(seconds=seconds))


class Client:
    def __init__(self, rows):
        self.rows = rows
        self.query = None

    def query_api(self):
        return self

    def query_stream(self, query):
        self.query = query
        return iter(self.rows)


def export(client, path, **kwargs):
    return export_csv(client, SETTINGS, source="synthetic", start=START,
                      end=END, output=path, now=END, **kwargs)


def test_full_export_has_no_dashboard_cap_and_keeps_precision(tmp_path):
    client = Client([record(i / 10) for i in range(1005)])
    path = tmp_path / "data" / "observations.csv"
    assert export(client, path) == 1005
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1005
    assert rows[1]["timestamp_utc"] == "2026-10-01T00:00:00.100000Z"
    assert rows[0]["source"] == "synthetic"
    assert rows[0]["synthetic"] == "true"
    assert rows[0]["temperature_c"] == "23.5"
    assert path.stat().st_mode & 0o777 == 0o600
    assert 'limit(' not in client.query
    assert 'r.source == "synthetic"' in client.query
    assert 'r.device_id == "esp32-rack-01"' in client.query
    assert 'stop: time(v: "2026-10-02T00:00:00Z")' in client.query


@pytest.mark.parametrize("rows", [
    [record(source="sensor")], [record(device_id="another-device")],
    [record(temperature_c=100)], [record(-1)], [record(86400)],
    [record(1), record(0)], [record(), record()],
])
def test_invalid_rows_never_publish_partial_export(tmp_path, rows):
    path = tmp_path / "invalid.csv"
    with pytest.raises(ValueError):
        export(Client(rows), path)
    assert list(tmp_path.iterdir()) == []


def test_stream_failure_cleans_partial_file(tmp_path):
    def rows():
        yield record()
        raise RuntimeError("private-token")
    with pytest.raises(RuntimeError):
        export(Client(rows()), tmp_path / "partial.csv")
    assert list(tmp_path.iterdir()) == []


def test_existing_file_is_preserved_without_query(tmp_path):
    path = tmp_path / "existing.csv"
    path.write_text("original")
    client = Client([])
    with pytest.raises(FileExistsError):
        export(client, path)
    assert path.read_text() == "original"
    assert client.query is None


def test_output_created_during_query_is_not_overwritten(tmp_path):
    path = tmp_path / "race.csv"
    def rows():
        path.write_text("concurrent export")
        yield record()
    with pytest.raises(FileExistsError):
        export(Client(rows()), path)
    assert path.read_text() == "concurrent export"
    assert list(tmp_path.iterdir()) == [path]


def test_empty_export_is_header_only(tmp_path):
    path = tmp_path / "empty.csv"
    assert export(Client([]), path) == 0
    assert len(path.read_text().splitlines()) == 1


@pytest.mark.parametrize("value", ["2026-10-01", "2026-10-01T00:00:00",
                                  "2026-10-01T00:00:00.1234567Z", "bad"])
def test_ambiguous_timestamp_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_timestamp(value)


def test_offset_is_normalized_to_utc():
    assert parse_timestamp("2026-10-01T03:00:00+03:00") == START


@pytest.mark.parametrize("start,end", [
    (START, START), (END, START), (START, END + timedelta(seconds=1)),
    (END - timedelta(days=43), END),
    (datetime(1969, 1, 1, tzinfo=timezone.utc), END),
    (START.replace(tzinfo=None), END),
])
def test_invalid_interval(start, end):
    with pytest.raises(ValueError):
        validate_interval(start, end, END)


def test_six_week_interval_is_allowed():
    validate_interval(END - timedelta(days=42), END, END)


def test_cli_error_does_not_expose_secret(monkeypatch, capsys, tmp_path):
    def fail():
        raise RuntimeError("Authorization: private-token")
    monkeypatch.setattr(Settings, "from_env", fail)
    assert main(["--source", "sensor", "--start", START.isoformat(),
                 "--end", END.isoformat(), "--output", str(tmp_path / "data.csv")]) == 1
    error = capsys.readouterr().err
    assert "Export failed" in error
    assert "private-token" not in error

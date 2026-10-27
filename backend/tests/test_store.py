"""Storage boundaries preserve provenance, UTC order and QoS1 idempotence."""

from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from ptixiaki.config import Settings
from ptixiaki.models import Telemetry
from ptixiaki.store import InfluxStore


@pytest.fixture
def store():
    with patch("ptixiaki.store.InfluxDBClient") as client_class:
        result = InfluxStore(Settings(influxdb_token="test-only"))
        yield result
        result.close()


def reading(*, synthetic=True):
    return Telemetry(
        device_id="esp32-rack-01",
        timestamp_utc=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        temperature_c=25.4,
        relative_humidity_pct=48.2,
        pressure_hpa=1012.7,
        synthetic=synthetic,
    )


def record(timestamp, source="synthetic"):
    return SimpleNamespace(
        get_time=lambda: timestamp,
        values={
            "device_id": "esp32-rack-01",
            "source": source,
            "temperature_c": 25.4,
            "relative_humidity_pct": 48.2,
            "pressure_hpa": 1012.7,
        },
    )


def test_redelivered_reading_has_identical_influx_point_identity(store):
    telemetry = reading()
    store.write(telemetry)
    store.write(telemetry)
    calls = store.writer.write.call_args_list
    first, second = (call.kwargs["record"].to_line_protocol() for call in calls)
    assert first == second
    assert "device_id=esp32-rack-01" in first
    assert "source=synthetic" in first
    assert "temperature_c=25.4" in first
    assert "relative_humidity_pct=48.2" in first
    assert "pressure_hpa=1012.7" in first
    assert calls[0].kwargs["bucket"] == "telemetry"


def test_sensor_and_synthetic_points_do_not_share_identity(store):
    store.write(reading(synthetic=True))
    store.write(reading(synthetic=False))
    lines = [call.kwargs["record"].to_line_protocol() for call in store.writer.write.call_args_list]
    assert "source=synthetic" in lines[0]
    assert "source=sensor" in lines[1]
    assert lines[0].split(" ", 1)[0] != lines[1].split(" ", 1)[0]


@pytest.mark.parametrize("source", ["synthetic", "sensor"])
def test_latest_filters_single_device_and_requested_source(store, source):
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    query_api = store.client.query_api.return_value
    query_api.query_stream.return_value = [record(timestamp, source)]
    result = store.latest(source)
    query = query_api.query_stream.call_args.args[0]
    assert 'r.device_id == "esp32-rack-01"' in query
    assert f"r.source == {json.dumps(source)}" in query
    assert result.timestamp_utc == timestamp
    assert result.synthetic is (source == "synthetic")


def test_no_database_records_returns_no_reading(store):
    store.client.query_api.return_value.query_stream.return_value = []
    assert store.latest("sensor") is None


def test_history_keeps_latest_thousand_actual_points_in_chronological_order(store):
    latest = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    records = [record(latest - timedelta(seconds=offset)) for offset in range(1001)]
    store.client.query_api.return_value.query_stream.return_value = records
    result = store.history("synthetic", "1h")
    assert result.truncated is True
    assert len(result.readings) == 1000
    assert result.readings[0].timestamp_utc == latest - timedelta(seconds=999)
    assert result.readings[-1].timestamp_utc == latest
    assert all(a.timestamp_utc < b.timestamp_utc for a, b in zip(result.readings, result.readings[1:]))


@pytest.mark.parametrize("source,window", [("all", "1h"), ("sensor", "injected()")])
def test_store_also_rejects_untrusted_query_choices(store, source, window):
    with pytest.raises(ValueError):
        store.history(source, window)
    store.client.query_api.assert_not_called()

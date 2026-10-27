"""Telemetry boundary checks protect storage and later research inputs."""

from datetime import datetime, timedelta, timezone
import json

import pytest
from pydantic import ValidationError

from ptixiaki.models import Telemetry, parse_payload


@pytest.fixture
def payload():
    return {
        "device_id": "esp32-rack-01",
        "timestamp_utc": "2026-01-01T14:00:00+02:00",
        "temperature_c": 25.4,
        "relative_humidity_pct": 48.2,
        "pressure_hpa": 1012.7,
        "synthetic": True,
    }


def test_valid_reading_preserves_measurements_and_normalizes_utc(payload):
    reading = parse_payload(json.dumps(payload).encode())
    assert reading.timestamp_utc == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    assert reading.timestamp_utc.utcoffset() == timedelta(0)
    assert reading.temperature_c == 25.4
    assert reading.relative_humidity_pct == 48.2
    assert reading.pressure_hpa == 1012.7
    assert reading.synthetic is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature_c", -40.01),
        ("temperature_c", 85.01),
        ("relative_humidity_pct", -0.01),
        ("relative_humidity_pct", 100.01),
        ("pressure_hpa", 299.99),
        ("pressure_hpa", 1100.01),
        ("temperature_c", float("nan")),
        ("relative_humidity_pct", float("inf")),
        ("pressure_hpa", float("-inf")),
        ("temperature_c", "25.4"),
        ("relative_humidity_pct", True),
        ("pressure_hpa", False),
        ("synthetic", "false"),
        ("synthetic", 1),
    ],
)
def test_invalid_measurements_and_source_types_are_rejected(payload, field, value):
    payload[field] = value
    with pytest.raises((ValidationError, ValueError)):
        Telemetry.model_validate(payload)


@pytest.mark.parametrize(
    ("temperature", "humidity", "pressure"), [(-40, 0, 300), (85, 100, 1100)]
)
def test_sensor_operating_range_boundaries_are_allowed(payload, temperature, humidity, pressure):
    payload.update(temperature_c=temperature, relative_humidity_pct=humidity, pressure_hpa=pressure)
    reading = Telemetry.model_validate(payload)
    assert reading.temperature_c == temperature
    assert reading.relative_humidity_pct == humidity
    assert reading.pressure_hpa == pressure


@pytest.mark.parametrize("timestamp", ["2026-01-01T12:00:00", "not-a-date", 1767268800])
def test_ambiguous_or_non_iso_timestamps_are_rejected(payload, timestamp):
    payload["timestamp_utc"] = timestamp
    with pytest.raises((ValidationError, ValueError)):
        Telemetry.model_validate(payload)


def test_future_timestamp_cannot_make_device_appear_online_indefinitely(payload):
    payload["timestamp_utc"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    with pytest.raises((ValidationError, ValueError)):
        Telemetry.model_validate(payload)


def test_small_clock_skew_is_allowed(payload):
    payload["timestamp_utc"] = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    assert Telemetry.model_validate(payload).timestamp_utc.tzinfo is not None


def test_source_flag_is_mandatory(payload):
    del payload["synthetic"]
    with pytest.raises((ValidationError, ValueError)):
        parse_payload(json.dumps(payload).encode())


def test_unknown_fields_are_not_silently_discarded(payload):
    payload["temperature_f"] = 77.72
    with pytest.raises((ValidationError, ValueError)):
        parse_payload(json.dumps(payload).encode())


def test_only_configured_device_is_accepted(payload):
    payload["device_id"] = "unconfigured-device"
    with pytest.raises((ValidationError, ValueError)):
        parse_payload(json.dumps(payload).encode(), expected_device_id="esp32-rack-01")


def test_device_id_can_be_explicitly_configured(payload):
    payload["device_id"] = "configured-device"
    reading = parse_payload(json.dumps(payload).encode(), expected_device_id="configured-device")
    assert reading.device_id == "configured-device"


@pytest.mark.parametrize("payload", [b"not JSON", b"[]", b"null", b"\xff", b" " * 4097])
def test_invalid_payloads_are_rejected(payload):
    with pytest.raises((ValidationError, ValueError, UnicodeDecodeError)):
        parse_payload(payload)


def test_real_readings_keep_explicit_sensor_source(payload):
    payload["synthetic"] = False
    assert parse_payload(json.dumps(payload).encode()).synthetic is False


@pytest.mark.parametrize("timestamp", [
    "0001-01-01T00:00:00+01:00",
    "9999-12-31T23:59:59-01:00",
])
def test_timezone_overflow_is_a_validation_error(payload, timestamp):
    payload["timestamp_utc"] = timestamp
    with pytest.raises(ValidationError, match="cannot be represented in UTC"):
        parse_payload(json.dumps(payload).encode())

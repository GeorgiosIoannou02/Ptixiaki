"""MQTT acknowledgement must follow persistence, never just receipt."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ptixiaki.config import Settings
from ptixiaki.worker import IngestionWorker


class ImmediateEvent:
    """Controllable retry clock so failure tests never sleep."""

    def __init__(self, *, stop_on_wait=False):
        self.stopped = False
        self.stop_on_wait = stop_on_wait
        self.waits = []

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, delay):
        self.waits.append(delay)
        if self.stop_on_wait:
            self.set()
        return self.stopped


@pytest.fixture
def settings():
    return Settings(influxdb_token="test-only")


@pytest.fixture
def message(settings):
    payload = {
        "device_id": settings.device_id,
        "timestamp_utc": "2026-01-01T12:00:00Z",
        "temperature_c": 25.4,
        "relative_humidity_pct": 48.2,
        "pressure_hpa": 1012.7,
        "synthetic": True,
    }
    return SimpleNamespace(topic=settings.mqtt_topic, payload=json.dumps(payload).encode(), mid=42, qos=1)


def test_valid_telemetry_is_acknowledged_only_after_write(settings, message):
    events = []
    store = Mock()
    store.write.side_effect = lambda reading: events.append(("write", reading.synthetic))
    client = Mock()
    client.ack.side_effect = lambda mid, qos: events.append(("ack", mid, qos))
    IngestionWorker(settings, store).on_message(client, None, message)
    assert events == [("write", True), ("ack", 42, 1)]


def test_transient_database_failure_retries_without_premature_ack(settings, message):
    events = []
    attempts = 0

    def write(_reading):
        nonlocal attempts
        attempts += 1
        events.append("write")
        if attempts < 3:
            raise ConnectionError("database unavailable")

    store, client, clock = Mock(), Mock(), ImmediateEvent()
    store.write.side_effect = write
    client.ack.side_effect = lambda *_: events.append("ack")
    IngestionWorker(settings, store, stop_event=clock).on_message(client, None, message)
    assert events == ["write", "write", "write", "ack"]
    assert clock.waits == [1, 2]
    client.ack.assert_called_once_with(42, 1)


def test_shutdown_during_failed_write_leaves_message_unacknowledged(settings, message):
    store, client = Mock(), Mock()
    store.write.side_effect = ConnectionError("not persisted")
    clock = ImmediateEvent(stop_on_wait=True)
    IngestionWorker(settings, store, stop_event=clock).on_message(client, None, message)
    store.write.assert_called_once()
    client.ack.assert_not_called()


def test_poison_message_is_discarded_without_logging_payload(settings, message, caplog):
    message.payload = b'{"accidental_secret":"never-print-this"}'
    store, client = Mock(), Mock()
    IngestionWorker(settings, store).on_message(client, None, message)
    store.write.assert_not_called()
    client.ack.assert_called_once_with(42, 1)
    assert "never-print-this" not in caplog.text
    assert "Discarded invalid telemetry" in caplog.text


def test_unexpected_topic_cannot_write_to_telemetry_store(settings, message):
    message.topic = "unrelated/topic"
    store, client = Mock(), Mock()
    IngestionWorker(settings, store).on_message(client, None, message)
    store.write.assert_not_called()
    client.ack.assert_called_once_with(42, 1)


def test_database_exception_message_is_not_logged(settings, message, caplog):
    store, client = Mock(), Mock()
    store.write.side_effect = RuntimeError("Authorization Token never-print-this")
    clock = ImmediateEvent(stop_on_wait=True)
    IngestionWorker(settings, store, stop_event=clock).on_message(client, None, message)
    assert "never-print-this" not in caplog.text
    assert "retrying without acknowledgement" in caplog.text


@pytest.mark.parametrize("timestamp", [
    "0001-01-01T00:00:00+01:00",
    "9999-12-31T23:59:59-01:00",
])
def test_unrepresentable_utc_timestamp_is_discarded_not_retried(settings, message, timestamp):
    payload = json.loads(message.payload)
    payload["timestamp_utc"] = timestamp
    message.payload = json.dumps(payload).encode()
    store, client = Mock(), Mock()
    clock = ImmediateEvent()
    IngestionWorker(settings, store, stop_event=clock).on_message(client, None, message)
    store.write.assert_not_called()
    client.ack.assert_called_once_with(42, 1)
    assert clock.waits == []

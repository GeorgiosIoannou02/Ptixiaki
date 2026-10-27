"""Shared MQTT transport for local simulation and pipeline checks."""

from __future__ import annotations

import os
import time
from threading import Event
from uuid import uuid4

import paho.mqtt.client as mqtt


class Publisher:
    """QoS 1 publisher with automatic reconnects and bounded acknowledgement waits.

    Delivery acknowledgements come from the broker, not the ingestion worker.
    A retry may duplicate a message; keep the payload timestamp unchanged so the
    application's device/source/timestamp key remains idempotent.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self.host = os.getenv("MQTT_HOST", "127.0.0.1")
        self.port = int(os.getenv("MQTT_PORT", "1883"))
        self.topic = os.getenv(
            "MQTT_TOPIC", "ptixiaki/equipment-space-01/telemetry"
        )
        self.connected = Event()
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"ptixiaki-tool-{uuid4().hex[:16]}",
        )
        username = os.getenv("MQTT_USERNAME")
        password = os.getenv("MQTT_PASSWORD")
        if password and not username:
            raise ValueError("MQTT_PASSWORD requires MQTT_USERNAME")
        if username:
            self.client.username_pw_set(username, password)
        self.client.reconnect_delay_set(min_delay=1, max_delay=8)
        self.client.connect_timeout = min(timeout, 10.0)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, _client, _userdata, _flags, reason, _properties):
        if not reason.is_failure:
            self.connected.set()

    def _on_disconnect(self, _client, _userdata, _flags, _reason, _properties):
        self.connected.clear()

    def __enter__(self) -> Publisher:
        self.client.connect_async(self.host, self.port, keepalive=30)
        self.client.loop_start()
        if not self.connected.wait(self.timeout):
            self.close()
            raise TimeoutError("MQTT connection was not accepted before timeout")
        return self

    def publish(self, payload: str | bytes) -> None:
        deadline = time.monotonic() + self.timeout
        while (remaining := deadline - time.monotonic()) > 0:
            if not self.connected.wait(remaining):
                break
            publication = self.client.publish(
                self.topic, payload=payload, qos=1, retain=False
            )
            if publication.rc == mqtt.MQTT_ERR_NO_CONN:
                # A disconnect can race publish(). Retrying the same reading is
                # safe; the worker's storage key deduplicates that reading.
                time.sleep(min(0.2, remaining))
                continue
            if publication.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError("MQTT rejected the queued publication")
            publication.wait_for_publish(max(0.0, deadline - time.monotonic()))
            if publication.is_published():
                return
            break
        raise TimeoutError("MQTT delivery was not acknowledged before timeout")

    def close(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()

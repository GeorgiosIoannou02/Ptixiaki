#!/usr/bin/env python3
"""Exercise the running MQTT -> worker -> InfluxDB -> HTTP software pipeline.

This adds two explicitly synthetic readings to the development database. It
does not publish fake sensor data or delete existing measurements. Run against
the local development stack, not a production or research collection instance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import sys
import time

import httpx

from mqtt_support import Publisher


TIMEOUT = 30.0


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_json(client: httpx.Client, path: str, **params) -> dict:
    response = client.get(path, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"API check returned HTTP {response.status_code}")
    return response.json()


def history(client: httpx.Client, source: str) -> list[dict]:
    return get_json(client, "/api/readings", source=source, window="1h")["readings"]


def same_instant(reading: dict, expected: dict) -> bool:
    return instant(reading["timestamp_utc"]) == instant(expected["timestamp_utc"])


def verify_reading(actual: dict, expected: dict) -> None:
    assert same_instant(actual, expected), "UTC timestamp changed in transit"
    for key in expected.keys() - {"timestamp_utc"}:
        assert actual[key] == expected[key], f"Stored {key} differs from publication"


def wait_for_reading(client: httpx.Client, publisher: Publisher, expected: dict) -> None:
    deadline = time.monotonic() + TIMEOUT
    next_retry = 0.0
    while time.monotonic() < deadline:
        # Idempotent republishing also permits a worker that is still subscribing
        # when the first startup check begins. No retained MQTT messages are used.
        if time.monotonic() >= next_retry:
            publisher.publish(json.dumps(expected))
            next_retry = time.monotonic() + 2.0
        matches = [r for r in history(client, "synthetic") if same_instant(r, expected)]
        if matches:
            assert len(matches) == 1, "Duplicate timestamp produced multiple readings"
            verify_reading(matches[0], expected)
            return
        time.sleep(0.2)
    raise TimeoutError("Published synthetic reading did not reach the API")


def run() -> None:
    base_url = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
    with httpx.Client(base_url=base_url, timeout=5, trust_env=False) as client:
        deadline = time.monotonic() + TIMEOUT
        while True:
            try:
                response = client.get("/api/health")
                ready = response.status_code == 200 and response.json().get("status") == "ok"
            except (httpx.HTTPError, ValueError):
                ready = False
            if ready:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("API/database did not become ready")
            time.sleep(0.2)
        print("PASS readiness: API and database are reachable", flush=True)

        baseline = {
            "device_id": os.getenv("DEVICE_ID", "esp32-rack-01"),
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "temperature_c": 23.456,
            "relative_humidity_pct": 47.891,
            "pressure_hpa": 1009.876,
            "synthetic": True,
        }
        with Publisher(timeout=TIMEOUT) as publisher:
            wait_for_reading(client, publisher, baseline)
            print("PASS pipeline: MQTT publication returned through InfluxDB and HTTP intact",
                  flush=True)

            # Same MQTT connection preserves message order. The valid barrier
            # establishes that the worker has passed the invalid/duplicate input.
            publisher.publish(json.dumps(baseline))
            publisher.publish(b'{"synthetic":')
            invalid_time = max(datetime.now(timezone.utc),
                               instant(baseline["timestamp_utc"]) + timedelta(microseconds=1))
            invalid = {**baseline, "timestamp_utc": invalid_time.isoformat(),
                       "relative_humidity_pct": 101.0}
            publisher.publish(json.dumps(invalid))
            barrier_time = max(datetime.now(timezone.utc), invalid_time + timedelta(microseconds=1))
            barrier = {**baseline, "timestamp_utc": barrier_time.isoformat(),
                       "temperature_c": 24.567}
            wait_for_reading(client, publisher, barrier)

        readings = history(client, "synthetic")
        assert sum(same_instant(r, baseline) for r in readings) == 1, "Duplicate was stored twice"
        assert not any(same_instant(r, invalid) for r in readings), "Invalid humidity was stored"
        assert all(r["synthetic"] is True for r in readings), "Synthetic query mixed data sources"
        print("PASS ingestion: duplicate idempotent; malformed JSON and invalid humidity rejected", flush=True)

        sensor_readings = history(client, "sensor")
        assert all(r["synthetic"] is False for r in sensor_readings), "Sensor history contains simulation"
        assert not any(same_instant(r, baseline) or same_instant(r, barrier)
                       for r in sensor_readings), "Synthetic test points entered sensor history"
        latest_sensor = get_json(client, "/api/readings/latest", source="sensor")["reading"]
        assert latest_sensor is None or latest_sensor["synthetic"] is False, "Sensor latest mixed sources"
        latest = get_json(client, "/api/readings/latest", source="synthetic")
        assert latest["reading"] is not None and latest["reading"]["synthetic"] is True
        assert instant(latest["reading"]["timestamp_utc"]) >= instant(barrier["timestamp_utc"])
        assert latest["online"] is True, "Fresh synthetic stream was reported offline"
        print("PASS API: chronological latest, fresh status and separate sensor history", flush=True)
        print("Synthetic software checks passed. Hardware and research results remain unverified.")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, TimeoutError, ValueError, KeyError, httpx.HTTPError) as error:
        detail = str(error) if isinstance(error, (AssertionError, RuntimeError, TimeoutError)) else type(error).__name__
        print(f"FAIL pipeline check: {detail}", file=sys.stderr)
        raise SystemExit(1)

"""Exercise public API behavior without a live database."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from ptixiaki.api import create_app
from ptixiaki.config import Settings
from ptixiaki.models import Telemetry
from ptixiaki.store import HistoryResult


def reading(*, synthetic=True, seconds_ago=0):
    return Telemetry(
        device_id="esp32-rack-01",
        timestamp_utc=datetime.now(timezone.utc) - timedelta(seconds=seconds_ago),
        temperature_c=25.4,
        relative_humidity_pct=48.2,
        pressure_hpa=1012.7,
        synthetic=synthetic,
    )


class FakeStore:
    def __init__(self):
        self.available = True
        self.failure = None
        self.latest_reading = None
        self.history_result = HistoryResult(readings=[], truncated=False)
        self.requests = []

    def ping(self):
        if self.failure:
            raise self.failure
        return self.available

    def latest(self, source):
        self.requests.append(("latest", source))
        if self.failure:
            raise self.failure
        return self.latest_reading

    def history(self, source, window):
        self.requests.append(("history", source, window))
        if self.failure:
            raise self.failure
        return self.history_result

    def close(self):
        pass


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def client(store):
    app = create_app(settings=Settings(influxdb_token="test-token"), store=store)
    with TestClient(app) as client:
        yield client


def test_empty_database_is_explicit_not_sample_data(client):
    response = client.get("/api/readings/latest")
    assert response.status_code == 200
    assert response.json() == {"reading": None, "online": False, "age_seconds": None}
    history = client.get("/api/readings").json()
    assert history["readings"] == []
    assert history["source"] == "synthetic"
    assert history["truncated"] is False


def test_recent_reading_is_online_with_measurements(client, store):
    store.latest_reading = reading(seconds_ago=2)
    response = client.get("/api/readings/latest")
    assert response.status_code == 200
    result = response.json()
    assert result["online"] is True
    assert 2 <= result["age_seconds"] < 30
    assert result["reading"]["temperature_c"] == 25.4
    assert result["reading"]["synthetic"] is True


def test_stale_sensor_reading_is_offline(client, store):
    store.latest_reading = reading(synthetic=False, seconds_ago=300)
    result = client.get("/api/readings/latest?source=sensor").json()
    assert result["online"] is False
    assert result["age_seconds"] >= 300
    assert result["reading"]["synthetic"] is False
    assert store.requests == [("latest", "sensor")]


def test_small_future_skew_never_reports_negative_age(client, store):
    store.latest_reading = reading(seconds_ago=-30)
    result = client.get("/api/readings/latest").json()
    assert result["age_seconds"] == 0


def test_history_passes_source_and_window_and_reports_truncation(client, store):
    store.history_result = HistoryResult(
        readings=[reading(synthetic=False, seconds_ago=120), reading(synthetic=False, seconds_ago=60)],
        truncated=True,
    )
    response = client.get("/api/readings?source=sensor&window=6h")
    assert response.status_code == 200
    result = response.json()
    assert result["source"] == "sensor"
    assert result["window"] == "6h"
    assert result["truncated"] is True
    assert len(result["readings"]) == 2
    assert all(item["synthetic"] is False for item in result["readings"])
    assert store.requests == [("history", "sensor", "6h")]


@pytest.mark.parametrize("path", [
    "/api/readings?source=all",
    "/api/readings/latest?source=all",
    "/api/readings?window=1000h",
    "/api/readings?window=1h%20%7C%3E%20drop()",
])
def test_invalid_query_options_are_rejected_before_store_access(client, store, path):
    assert client.get(path).status_code == 422
    assert store.requests == []


def test_health_reports_database_availability(client, store):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}
    store.available = False
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}


@pytest.mark.parametrize("path", ["/api/health", "/api/readings/latest", "/api/readings"])
def test_database_exceptions_are_503_and_never_expose_credentials(client, store, path):
    store.failure = RuntimeError("Authorization: Token secret-must-not-escape")
    response = client.get(path)
    assert response.status_code == 503
    assert "secret-must-not-escape" not in response.text
    assert "Authorization" not in response.text

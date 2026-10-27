import pytest

from ptixiaki.config import Settings


def test_database_token_is_required(monkeypatch):
    monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_settings_load_explicit_service_and_device_configuration(monkeypatch):
    values = {
        "INFLUXDB_TOKEN": "test-only",
        "INFLUXDB_URL": "http://influxdb:8086",
        "INFLUXDB_ORG": "test-org",
        "INFLUXDB_BUCKET": "test-bucket",
        "MQTT_HOST": "mqtt",
        "MQTT_PORT": "1884",
        "MQTT_TOPIC": "ptixiaki/test/telemetry",
        "MQTT_CLIENT_ID": "test-ingestion",
        "MQTT_USERNAME": "test-user",
        "MQTT_PASSWORD": "test-password",
        "DEVICE_ID": "test-device",
        "DEVICE_OFFLINE_SECONDS": "90",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    config = Settings.from_env()
    assert config.influxdb_url == "http://influxdb:8086"
    assert config.influxdb_org == "test-org"
    assert config.influxdb_bucket == "test-bucket"
    assert config.mqtt_host == "mqtt"
    assert config.mqtt_port == 1884
    assert config.mqtt_topic == "ptixiaki/test/telemetry"
    assert config.mqtt_client_id == "test-ingestion"
    assert config.mqtt_username == "test-user"
    assert config.mqtt_password == "test-password"
    assert config.device_id == "test-device"
    assert config.device_offline_seconds == 90


@pytest.mark.parametrize("key,value", [
    ("MQTT_PORT", "0"),
    ("MQTT_PORT", "65536"),
    ("MQTT_PORT", "not-a-number"),
    ("DEVICE_OFFLINE_SECONDS", "0"),
    ("DEVICE_OFFLINE_SECONDS", "-1"),
])
def test_invalid_numeric_configuration_fails_early(monkeypatch, key, value):
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-only")
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        Settings.from_env()

"""Runtime configuration; credentials never have committed default values."""

from dataclasses import dataclass, field
import os
import re


@dataclass(frozen=True, slots=True)
class Settings:
    influxdb_token: str = field(default="", repr=False)
    influxdb_url: str = "http://localhost:8086"
    influxdb_org: str = "ptixiaki"
    influxdb_bucket: str = "telemetry"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "ptixiaki/equipment-space-01/telemetry"
    mqtt_client_id: str = "ptixiaki-ingestion"
    mqtt_username: str | None = None
    mqtt_password: str | None = field(default=None, repr=False)
    device_id: str = "esp32-rack-01"
    device_offline_seconds: int = 120

    def __post_init__(self):
        if not self.influxdb_token.strip():
            raise ValueError("INFLUXDB_TOKEN is required")
        if not 1 <= self.mqtt_port <= 65535:
            raise ValueError("MQTT_PORT must be between 1 and 65535")
        if self.device_offline_seconds <= 0:
            raise ValueError("DEVICE_OFFLINE_SECONDS must be positive")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.device_id):
            raise ValueError("DEVICE_ID must be a lowercase identifier of at most 64 characters")
        if not self.mqtt_host or not self.mqtt_client_id:
            raise ValueError("MQTT_HOST and MQTT_CLIENT_ID must be nonempty")
        if not self.mqtt_topic or any(char in self.mqtt_topic for char in "#+\x00"):
            raise ValueError("MQTT_TOPIC must be a single concrete topic")
        if not self.influxdb_org or not self.influxdb_bucket:
            raise ValueError("INFLUXDB_ORG and INFLUXDB_BUCKET must be nonempty")
        if not self.influxdb_url.startswith(("http://", "https://")):
            raise ValueError("INFLUXDB_URL must be an HTTP or HTTPS URL")
        if self.mqtt_password and not self.mqtt_username:
            raise ValueError("MQTT_USERNAME is required when MQTT_PASSWORD is configured")

    @classmethod
    def from_env(cls):
        def integer(name: str, default: int):
            try:
                return int(os.environ.get(name, str(default)))
            except ValueError:
                raise ValueError(f"{name} must be an integer") from None

        return cls(
            influxdb_token=os.environ.get("INFLUXDB_TOKEN", ""),
            influxdb_url=os.environ.get("INFLUXDB_URL", "http://localhost:8086"),
            influxdb_org=os.environ.get("INFLUXDB_ORG", "ptixiaki"),
            influxdb_bucket=os.environ.get("INFLUXDB_BUCKET", "telemetry"),
            mqtt_host=os.environ.get("MQTT_HOST", "localhost"),
            mqtt_port=integer("MQTT_PORT", 1883),
            mqtt_topic=os.environ.get("MQTT_TOPIC", "ptixiaki/equipment-space-01/telemetry"),
            mqtt_client_id=os.environ.get("MQTT_CLIENT_ID", "ptixiaki-ingestion"),
            mqtt_username=os.environ.get("MQTT_USERNAME") or None,
            mqtt_password=os.environ.get("MQTT_PASSWORD") or None,
            device_id=os.environ.get("DEVICE_ID", "esp32-rack-01"),
            device_offline_seconds=integer("DEVICE_OFFLINE_SECONDS", 120),
        )

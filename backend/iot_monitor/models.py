"""Telemetry contract. Sensor limits are validation limits, not alert thresholds."""

from datetime import datetime, timedelta, timezone
import json
import re
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, field_validator


Source = Literal["synthetic", "sensor"]
Window = Literal["1h", "6h", "24h"]
MAX_PAYLOAD_BYTES = 4096


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: Annotated[str, Field(strict=True, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]
    timestamp_utc: AwareDatetime
    temperature_c: Annotated[float, Field(ge=-40, le=85, allow_inf_nan=False)]
    relative_humidity_pct: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    pressure_hpa: Annotated[float, Field(ge=300, le=1100, allow_inf_nan=False)]
    synthetic: StrictBool

    @field_validator("temperature_c", "relative_humidity_pct", "pressure_hpa", mode="before")
    @classmethod
    def numeric_measurement(cls, value):
        if type(value) not in (int, float):
            raise ValueError("measurement must be a JSON number")
        return value

    @field_validator("timestamp_utc", mode="before")
    @classmethod
    def timestamp_format(cls, value):
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("timestamp_utc must be an ISO 8601 timestamp with timezone")
        # Pydantic truncates finer precision to microseconds. Reject it before
        # parsing so two distinct acquisitions cannot silently share a point key.
        if re.search(r"[.,]\d{7,}", value):
            raise ValueError("timestamp_utc supports at most six fractional digits")
        return value

    @field_validator("timestamp_utc")
    @classmethod
    def utc_timestamp(cls, value: datetime):
        try:
            value = value.astimezone(timezone.utc)
        except OverflowError:
            raise ValueError("timestamp_utc cannot be represented in UTC") from None
        if value < datetime(1970, 1, 1, tzinfo=timezone.utc):
            raise ValueError("timestamp_utc must be on or after the Unix epoch")
        if value > datetime.now(timezone.utc) + timedelta(minutes=2):
            raise ValueError("timestamp_utc is more than two minutes in the future")
        return value

    @property
    def source(self) -> Source:
        return "synthetic" if self.synthetic else "sensor"


def parse_payload(payload: bytes, expected_device_id: str = "esp32-rack-01") -> Telemetry:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("telemetry payload exceeds maximum size")
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("telemetry JSON must not contain duplicate fields")
            result[key] = value
        return result

    # Conflicting duplicate fields (especially synthetic/device_id) have no
    # unambiguous interpretation. Decode UTF-8 explicitly as the wire contract.
    try:
        decoded = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_fields)
    except RecursionError:
        raise ValueError("telemetry JSON is too deeply nested") from None
    reading = Telemetry.model_validate(decoded)
    if reading.device_id != expected_device_id:
        raise ValueError("unconfigured device")
    return reading


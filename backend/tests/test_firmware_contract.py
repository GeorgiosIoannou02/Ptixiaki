"""Compile the actual firmware serializer and validate its output with the backend."""
from pathlib import Path
import subprocess

from iot_monitor.models import parse_payload


def test_firmware_wire_contract(tmp_path):
    root = Path(__file__).resolve().parents[2]
    binary = tmp_path / "firmware-contract"
    subprocess.run([
        "g++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
        "-I", str(root / "firmware/include"),
        str(root / "firmware/tests/telemetry_test.cpp"), "-o", str(binary),
    ], check=True)
    payload = subprocess.check_output([str(binary)])
    reading = parse_payload(payload)
    assert reading.source == "sensor"
    assert reading.synthetic is False
    assert reading.pressure_hpa == 1013.25
    assert reading.temperature_c == 23.5
    assert reading.relative_humidity_pct == 48.25
    assert reading.timestamp_utc.isoformat() == "2026-01-01T12:00:00+00:00"

#!/usr/bin/env python3
"""Publish clearly marked synthetic readings for the one-device software demo."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
import random
import sys
import time

from mqtt_support import Publisher


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be an integer greater than zero")
    return number


def make_reading(index: int, rng: random.Random, device_id: str) -> dict:
    """A seeded demonstration curve, not measured data or anomaly ground truth."""
    return {
        "device_id": device_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "temperature_c": round(23 + 1.5 * math.sin(index / 12) + rng.uniform(-0.1, 0.1), 3),
        "relative_humidity_pct": round(47 + 4 * math.cos(index / 16) + rng.uniform(-0.2, 0.2), 3),
        "pressure_hpa": round(1012 + 1.2 * math.sin(index / 20) + rng.uniform(-0.1, 0.1), 3),
        "synthetic": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send SYNTHETIC data for one device; this does not read a sensor.",
        epilog="Connection settings: MQTT_HOST, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, "
        "MQTT_PASSWORD and DEVICE_ID environment variables. The demo interval is "
        "not a decision about the eventual hardware sampling rate.",
    )
    parser.add_argument("--interval", type=positive_float, default=5.0,
                        help="seconds between demo readings (default: 5)")
    parser.add_argument("--count", type=positive_int,
                        help="number of readings; omit to run until Ctrl-C")
    parser.add_argument("--seed", type=int, default=0,
                        help="repeatable measurement sequence (timestamps remain current)")
    parser.add_argument("--timeout", type=positive_float, default=30.0,
                        help="connection/publication timeout in seconds (default: 30)")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    device_id = os.getenv("DEVICE_ID", "esp32-rack-01")
    print("SIMULATED DATA ONLY — no physical sensor or real experiment.", flush=True)
    try:
        with Publisher(timeout=args.timeout) as publisher:
            index = 0
            while args.count is None or index < args.count:
                reading = make_reading(index, rng, device_id)
                publisher.publish(json.dumps(reading, allow_nan=False))
                index += 1
                print(f"Synthetic reading {index} acknowledged by MQTT: "
                      f"{reading['timestamp_utc']}", flush=True)
                if args.count is None or index < args.count:
                    time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Simulation stopped.", flush=True)
        return 130
    except (TimeoutError, RuntimeError, ValueError, OSError) as error:
        # Connection exceptions can expose destinations; never echo credentials.
        print(f"Simulation failed ({type(error).__name__}); check local service "
              "readiness and MQTT configuration. No delivery success is assumed.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

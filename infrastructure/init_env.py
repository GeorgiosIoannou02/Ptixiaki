"""Create local development credentials without overwriting existing settings."""

import os
from pathlib import Path
import secrets


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / ".env"
    if target.exists() or target.is_symlink():
        print(".env already exists; preserved without changes.")
        return
    # Database data and its credentials must be retained together.
    if (root / "data/influxdb/influxd.bolt").exists():
        raise SystemExit("Existing database found. Restore its original .env before starting.")
    content = (root / ".env.example").read_text()
    content = content.replace("INFLUXDB_PASSWORD=\n", f"INFLUXDB_PASSWORD={secrets.token_urlsafe(32)}\n")
    content = content.replace("INFLUXDB_TOKEN=\n", f"INFLUXDB_TOKEN={secrets.token_urlsafe(48)}\n")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)
    print("Created private .env for local development. Keep it with your database; do not commit it.")


if __name__ == "__main__":
    main()

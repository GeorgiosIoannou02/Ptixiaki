# PTIXIAKI — environmental monitoring

A bachelor's thesis prototype for **one ESP32 and one Grove BME280** in one equipment space. The first software milestone runs with explicitly simulated readings:

```text
Synthetic publisher → Mosquitto → Python ingestion worker → InfluxDB 2
                                                             ↓
                                                    FastAPI → React dashboard
```

The physical sensor, firmware, site deployment, real data collection, alerts, and anomaly-detection comparison are still pending. Simulation does not establish hardware readiness or research results. Read [the project context](PTIXIAKI_PROJECT_CONTEXT.md) for the confirmed scope and open decisions.

## Run the software demo

Requirements: Docker Engine with Compose v2 and Python 3.12. Install `uv` to run the Python checks locally. Node 22.12+ is needed only for frontend development outside Docker.

From the repository root:

```bash
python3 infrastructure/init_env.py
docker compose --profile demo up --build -d --wait
```

The initializer creates an ignored, private `.env` with random local database credentials and preserves it on subsequent runs. Keep `.env` and `data/` together; changing initialization variables does not reset an existing database.

The dashboard is served on host port **8080**, the API on **8000**, MQTT on **1883**, and InfluxDB on **8086**. All published ports bind to the host loopback address. The dashboard defaults to **Simulated data**, updates every five seconds, and can switch to **Sensor data**, which stays empty until real telemetry is ingested. Charts and timestamps use UTC. The simulator's five-second interval is a demo setting, not the final acquisition frequency.

Without the simulator:

```bash
docker compose up --build -d --wait
# If a simulator from an earlier run is still active:
docker compose --profile demo stop simulator
```

Stop all demo services without deleting data:

```bash
docker compose --profile demo stop
```

The broker uses anonymous MQTT only within this local development setup. Physical deployment requires a separately configured network, authentication, and authorization; this is not a production deployment configuration. The local database has no automatic retention expiry, allowing a later documented policy to preserve the planned 3–6 weeks of observations.

## Validate the pipeline

With services running, from the repository root:

```bash
uv sync --frozen
uv run --frozen pytest
uv run --frozen --env-file .env python scripts/check_pipeline.py
```

The integration check publishes two marked synthetic readings through the real broker and worker, verifies their stored values through the API, checks duplicate handling and invalid-reading rejection, and checks that sensor history remains separate. It adds synthetic data and deletes nothing; use the development instance.

Run the frontend checks separately:

```bash
cd frontend
npm ci
npm test
npm run build
```

## Develop locally

Start just the dependencies:

```bash
docker compose up -d --wait mqtt influxdb
uv sync --frozen
```

Then use separate terminals from the repository root:

```bash
uv run --frozen --env-file .env uvicorn ptixiaki.api:app --reload --host 127.0.0.1
uv run --frozen --env-file .env python -m ptixiaki.worker
uv run --frozen --env-file .env python scripts/simulate.py --count 12 --interval 5
```

From `frontend`, run `npm ci` and `npm run dev`. Vite proxies `/api` to the local API on port 8000; `VITE_API_PROXY_TARGET` can override that destination. Stop the corresponding Compose API/worker/web/simulator services first to avoid port conflicts and two workers sharing the same MQTT client ID.

## API and telemetry

- `GET /api/health` checks access to the configured database and bucket.
- `GET /api/readings/latest?source=synthetic` returns the latest reading, its age, and whether it is recent enough to count as online.
- `GET /api/readings?source=synthetic&window=1h` returns up to the latest 1,000 actual readings in ascending timestamp order, with `truncated=true` when older points in the requested window are omitted.
- `source` is `synthetic` or `sensor`; `window` is `1h`, `6h`, or `24h`. No automatic mixing of sources occurs.

See [the telemetry contract](docs/telemetry.md) for units, validation, MQTT behavior, and limitations. Online status describes the age of the latest measurement, not independently verified hardware or network connectivity. An API/storage error is shown as unavailable, not as a zero-valued reading.

## Cloud environment

The managed environment has a read-only home directory and a trusted egress proxy. Use writable tool caches and the supplied certificate bundle for container builds:

```bash
export UV_CACHE_DIR=/workspace/ptixiaki-environment/uv-cache
export npm_config_cache=/workspace/ptixiaki-environment/npm-cache
export BUILDX_CONFIG=/workspace/ptixiaki-environment/buildx
export PTIXIAKI_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
docker compose -f compose.yaml -f infrastructure/compose.cloud.yaml --profile demo up --build -d --wait
```

The optional override mounts the trusted CA bundle only during dependency installation. TLS and package verification stay enabled; certificates and credentials are not committed or baked into application images. On an ordinary workstation without this proxy, use the normal Compose command.

## Project layout

- `backend/ptixiaki/`: validation, configuration, storage, API, and MQTT worker.
- `backend/tests/`: backend regression tests.
- `frontend/`: React dashboard, UI tests, and nginx packaging.
- `scripts/`: synthetic publisher and full pipeline check.
- `infrastructure/`: local initialization, broker configuration, cloud build override.
- `data/`: ignored local database and broker state.

Next milestones are the actual ESP32/BME280 firmware and hardware check, real deployment permission and hosting, then alerts, data collection, and chronological baseline/ML evaluation. No ML performance claim follows from this software demo.

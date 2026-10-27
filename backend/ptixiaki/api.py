"""Read-only HTTP API. MQTT ingestion runs as a separate worker process."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import Settings
from .models import Source, Window
from .store import InfluxStore


logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, store=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application):
        application.state.settings = settings or Settings.from_env()
        application.state.store = store if store is not None else InfluxStore(application.state.settings)
        try:
            yield
        finally:
            application.state.store.close()

    application = FastAPI(title="PTIXIAKI telemetry API", version="0.1.0", lifespan=lifespan)

    @application.get("/api/health")
    def health(request: Request):
        try:
            available = request.app.state.store.ping()
        except Exception:
            available = False
        return JSONResponse(
            {"status": "ok" if available else "unavailable", "database": "up" if available else "down"},
            status_code=200 if available else 503,
        )

    @application.get("/api/readings/latest")
    def latest(request: Request, source: Source = "synthetic"):
        try:
            reading = request.app.state.store.latest(source)
        except Exception as error:
            logger.warning("Latest reading unavailable (%s)", type(error).__name__)
            raise HTTPException(503, "Telemetry storage is unavailable") from None
        age = max(0.0, (datetime.now(timezone.utc) - reading.timestamp_utc).total_seconds()) if reading else None
        return {
            "reading": reading,
            "online": age is not None and age <= request.app.state.settings.device_offline_seconds,
            "age_seconds": age,
        }

    @application.get("/api/readings")
    def history(request: Request, source: Source = "synthetic", window: Window = "1h"):
        try:
            result = request.app.state.store.history(source, window)
        except Exception as error:
            logger.warning("Reading history unavailable (%s)", type(error).__name__)
            raise HTTPException(503, "Telemetry storage is unavailable") from None
        return {"readings": result.readings, "source": source, "window": window, "truncated": result.truncated}

    return application


app = create_app()

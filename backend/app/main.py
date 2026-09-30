"""FastAPI application entry point.

Wires configuration and, for local development, serves generated audio from the
filesystem. Feature routers are mounted as they are built.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import logging

from app.api import auth, episodes, feedback, users
from app.config import get_settings
from app.observability import configure_logging, configure_telemetry

settings = get_settings()
configure_logging(settings)
log = logging.getLogger("app")

app = FastAPI(title="Jarvis", version=settings.service_version)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(episodes.router)
app.include_router(feedback.router)

# Instrument after routes exist (no-op unless OTEL_ENABLED).
configure_telemetry(app, settings)
log.info("Jarvis %s started (env=%s)", settings.service_version, settings.app_env)


# In local mode, serve generated episodes so the app can play them back.
if settings.storage_provider == "local":
    from pathlib import Path

    Path(settings.storage_local_dir).mkdir(parents=True, exist_ok=True)
    app.mount(
        "/media",
        StaticFiles(directory=settings.storage_local_dir),
        name="media",
    )

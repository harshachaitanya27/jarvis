"""FastAPI application entry point.

Wires configuration and, for local development, serves generated audio from the
filesystem. Feature routers are mounted as they are built.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import auth, episodes, feedback, users
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Jarvis", version="0.1.0")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(episodes.router)
app.include_router(feedback.router)


# In local mode, serve generated episodes so the app can play them back.
if settings.storage_provider == "local":
    from pathlib import Path

    Path(settings.storage_local_dir).mkdir(parents=True, exist_ok=True)
    app.mount(
        "/media",
        StaticFiles(directory=settings.storage_local_dir),
        name="media",
    )

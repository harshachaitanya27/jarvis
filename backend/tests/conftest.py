"""Shared test setup.

Points the app at a throwaway SQLite database and sets test secrets BEFORE any
app module is imported, then creates the schema once per session. Because the
data layer is engine-agnostic, the full HTTP stack runs on SQLite unchanged.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

_db_path = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"
os.environ["KEY_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["AUTH_PROVIDER"] = "jwt"

import pytest  # noqa: E402

from app.adapters.db.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    # Use a separate short-lived engine so the app's engine is only ever touched
    # inside request event loops (avoids cross-loop async pool issues).
    from sqlalchemy.ext.asyncio import create_async_engine

    async def create() -> None:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create())
    yield

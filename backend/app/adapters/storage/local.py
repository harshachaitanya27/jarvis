"""Local-filesystem StorageProvider — the zero-dependency default.

Writes objects under a base directory and serves them via a relative API path.
Swapped for S3/Supabase by changing STORAGE_PROVIDER; callers see no difference.
"""

from pathlib import Path

from app.core.interfaces.storage import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Keys may contain "/" to namespace; keep them inside base.
        p = (self.base / key).resolve()
        if not str(p).startswith(str(self.base.resolve())):
            raise ValueError(f"key escapes storage root: {key!r}")
        return p

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    async def get(self, key: str) -> bytes:
        p = self._path(key)
        if not p.exists():
            raise KeyError(key)
        return p.read_bytes()

    async def url(self, key: str, expires_seconds: int = 3600) -> str:
        # Local files are served by the app; signing is a no-op here.
        return f"/media/{key}"

    async def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

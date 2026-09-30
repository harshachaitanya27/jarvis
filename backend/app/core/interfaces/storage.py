"""Object-storage contract for generated audio.

Any backend (local filesystem, S3/R2/MinIO, Supabase Storage) implements this.
Nothing outside an adapter knows which one is in use.
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Stores and serves opaque binary objects addressed by a key."""

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store ``data`` under ``key``; return the canonical stored key."""
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Fetch the object's bytes. Raise ``KeyError`` if absent."""
        ...

    @abstractmethod
    async def url(self, key: str, expires_seconds: int = 3600) -> str:
        """Return a playable URL (signed/time-limited where supported)."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the object. No error if it is already gone."""
        ...

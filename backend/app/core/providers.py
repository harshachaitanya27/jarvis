"""Provider factory — the one place a config string becomes an adapter.

Every swappable dependency is built here from settings. Routes and services
ask for an interface and get whatever the env selected, so vendor choices never
leak into business logic.
"""

from app.config import Settings, get_settings
from app.core.interfaces.storage import StorageProvider


def build_storage(settings: Settings | None = None) -> StorageProvider:
    s = settings or get_settings()
    match s.storage_provider:
        case "local":
            from app.adapters.storage.local import LocalStorageProvider

            return LocalStorageProvider(s.storage_local_dir)
        case "s3":
            raise NotImplementedError("s3 storage adapter not implemented yet")
        case "supabase":
            raise NotImplementedError("supabase storage adapter not implemented yet")
        case other:  # pragma: no cover - guarded by config typing
            raise ValueError(f"unknown storage_provider: {other!r}")


# LLM / TTS / STT / Auth factories are added as their adapters land. Each will
# follow the same shape: match on the configured provider name, import the one
# adapter module lazily, return the interface type.

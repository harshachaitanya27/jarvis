"""Provider factory — the one place a config string becomes an adapter.

Every swappable dependency is built here from settings. Routes and services
ask for an interface and get whatever the env selected, so vendor choices never
leak into business logic.
"""

from app.config import Settings, get_settings
from app.core.interfaces.llm import LLMProvider
from app.core.interfaces.storage import StorageProvider
from app.core.interfaces.tts import TTSProvider


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


def build_llm(provider: str, api_key: str, model: str | None = None) -> LLMProvider:
    """Build the LLM adapter for a user, using their BYO key."""
    match provider:
        case "openai":
            from app.adapters.llm.openai import OpenAILLMProvider

            return OpenAILLMProvider(api_key, model or "gpt-4o-mini")
        case "anthropic":
            raise NotImplementedError("anthropic llm adapter not implemented yet")
        case "gemini":
            raise NotImplementedError("gemini llm adapter not implemented yet")
        case other:
            raise ValueError(f"unknown llm provider: {other!r}")


def build_tts(provider: str, api_key: str, model: str | None = None) -> TTSProvider:
    """Build the TTS adapter for a user, using their BYO key."""
    match provider:
        case "openai":
            from app.adapters.tts.openai import OpenAITTSProvider

            return OpenAITTSProvider(api_key, model or "tts-1")
        case "elevenlabs":
            raise NotImplementedError("elevenlabs tts adapter not implemented yet")
        case other:
            raise ValueError(f"unknown tts provider: {other!r}")


# STT / Auth factories follow the same shape as their adapters land.

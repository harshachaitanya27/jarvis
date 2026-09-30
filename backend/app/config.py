"""Central, typed configuration loaded from the environment.

Every platform choice (database, storage, auth, default providers) is a value
here, never a hardcoded import. Swapping a vendor means changing an env var,
not editing code outside that vendor's adapter.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["text", "json"] = "text"  # json for production aggregation

    # Database — a URL, so any Postgres-compatible host works unchanged
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/jarvis"
    )

    # Object storage — selects which StorageProvider adapter is built
    storage_provider: Literal["local", "s3", "supabase"] = "local"
    storage_local_dir: str = "./media"
    storage_s3_bucket: str | None = None
    storage_s3_region: str | None = None
    storage_s3_endpoint: str | None = None
    storage_s3_access_key: str | None = None
    storage_s3_secret_key: str | None = None

    # Auth — selects which AuthProvider adapter is built
    auth_provider: Literal["local", "supabase", "jwt"] = "local"

    # Secrets — Fernet key encrypting each user's BYO provider keys at rest
    key_encryption_key: str = ""

    # Auth — JWT signing for access tokens
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60 * 24 * 7  # 7 days

    # Observability — OpenTelemetry (logs, traces, metrics)
    service_name: str = "jarvis-backend"
    service_version: str = "0.1.0"
    otel_enabled: bool = False  # off by default so local dev needs no collector
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"  # OTLP/HTTP base
    otel_console_export: bool = False  # print signals to stdout instead of OTLP

    # Generation defaults (a user's stored config may override these)
    default_llm_provider: str = "openai"
    default_tts_provider: str = "openai"
    default_episode_minutes: int = 10
    default_episodes_per_night: int = 3


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the env is parsed once per process."""
    return Settings()

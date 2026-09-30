"""Pydantic request/response models for the HTTP API.

Kept separate from domain entities: these are the wire contract, the domain is
the internal model. Notably, no response ever exposes password hashes or
provider keys.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities import FeedbackType


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    topics: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TopicsRequest(BaseModel):
    topics: list[str]


class ProviderKeysRequest(BaseModel):
    # {"openai": "sk-...", "elevenlabs": "..."} — plaintext in, encrypted at rest.
    keys: dict[str, str]


class UserProfile(BaseModel):
    id: str
    email: str | None
    topics: list[str]
    configured_providers: list[str]
    daily_question_quota: int


class EpisodeSummary(BaseModel):
    id: str
    title: str | None
    status: str
    topics: list[str]
    duration_seconds: float | None
    created_at: datetime | None
    # Present only when the episode is ready; a playable (signed where supported) URL.
    audio_url: str | None


class TranscriptSegmentModel(BaseModel):
    speaker: str
    text: str
    start_seconds: float | None = None


class TranscriptResponse(BaseModel):
    episode_id: str
    segments: list[TranscriptSegmentModel]


class FeedbackCreate(BaseModel):
    type: FeedbackType  # invalid values are rejected with 422
    position_seconds: float | None = None


class FeedbackEventModel(BaseModel):
    id: str
    episode_id: str
    type: str
    position_seconds: float | None
    created_at: datetime | None

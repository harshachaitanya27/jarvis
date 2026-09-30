"""Pydantic request/response models for the HTTP API.

Kept separate from domain entities: these are the wire contract, the domain is
the internal model. Notably, no response ever exposes password hashes or
provider keys.
"""

from pydantic import BaseModel, Field


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

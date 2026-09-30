"""Core domain entities — plain dataclasses, no ORM, no vendor types.

These are what the app reasons about. The database adapter maps its own rows
to and from these, so the domain never imports SQLAlchemy or any driver.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EpisodeStatus(str, Enum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    VOICING = "voicing"
    ASSEMBLING = "assembling"
    READY = "ready"
    FAILED = "failed"


class FeedbackType(str, Enum):
    PLAY = "play"
    SKIP = "skip"
    COMPLETE = "complete"
    REPLAY = "replay"
    THUMB_UP = "thumb_up"
    THUMB_DOWN = "thumb_down"


class SignalSource(str, Enum):
    BEHAVIOR = "behavior"   # implicit: skips, completions, replays
    QUESTION = "question"   # explicit: spoken questions (higher weight)


@dataclass
class User:
    id: str
    email: str | None = None
    onboarding_topics: list[str] = field(default_factory=list)
    # BYO provider keys, stored ENCRYPTED at rest (Fernet). Never plaintext here.
    provider_keys_encrypted: dict[str, str] = field(default_factory=dict)
    daily_question_quota: int = 3
    created_at: datetime | None = None


@dataclass
class Episode:
    id: str
    user_id: str
    topics: list[str]
    status: EpisodeStatus = EpisodeStatus.QUEUED
    title: str | None = None
    audio_key: str | None = None       # storage key, resolved to a URL on read
    duration_seconds: float | None = None
    error: str | None = None           # failure reason when status == FAILED
    created_at: datetime | None = None


@dataclass
class TranscriptSegment:
    speaker: str
    text: str
    start_seconds: float | None = None


@dataclass
class Transcript:
    episode_id: str
    segments: list[TranscriptSegment] = field(default_factory=list)


@dataclass
class FeedbackEvent:
    id: str
    user_id: str
    episode_id: str
    type: FeedbackType
    position_seconds: float | None = None
    created_at: datetime | None = None


@dataclass
class Conversation:
    id: str
    user_id: str
    episode_id: str
    question_text: str
    answer_text: str
    created_at: datetime | None = None


@dataclass
class TopicSignal:
    user_id: str
    topic_cluster: str
    weight: float
    source: SignalSource
    updated_at: datetime | None = None

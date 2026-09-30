"""Persistence contracts — one repository per aggregate.

Services depend on these interfaces, never on SQLAlchemy or a driver. The db
adapter provides concrete implementations; swapping the store means writing a
new adapter, not touching services.
"""

from abc import ABC, abstractmethod

from app.domain.entities import (
    Conversation,
    Episode,
    EpisodeStatus,
    FeedbackEvent,
    TopicSignal,
    Transcript,
    User,
)


class UserRepository(ABC):
    @abstractmethod
    async def get(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def list_all(self, limit: int = 1000) -> list[User]: ...


class EpisodeRepository(ABC):
    @abstractmethod
    async def create(self, episode: Episode) -> Episode: ...

    @abstractmethod
    async def get(self, episode_id: str) -> Episode | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: str, limit: int = 50) -> list[Episode]: ...

    @abstractmethod
    async def set_status(
        self, episode_id: str, status: EpisodeStatus, error: str | None = None
    ) -> None: ...

    @abstractmethod
    async def set_title(self, episode_id: str, title: str) -> None: ...

    @abstractmethod
    async def set_audio(
        self, episode_id: str, audio_key: str, duration_seconds: float
    ) -> None: ...


class TranscriptRepository(ABC):
    @abstractmethod
    async def save(self, transcript: Transcript) -> None: ...

    @abstractmethod
    async def get_for_episode(self, episode_id: str) -> Transcript | None: ...


class FeedbackRepository(ABC):
    """Append-only event log — the implicit taste signal for V3."""

    @abstractmethod
    async def add(self, event: FeedbackEvent) -> None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: str, limit: int = 500
    ) -> list[FeedbackEvent]: ...


class ConversationRepository(ABC):
    """Spoken Q&A captured as explicit intent signal (V2)."""

    @abstractmethod
    async def add(self, conversation: Conversation) -> None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: str, limit: int = 500
    ) -> list[Conversation]: ...


class TopicSignalRepository(ABC):
    """The evolving persona the bandit reads and updates (V3)."""

    @abstractmethod
    async def upsert(self, signal: TopicSignal) -> None: ...

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[TopicSignal]: ...

"""SQLAlchemy implementations of the repository interfaces.

Each method translates between ORM rows and domain entities, so callers stay
free of persistence types. This is the only module that imports both.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db import models as m
from app.core.interfaces.database import (
    ConversationRepository,
    EpisodeRepository,
    FeedbackRepository,
    TopicSignalRepository,
    TranscriptRepository,
    UserRepository,
)
from app.domain.entities import (
    Conversation,
    Episode,
    EpisodeStatus,
    FeedbackEvent,
    FeedbackType,
    SignalSource,
    TopicSignal,
    Transcript,
    TranscriptSegment,
    User,
)

# ── mappers ───────────────────────────────────────────────────────


def _user(row: m.UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        onboarding_topics=list(row.onboarding_topics or []),
        provider_keys_encrypted=dict(row.provider_keys_encrypted or {}),
        daily_question_quota=row.daily_question_quota,
        created_at=row.created_at,
    )


def _episode(row: m.EpisodeRow) -> Episode:
    return Episode(
        id=row.id,
        user_id=row.user_id,
        topics=list(row.topics or []),
        status=EpisodeStatus(row.status),
        title=row.title,
        audio_key=row.audio_key,
        duration_seconds=row.duration_seconds,
        error=row.error,
        created_at=row.created_at,
    )


# ── repositories ──────────────────────────────────────────────────


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.s = session

    async def get(self, user_id: str) -> User | None:
        row = await self.s.get(m.UserRow, user_id)
        return _user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        row = (
            await self.s.execute(select(m.UserRow).where(m.UserRow.email == email))
        ).scalar_one_or_none()
        return _user(row) if row else None

    async def create(self, user: User) -> User:
        row = m.UserRow(
            email=user.email,
            onboarding_topics=user.onboarding_topics,
            provider_keys_encrypted=user.provider_keys_encrypted,
            daily_question_quota=user.daily_question_quota,
        )
        if user.id:
            row.id = user.id
        self.s.add(row)
        await self.s.flush()
        return _user(row)

    async def update(self, user: User) -> User:
        row = await self.s.get(m.UserRow, user.id)
        if row is None:
            raise KeyError(user.id)
        row.email = user.email
        row.onboarding_topics = user.onboarding_topics
        row.provider_keys_encrypted = user.provider_keys_encrypted
        row.daily_question_quota = user.daily_question_quota
        await self.s.flush()
        return _user(row)


class SqlEpisodeRepository(EpisodeRepository):
    def __init__(self, session: AsyncSession):
        self.s = session

    async def create(self, episode: Episode) -> Episode:
        row = m.EpisodeRow(
            user_id=episode.user_id,
            topics=episode.topics,
            status=episode.status.value,
            title=episode.title,
        )
        if episode.id:
            row.id = episode.id
        self.s.add(row)
        await self.s.flush()
        return _episode(row)

    async def get(self, episode_id: str) -> Episode | None:
        row = await self.s.get(m.EpisodeRow, episode_id)
        return _episode(row) if row else None

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[Episode]:
        rows = (
            await self.s.execute(
                select(m.EpisodeRow)
                .where(m.EpisodeRow.user_id == user_id)
                .order_by(m.EpisodeRow.created_at.desc())
                .limit(limit)
            )
        ).scalars()
        return [_episode(r) for r in rows]

    async def set_status(
        self, episode_id: str, status: EpisodeStatus, error: str | None = None
    ) -> None:
        row = await self.s.get(m.EpisodeRow, episode_id)
        if row is None:
            raise KeyError(episode_id)
        row.status = status.value
        row.error = error
        await self.s.flush()

    async def set_title(self, episode_id: str, title: str) -> None:
        row = await self.s.get(m.EpisodeRow, episode_id)
        if row is None:
            raise KeyError(episode_id)
        row.title = title
        await self.s.flush()

    async def set_audio(
        self, episode_id: str, audio_key: str, duration_seconds: float
    ) -> None:
        row = await self.s.get(m.EpisodeRow, episode_id)
        if row is None:
            raise KeyError(episode_id)
        row.audio_key = audio_key
        row.duration_seconds = duration_seconds
        await self.s.flush()


class SqlTranscriptRepository(TranscriptRepository):
    def __init__(self, session: AsyncSession):
        self.s = session

    async def save(self, transcript: Transcript) -> None:
        segments = [
            {"speaker": seg.speaker, "text": seg.text, "start_seconds": seg.start_seconds}
            for seg in transcript.segments
        ]
        row = await self.s.get(m.TranscriptRow, transcript.episode_id)
        if row is None:
            row = m.TranscriptRow(episode_id=transcript.episode_id, segments=segments)
            self.s.add(row)
        else:
            row.segments = segments
        await self.s.flush()

    async def get_for_episode(self, episode_id: str) -> Transcript | None:
        row = await self.s.get(m.TranscriptRow, episode_id)
        if row is None:
            return None
        return Transcript(
            episode_id=row.episode_id,
            segments=[TranscriptSegment(**seg) for seg in (row.segments or [])],
        )


class SqlFeedbackRepository(FeedbackRepository):
    def __init__(self, session: AsyncSession):
        self.s = session

    async def add(self, event: FeedbackEvent) -> None:
        row = m.FeedbackEventRow(
            user_id=event.user_id,
            episode_id=event.episode_id,
            type=event.type.value,
            position_seconds=event.position_seconds,
        )
        if event.id:
            row.id = event.id
        self.s.add(row)
        await self.s.flush()

    async def list_for_user(
        self, user_id: str, limit: int = 500
    ) -> list[FeedbackEvent]:
        rows = (
            await self.s.execute(
                select(m.FeedbackEventRow)
                .where(m.FeedbackEventRow.user_id == user_id)
                .order_by(m.FeedbackEventRow.created_at.desc())
                .limit(limit)
            )
        ).scalars()
        return [
            FeedbackEvent(
                id=r.id,
                user_id=r.user_id,
                episode_id=r.episode_id,
                type=FeedbackType(r.type),
                position_seconds=r.position_seconds,
                created_at=r.created_at,
            )
            for r in rows
        ]


class SqlConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self.s = session

    async def add(self, conversation: Conversation) -> None:
        row = m.ConversationRow(
            user_id=conversation.user_id,
            episode_id=conversation.episode_id,
            question_text=conversation.question_text,
            answer_text=conversation.answer_text,
        )
        if conversation.id:
            row.id = conversation.id
        self.s.add(row)
        await self.s.flush()

    async def list_for_user(
        self, user_id: str, limit: int = 500
    ) -> list[Conversation]:
        rows = (
            await self.s.execute(
                select(m.ConversationRow)
                .where(m.ConversationRow.user_id == user_id)
                .order_by(m.ConversationRow.created_at.desc())
                .limit(limit)
            )
        ).scalars()
        return [
            Conversation(
                id=r.id,
                user_id=r.user_id,
                episode_id=r.episode_id,
                question_text=r.question_text,
                answer_text=r.answer_text,
                created_at=r.created_at,
            )
            for r in rows
        ]


class SqlTopicSignalRepository(TopicSignalRepository):
    def __init__(self, session: AsyncSession):
        self.s = session

    async def upsert(self, signal: TopicSignal) -> None:
        row = await self.s.get(
            m.TopicSignalRow, (signal.user_id, signal.topic_cluster)
        )
        if row is None:
            row = m.TopicSignalRow(
                user_id=signal.user_id,
                topic_cluster=signal.topic_cluster,
                weight=signal.weight,
                source=signal.source.value,
            )
            self.s.add(row)
        else:
            row.weight = signal.weight
            row.source = signal.source.value
        await self.s.flush()

    async def list_for_user(self, user_id: str) -> list[TopicSignal]:
        rows = (
            await self.s.execute(
                select(m.TopicSignalRow).where(m.TopicSignalRow.user_id == user_id)
            )
        ).scalars()
        return [
            TopicSignal(
                user_id=r.user_id,
                topic_cluster=r.topic_cluster,
                weight=r.weight,
                source=SignalSource(r.source),
                updated_at=r.updated_at,
            )
            for r in rows
        ]

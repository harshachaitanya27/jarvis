"""Generation job runner — turns a user's topics into finished episodes.

Composition happens here: decrypt the user's BYO keys, build the LLM/TTS
adapters they configured, create episode rows, and drive each through the
GenerationService. The provider builders are injected so this is testable with
fakes and swappable in production.
"""

import logging
from collections.abc import Callable

from app.config import Settings, get_settings
from app.core.interfaces.database import (
    EpisodeRepository,
    TranscriptRepository,
    UserRepository,
)
from app.core.interfaces.llm import EpisodeFormat, LLMProvider
from app.core.interfaces.storage import StorageProvider
from app.core.interfaces.tts import TTSProvider
from app.core.providers import build_llm as _build_llm
from app.core.providers import build_tts as _build_tts
from app.domain.entities import Episode, User
from app.services.generation import GenerationService
from app.services.users import UserService
from app.tracing import get_tracer

log = logging.getLogger(__name__)
tracer = get_tracer(__name__)

LLMBuilder = Callable[[str, str], LLMProvider]
TTSBuilder = Callable[[str, str], TTSProvider]


def select_episode_topics(user: User, count: int) -> list[list[str]]:
    """Pick the topic sets for tonight's episodes — one per interest, capped.

    A deliberately simple V1 policy; the V3 bandit replaces this with taste-
    driven selection.
    """
    topics = user.onboarding_topics or []
    return [[t] for t in topics[:count]]


class GenerationJobRunner:
    def __init__(
        self,
        episodes: EpisodeRepository,
        transcripts: TranscriptRepository,
        storage: StorageProvider,
    ):
        self.episodes = episodes
        self.gen = GenerationService(episodes, transcripts, storage)

    async def run_for_user(
        self,
        user: User,
        llm: LLMProvider,
        tts: TTSProvider,
        count: int,
        fmt: EpisodeFormat = "narration",
        minutes: int = 10,
    ) -> list[Episode]:
        """Create and generate this user's episodes; skip failures individually."""
        topic_sets = select_episode_topics(user, count)
        log.info("generating %d episode(s) for user %s", len(topic_sets), user.id)
        produced: list[Episode] = []
        with tracer.start_as_current_span("jobs.run_for_user") as span:
            span.set_attribute("user.id", user.id)
            span.set_attribute("episodes.requested", len(topic_sets))
            for topics in topic_sets:
                episode = await self.episodes.create(
                    Episode(id="", user_id=user.id, topics=topics)
                )
                try:
                    # generation.run opens its own child span under this one.
                    await self.gen.run(
                        episode, llm, tts, fmt=fmt, target_minutes=minutes
                    )
                    produced.append(episode)
                except Exception:  # noqa: BLE001 - one bad episode shouldn't stop the batch
                    log.exception("episode %s failed for user %s", episode.id, user.id)
            span.set_attribute("episodes.produced", len(produced))
        log.info(
            "user %s: %d/%d episode(s) produced", user.id, len(produced), len(topic_sets)
        )
        return produced


async def generate_for_user(
    user: User,
    *,
    runner: GenerationJobRunner,
    user_service: UserService,
    settings: Settings | None = None,
    build_llm: LLMBuilder = _build_llm,
    build_tts: TTSBuilder = _build_tts,
    count: int | None = None,
    fmt: EpisodeFormat = "narration",
    minutes: int | None = None,
) -> list[Episode]:
    """Build the user's providers from their stored keys, then run generation.

    Raises ``KeyError`` if the user has no key for the configured default
    provider (caller decides whether to skip them).
    """
    s = settings or get_settings()
    log.debug(
        "building providers for user %s (llm=%s, tts=%s)",
        user.id,
        s.default_llm_provider,
        s.default_tts_provider,
    )
    llm = build_llm(s.default_llm_provider, user_service.decrypt_key(user, s.default_llm_provider))
    tts = build_tts(s.default_tts_provider, user_service.decrypt_key(user, s.default_tts_provider))
    return await runner.run_for_user(
        user,
        llm,
        tts,
        count=count or s.default_episodes_per_night,
        fmt=fmt,
        minutes=minutes or s.default_episode_minutes,
    )


async def generate_for_user_id(user_id: str) -> None:
    """Load a user in a fresh session and run generation for them.

    Self-contained (opens its own DB session + real adapters), so it can run as
    a background task (the "generate now" endpoint) or from the CLI. Swallows a
    missing-key error — the caller validates that separately.
    """
    from app.adapters.db.repositories import (
        SqlEpisodeRepository,
        SqlTranscriptRepository,
        SqlUserRepository,
    )
    from app.adapters.db.session import SessionFactory
    from app.core.providers import build_storage
    from app.services.crypto import KeyVault

    async with SessionFactory() as session:
        users = SqlUserRepository(session)
        user = await users.get(user_id)
        if user is None:
            log.warning("generate_for_user_id: no such user %s", user_id)
            return
        runner = GenerationJobRunner(
            SqlEpisodeRepository(session),
            SqlTranscriptRepository(session),
            build_storage(),
        )
        user_service = UserService(users, KeyVault())
        try:
            await generate_for_user(user, runner=runner, user_service=user_service)
        except KeyError as exc:
            log.warning("generate_for_user_id: user %s skipped — %s", user_id, exc)
        await session.commit()

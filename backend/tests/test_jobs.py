"""Job runner tests using fakes — no network, no real keys."""

import asyncio

from cryptography.fernet import Fernet

from app.adapters.storage.local import LocalStorageProvider
from app.config import Settings
from app.core.interfaces.database import EpisodeRepository, TranscriptRepository
from app.core.interfaces.llm import LLMProvider, ResearchBrief, Script, ScriptSegment
from app.core.interfaces.tts import SynthesisResult, TTSProvider
from app.domain.entities import Episode, EpisodeStatus, User
from app.services.crypto import KeyVault
from app.services.jobs import (
    GenerationJobRunner,
    generate_for_user,
    select_episode_topics,
)
from app.services.users import UserService

# ── fakes ─────────────────────────────────────────────────────────


class FakeLLM(LLMProvider):
    async def research(self, topic): return ResearchBrief(topic, "s", ["k"], [])

    async def generate_script(self, brief, fmt, target_minutes):
        return Script(title=f"T:{brief.topic}", segments=[ScriptSegment("host", "hi there")])

    async def answer(self, question, context): return "a"


class FakeTTS(TTSProvider):
    async def synthesize(self, text, voice):
        return SynthesisResult(audio=b"audio", content_type="audio/mpeg")

    async def voices(self): return ["alloy"]


class MemEpisodes(EpisodeRepository):
    def __init__(self):
        self.items: dict[str, Episode] = {}
        self._n = 0

    async def create(self, episode):
        self._n += 1
        episode.id = episode.id or f"e{self._n}"
        self.items[episode.id] = episode
        return episode

    async def get(self, episode_id): return self.items.get(episode_id)
    async def list_for_user(self, user_id, limit=50):
        return [e for e in self.items.values() if e.user_id == user_id]

    async def set_status(self, episode_id, status, error=None):
        self.items[episode_id].status = status
        self.items[episode_id].error = error

    async def set_title(self, episode_id, title):
        self.items[episode_id].title = title

    async def set_audio(self, episode_id, audio_key, duration_seconds):
        self.items[episode_id].audio_key = audio_key
        self.items[episode_id].duration_seconds = duration_seconds


class MemTranscripts(TranscriptRepository):
    async def save(self, transcript): pass
    async def get_for_episode(self, episode_id): return None


# ── tests ─────────────────────────────────────────────────────────


def test_select_episode_topics_caps_and_splits():
    user = User(id="u", onboarding_topics=["a", "b", "c", "d"])
    assert select_episode_topics(user, 2) == [["a"], ["b"]]
    assert select_episode_topics(User(id="u"), 3) == []


def test_run_for_user_produces_ready_episodes(tmp_path):
    episodes = MemEpisodes()
    runner = GenerationJobRunner(episodes, MemTranscripts(), LocalStorageProvider(str(tmp_path)))
    user = User(id="u1", onboarding_topics=["x", "y", "z"])

    produced = asyncio.run(runner.run_for_user(user, FakeLLM(), FakeTTS(), count=2))

    assert len(produced) == 2
    assert all(e.status == EpisodeStatus.READY for e in produced)
    assert all(e.audio_key for e in produced)


def test_run_for_user_isolates_a_failing_episode(tmp_path):
    class FlakyTTS(FakeTTS):
        def __init__(self): self.calls = 0

        async def synthesize(self, text, voice):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")
            return await super().synthesize(text, voice)

    episodes = MemEpisodes()
    runner = GenerationJobRunner(episodes, MemTranscripts(), LocalStorageProvider(str(tmp_path)))
    user = User(id="u1", onboarding_topics=["x", "y"])

    produced = asyncio.run(runner.run_for_user(user, FakeLLM(), FlakyTTS(), count=2))

    assert len(produced) == 1  # second episode still made it
    statuses = {e.status for e in episodes.items.values()}
    assert statuses == {EpisodeStatus.READY, EpisodeStatus.FAILED}


def test_generate_for_user_builds_providers_from_stored_key(tmp_path):
    vault = KeyVault(Fernet.generate_key().decode())
    user = User(
        id="u1",
        onboarding_topics=["x"],
        provider_keys_encrypted={"openai": vault.encrypt("sk-123")},
    )
    user_service = UserService(users=None, key_vault=vault)  # decrypt_key ignores repo
    runner = GenerationJobRunner(
        MemEpisodes(), MemTranscripts(), LocalStorageProvider(str(tmp_path))
    )
    settings = Settings(
        default_llm_provider="openai",
        default_tts_provider="openai",
        default_episodes_per_night=1,
        default_episode_minutes=5,
    )

    seen: dict[str, tuple] = {}

    def fake_build_llm(name, key): seen["llm"] = (name, key); return FakeLLM()
    def fake_build_tts(name, key): seen["tts"] = (name, key); return FakeTTS()

    produced = asyncio.run(
        generate_for_user(
            user,
            runner=runner,
            user_service=user_service,
            settings=settings,
            build_llm=fake_build_llm,
            build_tts=fake_build_tts,
        )
    )

    assert len(produced) == 1
    assert seen["llm"] == ("openai", "sk-123")  # decrypted key reached the builder
    assert seen["tts"] == ("openai", "sk-123")

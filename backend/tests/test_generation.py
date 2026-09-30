"""Pipeline tests using fakes — no network, no API keys.

Exercises GenerationService against in-memory repositories, fake LLM/TTS
adapters, and the real local storage provider, so the state machine and
outputs are verified deterministically.
"""

import asyncio

import pytest

from app.adapters.storage.local import LocalStorageProvider
from app.core.interfaces.database import EpisodeRepository, TranscriptRepository
from app.core.interfaces.llm import (
    LLMProvider,
    ResearchBrief,
    Script,
    ScriptSegment,
)
from app.core.interfaces.tts import SynthesisResult, TTSProvider
from app.domain.entities import Episode, EpisodeStatus, Transcript
from app.services.generation import GenerationService

# ── fakes ─────────────────────────────────────────────────────────


class FakeLLM(LLMProvider):
    async def research(self, topic: str) -> ResearchBrief:
        return ResearchBrief(topic, f"summary of {topic}", ["p1", "p2"], ["http://s"])

    async def generate_script(self, brief, fmt, target_minutes) -> Script:
        return Script(
            title=f"Ep: {brief.topic}",
            segments=[
                ScriptSegment("host", "Hello world."),
                ScriptSegment("host", "More words here today."),
            ],
            show_notes="notes",
        )

    async def answer(self, question: str, context: str) -> str:
        return "an answer"


class FakeTTS(TTSProvider):
    async def synthesize(self, text: str, voice: str) -> SynthesisResult:
        return SynthesisResult(audio=f"[{voice}:{text}]".encode(), content_type="audio/mpeg")

    async def voices(self) -> list[str]:
        return ["alloy"]


class MemEpisodes(EpisodeRepository):
    def __init__(self, episode: Episode):
        self.by_id = {episode.id: episode}
        self.status_history: list[EpisodeStatus] = []

    async def create(self, episode): self.by_id[episode.id] = episode; return episode
    async def get(self, episode_id): return self.by_id.get(episode_id)
    async def list_for_user(self, user_id, limit=50): return list(self.by_id.values())

    async def set_status(self, episode_id, status, error=None):
        ep = self.by_id[episode_id]
        ep.status = status
        ep.error = error
        self.status_history.append(status)

    async def set_title(self, episode_id, title):
        self.by_id[episode_id].title = title

    async def set_audio(self, episode_id, audio_key, duration_seconds):
        ep = self.by_id[episode_id]
        ep.audio_key = audio_key
        ep.duration_seconds = duration_seconds


class MemTranscripts(TranscriptRepository):
    def __init__(self):
        self.saved: Transcript | None = None

    async def save(self, transcript): self.saved = transcript
    async def get_for_episode(self, episode_id): return self.saved


# ── tests ─────────────────────────────────────────────────────────


def test_pipeline_produces_ready_episode(tmp_path):
    ep = Episode(id="e1", user_id="u1", topics=["space"])
    episodes, transcripts = MemEpisodes(ep), MemTranscripts()
    storage = LocalStorageProvider(str(tmp_path))
    svc = GenerationService(episodes, transcripts, storage)

    result = asyncio.run(
        svc.run(ep, FakeLLM(), FakeTTS(), fmt="narration", target_minutes=5)
    )

    assert result.status == EpisodeStatus.READY
    assert result.title == "Ep: space"
    assert result.audio_key == "u1/e1.mp3"
    assert result.duration_seconds and result.duration_seconds > 0

    # audio actually written and contains both voiced segments
    data = asyncio.run(storage.get("u1/e1.mp3"))
    assert b"[alloy:Hello world.]" in data
    assert b"[alloy:More words here today.]" in data

    # transcript persisted with both segments
    assert transcripts.saved is not None
    assert len(transcripts.saved.segments) == 2

    # states walked in order, ending READY
    assert episodes.status_history == [
        EpisodeStatus.RESEARCHING,
        EpisodeStatus.SCRIPTING,
        EpisodeStatus.VOICING,
        EpisodeStatus.ASSEMBLING,
        EpisodeStatus.READY,
    ]


def test_pipeline_marks_failed_on_error(tmp_path):
    class BoomLLM(FakeLLM):
        async def generate_script(self, brief, fmt, target_minutes):
            raise RuntimeError("boom")

    ep = Episode(id="e2", user_id="u1", topics=["x"])
    episodes, transcripts = MemEpisodes(ep), MemTranscripts()
    svc = GenerationService(episodes, transcripts, LocalStorageProvider(str(tmp_path)))

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(svc.run(ep, BoomLLM(), FakeTTS()))

    assert ep.status == EpisodeStatus.FAILED
    assert ep.error == "boom"


def test_conversation_format_maps_two_voices(tmp_path):
    captured: list[str] = []

    class TwoSpeakerLLM(FakeLLM):
        async def generate_script(self, brief, fmt, target_minutes):
            return Script(
                title="Chat",
                segments=[
                    ScriptSegment("host", "Hi."),
                    ScriptSegment("cohost", "Hello back."),
                ],
            )

    class RecordingTTS(FakeTTS):
        async def synthesize(self, text, voice):
            captured.append(voice)
            return await super().synthesize(text, voice)

    ep = Episode(id="e3", user_id="u1", topics=["y"])
    svc = GenerationService(
        MemEpisodes(ep), MemTranscripts(), LocalStorageProvider(str(tmp_path))
    )
    asyncio.run(svc.run(ep, TwoSpeakerLLM(), RecordingTTS(), fmt="conversation"))

    assert captured == ["alloy", "onyx"]  # host, cohost mapped to distinct voices

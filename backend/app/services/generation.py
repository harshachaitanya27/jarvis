"""The overnight generation pipeline.

Drives one episode through its states — researching → scripting → voicing →
assembling → ready — using only the provider and repository interfaces. It
never imports a vendor: the caller passes already-built LLM/TTS adapters, so
this stays unit-testable with fakes and swappable in production.
"""

import logging
import time

from app.core.interfaces.database import EpisodeRepository, TranscriptRepository
from app.core.interfaces.llm import (
    EpisodeFormat,
    LLMProvider,
    ResearchBrief,
    Script,
)
from app.core.interfaces.storage import StorageProvider
from app.core.interfaces.tts import TTSProvider
from app.domain.entities import (
    Episode,
    EpisodeStatus,
    Transcript,
    TranscriptSegment,
)
from app.services.audio import assemble, estimate_duration_seconds
from app.tracing import Status, StatusCode, get_tracer

log = logging.getLogger(__name__)
tracer = get_tracer(__name__)

DEFAULT_VOICE = "alloy"
CONVERSATION_VOICES = {"host": "alloy", "cohost": "onyx"}


class GenerationService:
    def __init__(
        self,
        episodes: EpisodeRepository,
        transcripts: TranscriptRepository,
        storage: StorageProvider,
    ):
        self.episodes = episodes
        self.transcripts = transcripts
        self.storage = storage

    async def run(
        self,
        episode: Episode,
        llm: LLMProvider,
        tts: TTSProvider,
        fmt: EpisodeFormat = "narration",
        target_minutes: int = 10,
        voices: dict[str, str] | None = None,
    ) -> Episode:
        """Produce audio for ``episode``; update its row at each state.

        On any failure the episode is marked FAILED with the reason and the
        exception re-raised so a job runner can record it.
        """
        started = time.perf_counter()
        log.info(
            "generating episode %s (user=%s, fmt=%s, topics=%s)",
            episode.id,
            episode.user_id,
            fmt,
            episode.topics,
        )
        with tracer.start_as_current_span("generation.run") as span:
            span.set_attribute("episode.id", episode.id)
            span.set_attribute("user.id", episode.user_id)
            span.set_attribute("episode.format", fmt)
            span.set_attribute("episode.target_minutes", target_minutes)
            try:
                await self.episodes.set_status(episode.id, EpisodeStatus.RESEARCHING)
                log.debug(
                    "researching %d topic(s) for %s", len(episode.topics), episode.id
                )
                with tracer.start_as_current_span("generation.research") as s:
                    s.set_attribute("topic.count", len(episode.topics))
                    brief = await self._research(llm, episode.topics)

                await self.episodes.set_status(episode.id, EpisodeStatus.SCRIPTING)
                log.debug("scripting %s (~%d min)", episode.id, target_minutes)
                with tracer.start_as_current_span("generation.script"):
                    script = await llm.generate_script(brief, fmt, target_minutes)
                await self.episodes.set_title(episode.id, script.title)

                await self.episodes.set_status(episode.id, EpisodeStatus.VOICING)
                log.debug(
                    "voicing %d segment(s) for %s", len(script.segments), episode.id
                )
                with tracer.start_as_current_span("generation.voice") as s:
                    s.set_attribute("segment.count", len(script.segments))
                    results = []
                    for seg in script.segments:
                        voice = self._voice_for(seg.speaker, voices)
                        results.append(await tts.synthesize(seg.text, voice))

                await self.episodes.set_status(episode.id, EpisodeStatus.ASSEMBLING)
                with tracer.start_as_current_span("generation.assemble"):
                    audio, content_type, duration = assemble(results)
                    if duration is None:
                        duration = estimate_duration_seconds(
                            " ".join(s.text for s in script.segments)
                        )
                    key = f"{episode.user_id}/{episode.id}.mp3"
                    await self.storage.put(key, audio, content_type)
                    await self.transcripts.save(_to_transcript(episode.id, script))

                await self.episodes.set_audio(episode.id, key, duration)
                await self.episodes.set_status(episode.id, EpisodeStatus.READY)

                episode.title = script.title
                episode.audio_key = key
                episode.duration_seconds = duration
                episode.status = EpisodeStatus.READY
                span.set_attribute("episode.duration_seconds", duration)
                span.set_attribute("episode.segments", len(script.segments))
                log.info(
                    "episode %s ready: %r (%.1fs audio, %d segments) in %.1fs",
                    episode.id,
                    script.title,
                    duration,
                    len(script.segments),
                    time.perf_counter() - started,
                )
                return episode

            except Exception as exc:  # noqa: BLE001 - record then re-raise
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                log.exception(
                    "generation failed for episode %s after %.1fs",
                    episode.id,
                    time.perf_counter() - started,
                )
                await self.episodes.set_status(
                    episode.id, EpisodeStatus.FAILED, error=str(exc)
                )
                raise

    async def _research(
        self, llm: LLMProvider, topics: list[str]
    ) -> ResearchBrief:
        briefs = [await llm.research(t) for t in topics]
        if len(briefs) == 1:
            return briefs[0]
        return ResearchBrief(
            topic=", ".join(topics),
            summary="\n\n".join(b.summary for b in briefs),
            key_points=[p for b in briefs for p in b.key_points],
            sources=[s for b in briefs for s in b.sources],
        )

    @staticmethod
    def _voice_for(speaker: str, voices: dict[str, str] | None) -> str:
        if voices and speaker in voices:
            return voices[speaker]
        return CONVERSATION_VOICES.get(speaker, DEFAULT_VOICE)


def _to_transcript(episode_id: str, script: Script) -> Transcript:
    return Transcript(
        episode_id=episode_id,
        segments=[
            TranscriptSegment(speaker=s.speaker, text=s.text) for s in script.segments
        ],
    )

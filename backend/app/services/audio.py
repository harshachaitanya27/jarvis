"""Assemble per-segment TTS output into a single episode file.

MVP concatenation of encoded audio bytes — adequate for MP3 playback and
dependency-free. A future version can re-encode with ffmpeg for gapless joins
and precise duration. Duration is summed when the provider reports it, else the
caller supplies an estimate.
"""

from app.core.interfaces.tts import SynthesisResult

# Average speaking pace for estimating duration from text when unknown.
WORDS_PER_MINUTE = 150


def assemble(results: list[SynthesisResult]) -> tuple[bytes, str, float | None]:
    """Concatenate segment audio; return (bytes, content_type, duration_or_None)."""
    if not results:
        return b"", "audio/mpeg", 0.0
    audio = b"".join(r.audio for r in results)
    content_type = results[0].content_type
    durations = [r.duration_seconds for r in results]
    total = sum(durations) if all(d is not None for d in durations) else None
    return audio, content_type, total


def estimate_duration_seconds(text: str) -> float:
    """Fallback episode length from word count at a typical speaking pace."""
    words = len(text.split())
    return round(words / WORDS_PER_MINUTE * 60, 1)

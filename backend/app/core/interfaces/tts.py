"""Text-to-speech contract: render text to audio.

ElevenLabs, OpenAI TTS, or a future in-house voice each implement this.
The dominant cost/latency step in the pipeline, so kept deliberately small.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SynthesisResult:
    audio: bytes
    content_type: str  # e.g. "audio/mpeg"
    duration_seconds: float | None = None


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> SynthesisResult:
        """Render ``text`` in ``voice`` to audio bytes."""
        ...

    @abstractmethod
    async def voices(self) -> list[str]:
        """List voice ids this provider offers."""
        ...

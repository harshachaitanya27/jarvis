"""Speech-to-text contract: transcribe a listener's spoken question (V2).

Whisper, Deepgram, or a future in-house model each implement this. Not used in
the V1 generation pipeline — it powers interactive Q&A only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Transcription:
    text: str
    language: str | None = None
    confidence: float | None = None


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, content_type: str) -> Transcription:
        """Transcribe spoken audio to text."""
        ...

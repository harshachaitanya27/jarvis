"""LLM contract: research a topic, then write an episode script.

OpenAI, Anthropic, Gemini, or a future in-house model each implement this.
The generation pipeline depends only on this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

EpisodeFormat = Literal["narration", "conversation"]


@dataclass
class ResearchBrief:
    """Grounded material a script is written from."""

    topic: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # URLs, grounding refs


@dataclass
class ScriptSegment:
    """One spoken chunk. ``speaker`` distinguishes voices in conversation format."""

    speaker: str  # e.g. "host", "cohost", or a voice id
    text: str


@dataclass
class Script:
    """A full episode script, ready to voice segment by segment."""

    title: str
    segments: list[ScriptSegment]
    show_notes: str = ""


class LLMProvider(ABC):
    @abstractmethod
    async def research(self, topic: str) -> ResearchBrief:
        """Gather grounded material for ``topic``."""
        ...

    @abstractmethod
    async def generate_script(
        self,
        brief: ResearchBrief,
        fmt: EpisodeFormat,
        target_minutes: int,
    ) -> Script:
        """Write an episode script from a brief, sized to ``target_minutes``."""
        ...

    @abstractmethod
    async def answer(self, question: str, context: str) -> str:
        """Answer a listener question, grounded in ``context`` (V2 Q&A)."""
        ...

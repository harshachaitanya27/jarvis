"""Anthropic implementation of LLMProvider (the Messages API).

Talks to /v1/messages over httpx so the adapter carries no vendor SDK — the
same shape as the OpenAI adapter, so the pipeline is unaware which is in use.
An httpx client can be injected for offline testing.
"""

import json

import httpx

from app.adapters.errors import raise_for_provider
from app.core.interfaces.llm import (
    EpisodeFormat,
    LLMProvider,
    ResearchBrief,
    Script,
    ScriptSegment,
)

_API = "https://api.anthropic.com/v1/messages"
_VERSION = "2023-06-01"


def _extract_json(text: str) -> dict:
    """Parse a JSON object from a model reply, tolerating surrounding prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


class AnthropicLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-8",
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._key = api_key
        self._model = model
        self._timeout = timeout
        self._client = client

    async def _post(self, payload: dict) -> dict:
        headers = {
            "x-api-key": self._key,
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }
        if self._client is not None:
            resp = await self._client.post(_API, headers=headers, json=payload)
            raise_for_provider(resp, "Anthropic")
            return resp.json()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(_API, headers=headers, json=payload)
            raise_for_provider(resp, "Anthropic")
            return resp.json()

    async def _message(self, system: str, user: str, max_tokens: int) -> str:
        data = await self._post(
            {
                "model": self._model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
        )
        return "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )

    async def research(self, topic: str) -> ResearchBrief:
        text = await self._message(
            system="You are a podcast researcher. Reply with ONLY a JSON object: "
            '{"summary": str, "key_points": [str], "sources": [str]}. No other text.',
            user=f"Research this topic: {topic}",
            max_tokens=2000,
        )
        data = _extract_json(text)
        return ResearchBrief(
            topic=topic,
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
            sources=data.get("sources", []),
        )

    async def generate_script(
        self, brief: ResearchBrief, fmt: EpisodeFormat, target_minutes: int
    ) -> Script:
        style = (
            "a single narrator" if fmt == "narration" else "a host and cohost dialogue"
        )
        text = await self._message(
            system="You write podcast scripts. Reply with ONLY a JSON object: "
            '{"title": str, "segments": [{"speaker": str, "text": str}], '
            '"show_notes": str}. For narration use speaker "host"; for conversation '
            'alternate "host" and "cohost". No other text.',
            user=(
                f"Write a ~{target_minutes} minute episode as {style} on "
                f"'{brief.topic}'.\nSummary: {brief.summary}\n"
                f"Key points: {'; '.join(brief.key_points)}"
            ),
            max_tokens=8000,
        )
        data = _extract_json(text)
        return Script(
            title=data.get("title", brief.topic),
            segments=[
                ScriptSegment(speaker=s.get("speaker", "host"), text=s.get("text", ""))
                for s in data.get("segments", [])
            ],
            show_notes=data.get("show_notes", ""),
        )

    async def answer(self, question: str, context: str) -> str:
        return await self._message(
            system="Answer the listener's question briefly, grounded only in the "
            "provided episode context.",
            user=f"Context:\n{context}\n\nQ: {question}",
            max_tokens=1024,
        )

"""OpenAI implementation of LLMProvider.

Talks to the Chat Completions API over httpx so the adapter carries no vendor
SDK. Research and scripting request JSON and parse it into domain value objects.
"""

import json

import httpx

from app.core.interfaces.llm import (
    EpisodeFormat,
    LLMProvider,
    ResearchBrief,
    Script,
    ScriptSegment,
)

_API = "https://api.openai.com/v1/chat/completions"


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: float = 60.0):
        self._key = api_key
        self._model = model
        self._timeout = timeout

    async def _chat(self, messages: list[dict], json_mode: bool = False) -> str:
        payload: dict = {"model": self._model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                _API,
                headers={"Authorization": f"Bearer {self._key}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def research(self, topic: str) -> ResearchBrief:
        content = await self._chat(
            [
                {
                    "role": "system",
                    "content": "You are a podcast researcher. Reply with JSON: "
                    '{"summary": str, "key_points": [str], "sources": [str]}.',
                },
                {"role": "user", "content": f"Research this topic: {topic}"},
            ],
            json_mode=True,
        )
        data = json.loads(content)
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
            "a single narrator" if fmt == "narration" else "a host and cohort dialogue"
        )
        content = await self._chat(
            [
                {
                    "role": "system",
                    "content": "You write podcast scripts. Reply with JSON: "
                    '{"title": str, "segments": [{"speaker": str, "text": str}], '
                    '"show_notes": str}. For narration use speaker "host"; for '
                    'conversation alternate "host" and "cohost".',
                },
                {
                    "role": "user",
                    "content": (
                        f"Write a ~{target_minutes} minute episode as {style} on "
                        f"'{brief.topic}'.\nSummary: {brief.summary}\n"
                        f"Key points: {'; '.join(brief.key_points)}"
                    ),
                },
            ],
            json_mode=True,
        )
        data = json.loads(content)
        return Script(
            title=data.get("title", brief.topic),
            segments=[
                ScriptSegment(speaker=s.get("speaker", "host"), text=s.get("text", ""))
                for s in data.get("segments", [])
            ],
            show_notes=data.get("show_notes", ""),
        )

    async def answer(self, question: str, context: str) -> str:
        return await self._chat(
            [
                {
                    "role": "system",
                    "content": "Answer the listener's question briefly, grounded only "
                    "in the provided episode context.",
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQ: {question}"},
            ]
        )

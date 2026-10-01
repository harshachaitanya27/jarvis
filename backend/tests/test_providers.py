"""Adapter tests for Anthropic (LLM) and ElevenLabs (TTS).

Uses httpx.MockTransport to assert request shape and response parsing without
any network calls or real keys.
"""

import asyncio
import json

import httpx
import pytest

from app.adapters.errors import ProviderError
from app.adapters.llm.anthropic import AnthropicLLMProvider
from app.adapters.llm.openai import OpenAILLMProvider
from app.adapters.tts.elevenlabs import ElevenLabsTTSProvider
from app.adapters.tts.openai import OpenAITTSProvider
from app.core.interfaces.llm import ResearchBrief


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ── Anthropic LLM ─────────────────────────────────────────────────


def test_anthropic_research_shapes_request_and_parses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["api_key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        seen["body"] = json.loads(request.content)
        reply = json.dumps(
            {"summary": "a summary", "key_points": ["p1", "p2"], "sources": ["http://s"]}
        )
        return httpx.Response(200, json={"content": [{"type": "text", "text": reply}]})

    llm = AnthropicLLMProvider("sk-test", model="claude-opus-4-8", client=_client(handler))
    brief = asyncio.run(llm.research("space"))

    assert brief.summary == "a summary"
    assert brief.key_points == ["p1", "p2"]
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["api_key"] == "sk-test"
    assert seen["version"] == "2023-06-01"
    assert seen["body"]["model"] == "claude-opus-4-8"
    assert seen["body"]["max_tokens"] > 0
    assert seen["body"]["messages"][0]["role"] == "user"


def test_anthropic_generate_script_parses_segments():
    def handler(request: httpx.Request) -> httpx.Response:
        reply = json.dumps(
            {
                "title": "Ep One",
                "segments": [
                    {"speaker": "host", "text": "hello"},
                    {"speaker": "cohost", "text": "hi"},
                ],
                "show_notes": "notes",
            }
        )
        return httpx.Response(200, json={"content": [{"type": "text", "text": reply}]})

    llm = AnthropicLLMProvider("sk-test", client=_client(handler))
    script = asyncio.run(
        llm.generate_script(ResearchBrief("space", "s"), "conversation", 5)
    )

    assert script.title == "Ep One"
    assert [s.speaker for s in script.segments] == ["host", "cohost"]
    assert script.segments[0].text == "hello"


def test_anthropic_extracts_json_from_surrounding_prose():
    def handler(request: httpx.Request) -> httpx.Response:
        messy = 'Here is the JSON:\n{"summary": "x", "key_points": [], "sources": []}\nDone.'
        return httpx.Response(200, json={"content": [{"type": "text", "text": messy}]})

    llm = AnthropicLLMProvider("sk-test", client=_client(handler))
    brief = asyncio.run(llm.research("x"))
    assert brief.summary == "x"


# ── ElevenLabs TTS ────────────────────────────────────────────────


def test_elevenlabs_synthesize_posts_to_voice_and_returns_audio():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["api_key"] = request.headers.get("xi-api-key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=b"mp3-bytes")

    tts = ElevenLabsTTSProvider("xi-test", client=_client(handler))
    result = asyncio.run(tts.synthesize("hello world", "voice-123"))

    assert result.audio == b"mp3-bytes"
    assert result.content_type == "audio/mpeg"
    assert seen["url"].endswith("/text-to-speech/voice-123")
    assert seen["api_key"] == "xi-test"
    assert seen["body"]["text"] == "hello world"


def test_elevenlabs_synthesize_falls_back_to_default_voice():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, content=b"x")

    tts = ElevenLabsTTSProvider("xi-test", client=_client(handler))
    asyncio.run(tts.synthesize("hi", ""))
    assert "/text-to-speech/21m00Tcm4TlvDq8ikWAM" in seen["url"]


def test_elevenlabs_voices_lists_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"voices": [{"voice_id": "v1"}, {"voice_id": "v2"}]}
        )

    tts = ElevenLabsTTSProvider("xi-test", client=_client(handler))
    assert asyncio.run(tts.voices()) == ["v1", "v2"]


# ── error-body surfacing ──────────────────────────────────────────


def test_openai_llm_surfaces_provider_error_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "exceeded quota", "code": "insufficient_quota"}},
        )

    llm = OpenAILLMProvider("sk-test", client=_client(handler))
    with pytest.raises(ProviderError) as exc:
        asyncio.run(llm.research("x"))
    msg = str(exc.value)
    assert "OpenAI" in msg and "429" in msg and "insufficient_quota" in msg


def test_openai_tts_surfaces_provider_error_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Incorrect API key provided")

    tts = OpenAITTSProvider("sk-test", client=_client(handler))
    with pytest.raises(ProviderError) as exc:
        asyncio.run(tts.synthesize("hi", "alloy"))
    assert "OpenAI" in str(exc.value) and "401" in str(exc.value)


def test_elevenlabs_surfaces_provider_error_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="voice not found")

    tts = ElevenLabsTTSProvider("xi-test", client=_client(handler))
    with pytest.raises(ProviderError) as exc:
        asyncio.run(tts.synthesize("hi", "bad-voice"))
    assert "ElevenLabs" in str(exc.value) and "422" in str(exc.value)

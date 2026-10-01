"""ElevenLabs implementation of TTSProvider.

Calls the text-to-speech endpoint over httpx and returns MP3 bytes. A voice is
an ElevenLabs voice id; an httpx client can be injected for offline testing.
"""

import httpx

from app.adapters.errors import raise_for_provider
from app.core.interfaces.tts import SynthesisResult, TTSProvider

_BASE = "https://api.elevenlabs.io/v1"
# A default public voice ("Rachel") used when no voice id is supplied.
_DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"


class ElevenLabsTTSProvider(TTSProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "eleven_turbo_v2_5",
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._key = api_key
        self._model = model
        self._timeout = timeout
        self._client = client

    async def synthesize(self, text: str, voice: str) -> SynthesisResult:
        voice_id = voice or _DEFAULT_VOICE
        url = f"{_BASE}/text-to-speech/{voice_id}"
        headers = {"xi-api-key": self._key, "accept": "audio/mpeg"}
        payload = {"text": text, "model_id": self._model}
        if self._client is not None:
            resp = await self._client.post(url, headers=headers, json=payload)
            raise_for_provider(resp, "ElevenLabs")
            return SynthesisResult(audio=resp.content, content_type="audio/mpeg")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            raise_for_provider(resp, "ElevenLabs")
            return SynthesisResult(audio=resp.content, content_type="audio/mpeg")

    async def voices(self) -> list[str]:
        url = f"{_BASE}/voices"
        headers = {"xi-api-key": self._key}
        if self._client is not None:
            resp = await self._client.get(url, headers=headers)
            raise_for_provider(resp, "ElevenLabs")
            data = resp.json()
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=headers)
                raise_for_provider(resp, "ElevenLabs")
                data = resp.json()
        return [v["voice_id"] for v in data.get("voices", [])]

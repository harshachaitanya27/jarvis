"""OpenAI implementation of TTSProvider (the /audio/speech endpoint).

Returns MP3 bytes. The API does not report duration, so it is left unset and
estimated downstream during assembly.
"""

import httpx

from app.core.interfaces.tts import SynthesisResult, TTSProvider

_API = "https://api.openai.com/v1/audio/speech"
_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class OpenAITTSProvider(TTSProvider):
    def __init__(self, api_key: str, model: str = "tts-1", timeout: float = 120.0):
        self._key = api_key
        self._model = model
        self._timeout = timeout

    async def synthesize(self, text: str, voice: str) -> SynthesisResult:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                _API,
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "model": self._model,
                    "voice": voice if voice in _VOICES else _VOICES[0],
                    "input": text,
                    "response_format": "mp3",
                },
            )
            resp.raise_for_status()
            return SynthesisResult(audio=resp.content, content_type="audio/mpeg")

    async def voices(self) -> list[str]:
        return list(_VOICES)

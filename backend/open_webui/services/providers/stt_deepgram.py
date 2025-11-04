"""Deepgram speech-to-text provider."""

from __future__ import annotations

import httpx

from open_webui.services.interfaces import STTService


class DeepgramSTTService(STTService):
    def __init__(
        self,
        api_key: str,
        *,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        content_type: str = "audio/wav",
        **_: object,
    ) -> str:
        params: dict[str, str] = {}
        if self._model:
            params["model"] = self._model
        if language:
            params["language"] = language

        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": content_type,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers=headers,
                params={"smart_format": "true", **params},
                content=audio,
            )
            response.raise_for_status()

        payload = response.json()
        try:
            channels = payload["results"]["channels"]
            alternatives = channels[0]["alternatives"]
            transcript = alternatives[0].get("transcript", "")
            return transcript.strip()
        except (KeyError, IndexError):
            return ""


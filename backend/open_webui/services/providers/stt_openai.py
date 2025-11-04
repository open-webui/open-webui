"""OpenAI Whisper API speech-to-text provider."""

from __future__ import annotations

import httpx

from open_webui.services.interfaces import STTService


class OpenAISTTService(STTService):
    def __init__(
        self,
        api_key: str,
        *,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-transcribe",
        timeout: float = 60.0,
        default_filename: str = "audio.wav",
    ) -> None:
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._default_filename = default_filename

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        filename: str | None = None,
        **_: object,
    ) -> str:
        data = {"model": self._model}
        if language:
            data["language"] = language

        headers = {"Authorization": f"Bearer {self._api_key}"}
        effective_filename = filename or self._default_filename

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._api_base}/audio/transcriptions",
                headers=headers,
                data=data,
                files={
                    "file": (
                        effective_filename,
                        audio,
                        "application/octet-stream",
                    )
                },
            )
            response.raise_for_status()

        payload = response.json()
        text = payload.get("text")
        if not text and "results" in payload:
            text = " ".join(
                alternative.get("text", "")
                for channel in payload["results"].get("channels", [])
                for alternative in channel.get("alternatives", [])
            ).strip()
        return text or ""


"""OpenAI text-to-speech provider."""

from __future__ import annotations

import httpx

from open_webui.services.interfaces import TTSService


class OpenAITTSService(TTSService):
    def __init__(
        self,
        api_key: str,
        *,
        api_base: str = "https://api.openai.com/v1",
        model: str,
        default_voice: str | None = None,
        request_overrides: dict | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._model = model
        self._default_voice = default_voice
        self._request_overrides = request_overrides or {}
        self._timeout = timeout

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        response_format: str | None = None,
        extra: dict | None = None,
        **kwargs: object,
    ) -> bytes:
        payload: dict[str, object] = {
            "model": model or self._model,
            "input": text,
        }
        selected_voice = voice or self._default_voice
        if selected_voice:
            payload["voice"] = selected_voice
        if response_format:
            payload["response_format"] = response_format
        overrides = {**self._request_overrides, **(extra or {}), **kwargs}
        payload.update({k: v for k, v in overrides.items() if v is not None})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._api_base}/audio/speech",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.content

"""Azure Speech-to-Text service provider."""

from __future__ import annotations

import json
import mimetypes

import httpx

from open_webui.services.interfaces import STTService


class AzureSTTService(STTService):
    def __init__(
        self,
        api_key: str,
        *,
        region: str,
        base_url: str | None = None,
        api_version: str = "2024-11-15",
        model: str | None = None,
        locales: str | None = None,
        max_speakers: int = 3,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._region = region
        self._base_url = base_url.rstrip("/") if base_url else None
        self._api_version = api_version
        self._model = model
        self._locales = locales
        self._max_speakers = max_speakers
        self._timeout = timeout

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
        **_: object,
    ) -> str:
        endpoint = self._base_url or f"https://{self._region}.api.cognitive.microsoft.com"
        url = f"{endpoint}/speechtotext/transcriptions:transcribe?api-version={self._api_version}"

        locales = self._locales.split(",") if self._locales else []
        if language and language not in locales:
            locales = [language] + locales

        definition = {
            "diarization": {"enabled": True, "maxSpeakers": self._max_speakers},
        }
        if locales:
            definition["locales"] = locales
        if self._model:
            definition["model"] = {"name": self._model}

        headers = {"Ocp-Apim-Subscription-Key": self._api_key}
        effective_filename = filename or "audio.wav"
        mime = content_type or mimetypes.guess_type(effective_filename)[0] or "audio/wav"

        data = {"definition": json.dumps(definition)}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                data=data,
                files={"audio": (effective_filename, audio, mime)},
            )
            response.raise_for_status()

        payload = response.json()
        combined = payload.get("combinedPhrases")
        if not combined:
            return ""
        primary = combined[0]
        return primary.get("text", "").strip()


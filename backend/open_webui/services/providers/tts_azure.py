"""Azure Cognitive Services text-to-speech provider."""

from __future__ import annotations

from xml.sax.saxutils import escape

import httpx

from open_webui.services.interfaces import TTSService


class AzureTTSService(TTSService):
    def __init__(
        self,
        api_key: str,
        *,
        region: str,
        voice: str,
        base_url: str | None = None,
        output_format: str = "audio-24khz-48kbitrate-mono-mp3",
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._region = region
        self._voice = voice
        self._base_url = base_url.rstrip("/") if base_url else None
        self._output_format = output_format
        self._timeout = timeout

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        style: str | None = None,
        style_degree: str | None = None,
        role: str | None = None,
        **_: object,
    ) -> bytes:
        selected_voice = voice or self._voice
        ssml_body = self._build_ssml(
            selected_voice,
            text,
            style=style,
            style_degree=style_degree,
            role=role,
        )
        endpoint = self._base_url or f"https://{self._region}.tts.speech.microsoft.com"
        url = f"{endpoint}/cognitiveservices/v1"

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": self._output_format,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=headers, content=ssml_body.encode("utf-8"))
            response.raise_for_status()
            return response.content

    def _build_ssml(
        self,
        voice: str,
        text: str,
        *,
        style: str | None,
        style_degree: str | None,
        role: str | None,
    ) -> str:
        escaped_text = escape(text)
        style_tag_start = style_tag_end = ""
        if style:
            style_attrs = f'style="{style}"'
            if style_degree:
                style_attrs += f' styledegree="{style_degree}"'
            if role:
                style_attrs += f' role="{role}"'
            style_tag_start = f"<mstts:express-as {style_attrs}>"
            style_tag_end = "</mstts:express-as>"

        return (
            "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" "
            "xmlns:mstts=\"http://www.w3.org/2001/mstts\" xml:lang=\"en-US\">"
            f"<voice name=\"{voice}\">"
            f"{style_tag_start}{escaped_text}{style_tag_end}"
            "</voice>"
            "</speak>"
        )

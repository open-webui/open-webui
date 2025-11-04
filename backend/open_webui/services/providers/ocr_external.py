"""SaaS OCR service implementations for Azure Document Intelligence and AWS Textract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from open_webui.services.interfaces import OCRService


@dataclass(slots=True)
class AzureDocumentIntelligenceConfig:
    endpoint: str
    api_key: str
    model_id: str = "prebuilt-read"
    api_version: str = "2024-02-29-preview"


class AzureDocumentIntelligenceService(OCRService):
    def __init__(self, config: AzureDocumentIntelligenceConfig, *, timeout: float = 180.0) -> None:
        self._config = config
        self._timeout = timeout

    async def extract(self, image: bytes) -> str:
        url = f"{self._config.endpoint}/documentintelligence/documentModels/{self._config.model_id}:analyze?api-version={self._config.api_version}"
        headers = {
            "Ocp-Apim-Subscription-Key": self._config.api_key,
            "Content-Type": "application/pdf",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=headers, content=image)
            response.raise_for_status()

            # Azure Doc Intelligence returns an operation-location header; poll the result
            operation_location = response.headers.get("operation-location")
            if not operation_location:
                return ""

            result = await self._poll_operation(client, operation_location)
            return self._extract_text(result)

    async def _poll_operation(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        while True:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status in {"succeeded", "failed"}:
                return payload
            await asyncio.sleep(2)

    def _extract_text(self, payload: dict[str, Any]) -> str:
        if payload.get("status") != "succeeded":
            return ""
        content = []
        analyze_result = payload.get("analyzeResult", {})
        for page in analyze_result.get("pages", []):
            for line in page.get("lines", []):
                text = line.get("content")
                if text:
                    content.append(text)
        return "\n".join(content)


@dataclass(slots=True)
class AWSTextractConfig:
    access_key_id: str
    secret_access_key: str
    region: str
    session_token: str | None = None


class AWSTextractService(OCRService):
    def __init__(self, config: AWSTextractConfig, *, timeout: float = 180.0) -> None:
        import boto3

        session_kwargs = {
            "aws_access_key_id": config.access_key_id,
            "aws_secret_access_key": config.secret_access_key,
            "region_name": config.region,
        }
        if config.session_token:
            session_kwargs["aws_session_token"] = config.session_token

        session = boto3.session.Session(**session_kwargs)
        self._client = session.client("textract")
        self._timeout = timeout

    async def extract(self, image: bytes) -> str:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._client.detect_document_text(Document={"Bytes": image}),
        )
        lines: list[str] = []
        for block in result.get("Blocks", []):
            if block.get("BlockType") == "LINE" and block.get("Text"):
                lines.append(block["Text"])
        return "\n".join(lines)


__all__ = [
    "AzureDocumentIntelligenceConfig",
    "AzureDocumentIntelligenceService",
    "AWSTextractConfig",
    "AWSTextractService",
]

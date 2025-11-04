"""Azure OpenAI embedding service implementation."""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

from open_webui.retrieval.utils import generate_azure_openai_batch_embeddings
from open_webui.services.interfaces import EmbeddingService


class AzureOpenAIEmbeddingService(EmbeddingService):
    def __init__(
        self,
        deployment: str,
        *,
        api_base: str,
        api_key: str,
        api_version: str,
    ) -> None:
        self._deployment = deployment
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._api_version = api_version

    async def embed_text(
        self,
        texts: Sequence[str],
        *,
        prefix: str | None = None,
        user: Any | None = None,
        **_: Any,
    ) -> Sequence[Sequence[float]]:
        payload = list(texts)

        def _request() -> Sequence[Sequence[float]]:
            embeddings = generate_azure_openai_batch_embeddings(
                self._deployment,
                payload,
                url=self._api_base,
                key=self._api_key,
                version=self._api_version,
                prefix=prefix,
                user=user,
            )
            if embeddings is None:
                raise RuntimeError("Azure OpenAI embedding request returned no data")
            return embeddings

        return await asyncio.to_thread(_request)


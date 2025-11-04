"""OpenAI embedding service implementation."""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

from open_webui.retrieval.utils import generate_openai_batch_embeddings
from open_webui.services.interfaces import EmbeddingService


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(
        self,
        model: str,
        api_base: str,
        api_key: str,
    ) -> None:
        self._model = model
        self._api_base = api_base.rstrip("/") or "https://api.openai.com/v1"
        self._api_key = api_key

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
            embeddings = generate_openai_batch_embeddings(
                self._model,
                payload,
                url=self._api_base,
                key=self._api_key,
                prefix=prefix,
                user=user,
            )
            if embeddings is None:
                raise RuntimeError("OpenAI embedding request returned no data")
            return embeddings

        return await asyncio.to_thread(_request)


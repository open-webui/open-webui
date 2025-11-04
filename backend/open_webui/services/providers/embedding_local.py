"""Local sentence-transformer embedding service."""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

from open_webui.retrieval.utils import get_model_path
from open_webui.services.interfaces import EmbeddingService


class LocalEmbeddingService(EmbeddingService):
    def __init__(
        self,
        model_name: str,
        *,
        auto_update: bool | None = None,
        trust_remote_code: bool | None = None,
        device: str | None = None,
        backend: str | None = None,
        model_kwargs: dict[str, Any] | None = None,
    ) -> None:
        from open_webui.config import (
            RAG_EMBEDDING_MODEL_AUTO_UPDATE,
            RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
        )
        from open_webui.env import (
            DEVICE_TYPE,
            SENTENCE_TRANSFORMERS_BACKEND,
            SENTENCE_TRANSFORMERS_MODEL_KWARGS,
        )

        self._model_name = model_name
        self._auto_update = (
            auto_update
            if auto_update is not None
            else RAG_EMBEDDING_MODEL_AUTO_UPDATE
        )
        self._trust_remote_code = (
            trust_remote_code
            if trust_remote_code is not None
            else RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE
        )
        self._device = device or DEVICE_TYPE or "cpu"
        self._backend = backend or SENTENCE_TRANSFORMERS_BACKEND
        self._model_kwargs = model_kwargs or SENTENCE_TRANSFORMERS_MODEL_KWARGS
        self._model = None

    async def embed_text(
        self,
        texts: Sequence[str],
        *,
        prefix: str | None = None,
        user: Any | None = None,
        **_: Any,
    ) -> Sequence[Sequence[float]]:
        return await asyncio.to_thread(self._encode, list(texts), prefix)

    def _ensure_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            model_path = get_model_path(self._model_name, self._auto_update)
            self._model = SentenceTransformer(
                model_path,
                device=self._device,
                trust_remote_code=self._trust_remote_code,
                backend=self._backend,
                model_kwargs=self._model_kwargs,
            )
        return self._model

    def _encode(self, texts: list[str], prefix: str | None) -> Sequence[Sequence[float]]:
        model = self._ensure_model()
        prompt_args = {"prompt": prefix} if prefix else {}
        embeddings = model.encode(texts, convert_to_numpy=True, **prompt_args)
        return [embedding.tolist() for embedding in embeddings]


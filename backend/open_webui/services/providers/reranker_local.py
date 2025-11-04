"""Local reranker service backed by sentence-transformers / ColBERT."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence

from open_webui.retrieval.utils import get_model_path
from open_webui.services.interfaces import RerankerService

log = logging.getLogger(__name__)


class LocalRerankerService(RerankerService):
    def __init__(
        self,
        model_name: str,
        *,
        auto_update: bool | None = None,
        trust_remote_code: bool | None = None,
    ) -> None:
        from open_webui.config import (
            RAG_RERANKING_MODEL_AUTO_UPDATE,
            RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
        )

        self._model_name = model_name
        self._auto_update = (
            auto_update
            if auto_update is not None
            else RAG_RERANKING_MODEL_AUTO_UPDATE
        )
        self._trust_remote_code = (
            trust_remote_code
            if trust_remote_code is not None
            else RAG_RERANKING_MODEL_TRUST_REMOTE_CODE
        )
        self._model = None

    async def rerank(
        self,
        query: str,
        documents: Sequence[str],
        *,
        top_k: int | None = None,
        user: Any | None = None,
    ) -> Sequence[float]:
        if not documents:
            return []

        def _run() -> Sequence[float]:
            model = self._ensure_model()
            pairs = [(query, doc) for doc in documents]
            scores = model.predict(pairs)
            if scores is None:
                return []
            if hasattr(scores, "tolist"):
                scores = scores.tolist()
            elif not isinstance(scores, list):
                scores = list(scores)
            return scores

        return await asyncio.to_thread(_run)

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        if self._is_colbert_model(self._model_name):
            self._model = self._load_colbert()
        else:
            self._model = self._load_cross_encoder()
        return self._model

    def _load_cross_encoder(self) -> Any:
        from sentence_transformers import CrossEncoder
        from open_webui.env import (
            DEVICE_TYPE,
            SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
            SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
        )

        model_path = get_model_path(self._model_name, self._auto_update)
        model = CrossEncoder(
            model_path,
            device=DEVICE_TYPE,
            trust_remote_code=self._trust_remote_code,
            backend=SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
            model_kwargs=SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
        )

        try:
            model_cfg = getattr(model, "model", None)
            if model_cfg and hasattr(model_cfg, "config"):
                cfg = model_cfg.config
                if getattr(cfg, "pad_token_id", None) is None:
                    eos = getattr(cfg, "eos_token_id", None)
                    if eos is not None:
                        cfg.pad_token_id = eos
                        log.debug(
                            "Reranker model lacked pad_token_id; defaulted to eos_token_id=%s",
                            eos,
                        )
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Failed to adjust pad_token_id on CrossEncoder: %s", exc)

        return model

    def _load_colbert(self) -> Any:
        from open_webui.env import DOCKER
        from open_webui.retrieval.models.colbert import ColBERT

        model_path = get_model_path(self._model_name, self._auto_update)
        env = "docker" if DOCKER else None
        return ColBERT(model_path, env=env)

    @staticmethod
    def _is_colbert_model(model_name: str) -> bool:
        lowered = model_name.lower()
        return "jinaai/jina-colbert-v2" in lowered or "colbert" in lowered

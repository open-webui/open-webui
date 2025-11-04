"""Synchronous helpers for interacting with async service providers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Sequence

from fastapi import HTTPException, Request

from open_webui.services.dependencies import (
    get_embedding_service,
    get_reranker_service,
)
from open_webui.services.interfaces import EmbeddingService, RerankerService

log = logging.getLogger(__name__)


def _run_sync(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def build_embedding_function(service: EmbeddingService) -> Callable[[Any, Any, Any], Any]:
    def _embed(texts, prefix=None, user=None):
        if isinstance(texts, list):
            embeddings = _run_sync(service.embed_text(texts, prefix=prefix, user=user))
            return [list(vector) for vector in embeddings]
        embeddings = _run_sync(service.embed_text([texts], prefix=prefix, user=user))
        return list(embeddings[0])

    return _embed


def build_reranker_function(service: RerankerService) -> Callable[..., Sequence[float]]:
    def _rerank(sentences, user=None, top_k=None):
        if not sentences:
            return []
        query = sentences[0][0]
        documents = [doc for _, doc in sentences]
        scores = _run_sync(
            service.rerank(query, documents, top_k=top_k, user=user)
        )
        if isinstance(scores, list):
            return scores
        if hasattr(scores, "tolist"):
            return scores.tolist()
        return list(scores)

    return _rerank


def get_sync_embedding_function(request: Request):
    service = get_embedding_service(request)
    return build_embedding_function(service)


def get_sync_reranker_function(request: Request):
    try:
        service = get_reranker_service(request)
    except HTTPException as exc:
        # Treat missing/local-disabled rerankers as optional.
        log.debug("Reranker service unavailable: %s", exc.detail)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Failed to resolve reranker service: %s", exc)
        return None
    return build_reranker_function(service)


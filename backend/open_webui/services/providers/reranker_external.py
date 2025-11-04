"""External reranker service wrapper."""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

from open_webui.retrieval.models.external import ExternalReranker
from open_webui.services.interfaces import RerankerService


class ExternalRerankerService(RerankerService):
    def __init__(self, *, model: str, url: str, api_key: str) -> None:
        self._client = ExternalReranker(api_key=api_key, url=url, model=model)

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
            scores = self._client.predict(
                [(query, doc) for doc in documents],
                user=user,
            )
            if scores is None:
                return []
            if hasattr(scores, "tolist"):
                scores = scores.tolist()
            elif not isinstance(scores, list):
                scores = list(scores)
            return scores

        return await asyncio.to_thread(_run)


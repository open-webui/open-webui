"""
Async facade over the synchronous VECTOR_DB_CLIENT.

The vector DB backends bundled with Open WebUI (Chroma, pgvector, Qdrant,
Milvus, OpenSearch, Pinecone, Weaviate, …) all expose a uniformly
synchronous API. Each method performs blocking network or disk I/O — and
some, like `insert`/`upsert`, can run for several seconds.

When such a sync method is awaited from an async route handler, it blocks
the event loop for its entire duration, freezing every other in-flight
HTTP request, websocket message and background task.

This module wraps the sync client in an `AsyncVectorDBClient` that
transparently dispatches each call to a worker thread via
`asyncio.to_thread`. Async callers can `await ASYNC_VECTOR_DB_CLIENT.x(...)`
in place of `VECTOR_DB_CLIENT.x(...)` and the loop stays responsive.

The original `VECTOR_DB_CLIENT` is unchanged, so callers already running
inside `run_in_threadpool` (e.g. `save_docs_to_vector_db`) are not
affected.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
)


class AsyncVectorDBClient:
    """Awaitable mirror of `VectorDBBase` that off-loads each call to a thread."""

    def __init__(self, sync_client: VectorDBBase) -> None:
        self._sync = sync_client

    @property
    def sync(self) -> VectorDBBase:
        """Escape hatch for code that must call the sync client directly
        (e.g. already inside a worker thread)."""
        return self._sync

    async def has_collection(self, *args: Any, **kwargs: Any) -> bool:
        return await asyncio.to_thread(self._sync.has_collection, *args, **kwargs)

    async def delete_collection(self, *args: Any, **kwargs: Any) -> None:
        return await asyncio.to_thread(self._sync.delete_collection, *args, **kwargs)

    async def insert(self, *args: Any, **kwargs: Any) -> None:
        return await asyncio.to_thread(self._sync.insert, *args, **kwargs)

    async def upsert(self, *args: Any, **kwargs: Any) -> None:
        return await asyncio.to_thread(self._sync.upsert, *args, **kwargs)

    async def search(self, *args: Any, **kwargs: Any) -> Optional[SearchResult]:
        return await asyncio.to_thread(self._sync.search, *args, **kwargs)

    async def query(self, *args: Any, **kwargs: Any) -> Optional[GetResult]:
        return await asyncio.to_thread(self._sync.query, *args, **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Optional[GetResult]:
        return await asyncio.to_thread(self._sync.get, *args, **kwargs)

    async def delete(self, *args: Any, **kwargs: Any) -> None:
        return await asyncio.to_thread(self._sync.delete, *args, **kwargs)

    async def reset(self, *args: Any, **kwargs: Any) -> None:
        return await asyncio.to_thread(self._sync.reset, *args, **kwargs)


ASYNC_VECTOR_DB_CLIENT = AsyncVectorDBClient(VECTOR_DB_CLIENT)

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

Thread-safety expectations
--------------------------
Every async caller now invokes `VECTOR_DB_CLIENT` from a worker thread
rather than the event-loop thread, and many can run concurrently. The
sync client (and its underlying backend driver) is therefore expected
to be safe for concurrent use across threads, which is the standard
contract for the bundled drivers (chroma, pgvector via SQLAlchemy
pool, qdrant-client, opensearch-py, …). This is *not* a new exposure
introduced by this facade — `save_docs_to_vector_db` already called
the sync client from `run_in_threadpool`, so concurrent threaded
access has always been a requirement of the codebase. Adding a global
serialization lock here would defeat the responsiveness this facade
exists to provide; any backend that genuinely cannot tolerate
concurrent access should grow its own internal serialization.

API surface
-----------
Method signatures mirror `VectorDBBase` exactly. This is deliberate:
permissive `*args/**kwargs` forwarding hides typos at the call site
(an earlier revision of this file shipped that, and a `metadata=`
typo silently broke an entire endpoint until explicit signatures
surfaced it). Callers that need a backend-specific parameter not on
`VectorDBBase` should reach for the `.sync` escape hatch and wrap
their own `asyncio.to_thread`, e.g. ::

    await asyncio.to_thread(
        ASYNC_VECTOR_DB_CLIENT.sync.some_backend_specific_op,
        collection_name, special_kwarg=value,
    )
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Union

from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)


class AsyncVectorDBClient:
    """Awaitable mirror of `VectorDBBase` that off-loads each call to a thread.

    Method signatures mirror `VectorDBBase` exactly so static analysis
    catches bad kwargs at the call site instead of letting them surface
    deep inside the worker thread (where the resulting ``TypeError`` is
    typically swallowed by surrounding ``try/except``).
    """

    def __init__(self, sync_client: VectorDBBase) -> None:
        self._sync = sync_client

    @property
    def sync(self) -> VectorDBBase:
        """Escape hatch for code that must call the sync client directly
        (e.g. already inside a worker thread)."""
        return self._sync

    async def has_collection(self, collection_name: str) -> bool:
        return await asyncio.to_thread(self._sync.has_collection, collection_name)

    async def delete_collection(self, collection_name: str) -> None:
        return await asyncio.to_thread(self._sync.delete_collection, collection_name)

    async def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        return await asyncio.to_thread(self._sync.insert, collection_name, items)

    async def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        return await asyncio.to_thread(self._sync.upsert, collection_name, items)

    async def search(
        self,
        collection_name: str,
        vectors: List[List[Union[float, int]]],
        filter: Optional[Dict] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        return await asyncio.to_thread(self._sync.search, collection_name, vectors, filter, limit)

    async def query(
        self,
        collection_name: str,
        filter: Dict,
        limit: Optional[int] = None,
    ) -> Optional[GetResult]:
        return await asyncio.to_thread(self._sync.query, collection_name, filter, limit)

    async def get(self, collection_name: str) -> Optional[GetResult]:
        return await asyncio.to_thread(self._sync.get, collection_name)

    async def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
    ) -> None:
        return await asyncio.to_thread(self._sync.delete, collection_name, ids, filter)

    async def reset(self) -> None:
        return await asyncio.to_thread(self._sync.reset)


ASYNC_VECTOR_DB_CLIENT = AsyncVectorDBClient(VECTOR_DB_CLIENT)

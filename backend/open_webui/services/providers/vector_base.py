"""Shared adapter logic for wrapping existing vector databases."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, Mapping, Sequence

from open_webui.retrieval.vector.main import VectorDBBase, VectorItem
from open_webui.services.interfaces import (
    VectorDBService,
    VectorQuery,
    VectorQueryResult,
    VectorRecord,
)

log = logging.getLogger(__name__)


def _coerce_vector(values: Sequence[float | int]) -> list[float]:
    return [float(v) for v in values]


def _coerce_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return metadata or {}


class VectorDBAdapter(VectorDBService):
    """Adapter turning existing VectorDBBase implementations into async services."""

    def __init__(self, client: VectorDBBase):
        self._client = client

    async def upsert(self, collection: str, records: Sequence[VectorRecord]) -> None:
        if not records:
            return

        items = [
            VectorItem(
                id=record.id,
                text=record.document or "",
                vector=_coerce_vector(record.values),
                metadata=_coerce_metadata(record.metadata),
            )
            for record in records
        ]

        await asyncio.to_thread(self._client.upsert, collection, items)

    async def delete(self, collection: str, record_ids: Sequence[str]) -> None:
        if not record_ids:
            return
        await asyncio.to_thread(self._client.delete, collection, list(record_ids), None)

    async def delete_collection(self, collection: str) -> None:
        await asyncio.to_thread(self._client.delete_collection, collection)

    async def query(self, collection: str, query: VectorQuery) -> Sequence[VectorQueryResult]:
        def _search() -> Any:
            return self._client.search(collection, [list(query.values)], query.top_k)

        result = await asyncio.to_thread(_search)
        if not result or not getattr(result, "ids", None):
            return []

        ids = result.ids[0] if result.ids else []
        documents = result.documents[0] if result.documents else [None] * len(ids)
        metadatas = result.metadatas[0] if result.metadatas else [None] * len(ids)
        distances = result.distances[0] if getattr(result, "distances", None) else [None] * len(ids)

        responses: list[VectorQueryResult] = []
        for idx, vector_id in enumerate(ids):
            score: float
            distance = distances[idx] if idx < len(distances) else None
            if distance is None:
                score = 0.0
            else:
                try:
                    score = float(distance)
                except (TypeError, ValueError):
                    score = 0.0

            document = documents[idx] if idx < len(documents) else None
            metadata = metadatas[idx] if idx < len(metadatas) else None
            responses.append(
                VectorQueryResult(
                    id=vector_id,
                    score=score,
                    document=document,
                    metadata=metadata,
                )
            )

        return responses

    async def get(self, collection: str, record_id: str) -> VectorRecord | None:
        def _get_all() -> Any:
            return self._client.get(collection)

        result = await asyncio.to_thread(_get_all)
        if not result or not getattr(result, "ids", None):
            return None

        ids = result.ids[0] if result.ids else []
        documents = result.documents[0] if result.documents else []
        metadatas = result.metadatas[0] if result.metadatas else []

        try:
            index = ids.index(record_id)
        except ValueError:
            return None

        document = documents[index] if index < len(documents) else None
        metadata = metadatas[index] if index < len(metadatas) else None

        return VectorRecord(id=record_id, values=[], document=document, metadata=metadata)

    async def find(
        self, collection: str, metadata_filter: Mapping[str, Any]
    ) -> Sequence[VectorRecord]:
        """Naive metadata scan using the underlying client's get()."""
        def _get_all() -> Any:
            return self._client.get(collection)

        result = await asyncio.to_thread(_get_all)
        if not result or not getattr(result, "ids", None):
            return []

        ids = result.ids[0] if result.ids else []
        documents = result.documents[0] if result.documents else []
        metadatas = result.metadatas[0] if result.metadatas else []

        def _match(md: Mapping[str, Any] | None) -> bool:
            if not metadata_filter:
                return True
            if not md:
                return False
            try:
                return all(md.get(k) == v for k, v in metadata_filter.items())
            except Exception:
                return False

        records: list[VectorRecord] = []
        for idx, vector_id in enumerate(ids):
            md = metadatas[idx] if idx < len(metadatas) else None
            if _match(md):
                document = documents[idx] if idx < len(documents) else None
                records.append(
                    VectorRecord(
                        id=vector_id,
                        values=[],
                        document=document,
                        metadata=md,
                    )
                )

        return records

    async def has_collection(self, collection: str) -> bool:
        return await asyncio.to_thread(self._client.has_collection, collection)

    async def reset(self) -> None:
        await asyncio.to_thread(self._client.reset)

    async def health(self) -> Mapping[str, Any]:
        try:
            await asyncio.to_thread(self._client.has_collection, "__healthcheck__")
            return {"status": "ok"}
        except Exception as exc:  # pragma: no cover - defensive fallback
            log.exception("Vector DB health check failed: %s", exc)
            return {"status": "error", "detail": str(exc)}

    async def delete_by_metadata(self, collection: str, metadata_filter: Mapping[str, Any]) -> None:
        matches = await self.find(collection, metadata_filter)
        if not matches:
            return
        await self.delete(collection, [m.id for m in matches])

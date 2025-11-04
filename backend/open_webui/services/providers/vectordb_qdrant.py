"""Qdrant vector database service."""

from __future__ import annotations

from .vector_base import VectorDBAdapter


class QdrantVectorDBService(VectorDBAdapter):
    def __init__(self) -> None:
        from open_webui.retrieval.vector.dbs.qdrant import QdrantClient

        super().__init__(QdrantClient())


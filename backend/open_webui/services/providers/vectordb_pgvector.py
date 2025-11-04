"""PGVector-backed vector database service."""

from __future__ import annotations

from .vector_base import VectorDBAdapter


class PgvectorVectorDBService(VectorDBAdapter):
    def __init__(self) -> None:
        from open_webui.retrieval.vector.dbs.pgvector import PgvectorClient

        super().__init__(PgvectorClient())


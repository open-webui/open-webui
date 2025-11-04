"""Chroma-backed vector database service."""

from __future__ import annotations

from .vector_base import VectorDBAdapter


class ChromaVectorDBService(VectorDBAdapter):
    def __init__(self) -> None:
        from open_webui.retrieval.vector.dbs.chroma import ChromaClient

        super().__init__(ChromaClient())


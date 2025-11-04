"""Pinecone vector database service."""

from __future__ import annotations

from .vector_base import VectorDBAdapter


class PineconeVectorDBService(VectorDBAdapter):
    def __init__(self) -> None:
        from open_webui.retrieval.vector.dbs.pinecone import PineconeClient

        super().__init__(PineconeClient())


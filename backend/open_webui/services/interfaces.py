"""Abstract service interfaces for pluggable runtime providers.

These interfaces intentionally avoid importing any heavyweight ML dependencies
so that enterprise deployments can choose lightweight SaaS-backed
implementations without pulling local inference libraries into memory at module
import time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class EmbeddingService(ABC):
    """Responsible for turning text into embedding vectors."""

    @abstractmethod
    async def embed_text(
        self,
        texts: Sequence[str],
        *,
        prefix: str | None = None,
        user: Any | None = None,
        **_: Any,
    ) -> Sequence[Sequence[float]]:
        """Return an embedding vector for each input text."""


class STTService(ABC):
    """Speech-to-text transcription provider."""

    @abstractmethod
    async def transcribe(
        self, audio: bytes, *, language: str | None = None, **_: Any
    ) -> str:
        """Transcribe raw audio bytes into text."""


class TTSService(ABC):
    """Text-to-speech synthesis provider."""

    @abstractmethod
    async def synthesize(
        self, text: str, *, voice: str | None = None, **_: Any
    ) -> bytes:
        """Produce audio bytes for the supplied text."""


class OCRService(ABC):
    """Optical character recognition provider."""

    @abstractmethod
    async def extract(self, image: bytes) -> str:
        """Extract textual content from the supplied image bytes."""


@dataclass(slots=True)
class VectorRecord:
    """Representation of a vector record stored in the vector database."""

    id: str
    values: Sequence[float]
    document: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class VectorQuery:
    """Vector similarity search query."""

    values: Sequence[float]
    top_k: int = 5
    metadata_filter: Mapping[str, Any] | None = None


@dataclass(slots=True)
class VectorQueryResult:
    """Vector search result item."""

    id: str
    score: float
    document: str | None = None
    metadata: Mapping[str, Any] | None = None


class VectorDBService(ABC):
    """Interface for vector database operations."""

    @abstractmethod
    async def upsert(self, collection: str, records: Sequence[VectorRecord]) -> None:
        """Insert or update the supplied vector records."""

    @abstractmethod
    async def delete(self, collection: str, record_ids: Sequence[str]) -> None:
        """Remove the specified records from the collection."""

    @abstractmethod
    async def delete_collection(self, collection: str) -> None:
        """Drop the collection entirely."""

    @abstractmethod
    async def query(self, collection: str, query: VectorQuery) -> Sequence[VectorQueryResult]:
        """Run a similarity search against the collection."""

    @abstractmethod
    async def get(self, collection: str, record_id: str) -> VectorRecord | None:
        """Retrieve a single record by identifier."""

    @abstractmethod
    async def find(
        self, collection: str, metadata_filter: Mapping[str, Any]
    ) -> Sequence[VectorRecord]:
        """Return records whose metadata matches all key/value pairs in the filter."""

    @abstractmethod
    async def has_collection(self, collection: str) -> bool:
        """Return True when the collection exists."""

    @abstractmethod
    async def reset(self) -> None:
        """Reset internal caches or connections."""

    @abstractmethod
    async def delete_by_metadata(self, collection: str, metadata_filter: Mapping[str, Any]) -> None:
        """Delete all records whose metadata matches the filter."""

    @abstractmethod
    async def health(self) -> Mapping[str, Any]:
        """Return implementation specific diagnostics information."""


class DocumentProcessor(ABC):
    """Pre-processing pipeline for ingested documents."""

    @abstractmethod
    async def process(self, document_id: str, content: str) -> Mapping[str, Any]:
        """Process raw document content and return structured payload."""


class RerankerService(ABC):
    """Optional reranking provider for retrieval results."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: Sequence[str],
        *,
        top_k: int | None = None,
        user: Any | None = None,
    ) -> Sequence[float]:
        """Return a relevance score for each document (aligned with input order)."""


__all__ = [
    "DocumentProcessor",
    "EmbeddingService",
    "OCRService",
    "RerankerService",
    "STTService",
    "TTSService",
    "VectorDBService",
    "VectorQuery",
    "VectorQueryResult",
    "VectorRecord",
]

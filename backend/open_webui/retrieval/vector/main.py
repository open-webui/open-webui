from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class VectorItem(BaseModel):
    id: str
    text: str
    vector: list[float | int]
    metadata: Any


class GetResult(BaseModel):
    ids: list[list[str]] | None
    documents: list[list[str]] | None
    metadatas: list[list[Any]] | None


class SearchResult(GetResult):
    distances: list[list[float | int]] | None


class VectorDBBase(ABC):
    """
    Abstract base class for all vector database backends.

    Implementations of this class provide methods for collection management,
    vector insertion, deletion, similarity search, and metadata filtering.

    Any custom vector database integration must inherit from this class and
    implement all abstract methods.
    """

    @abstractmethod
    def has_collection(self, collection_name: str) -> bool:
        """Check if the collection exists in the vector DB."""
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from the vector DB."""
        pass

    @abstractmethod
    def insert(self, collection_name: str, items: list[VectorItem]) -> None:
        """Insert a list of vector items into a collection."""
        pass

    @abstractmethod
    def upsert(self, collection_name: str, items: list[VectorItem]) -> None:
        """Insert or update vector items in a collection."""
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        vectors: list[list[float | int]],
        filter: dict | None = None,
        limit: int = 10,
    ) -> SearchResult | None:
        """Search for similar vectors in a collection."""
        pass

    @abstractmethod
    def query(
        self, collection_name: str, filter: dict, limit: int | None = None
    ) -> GetResult | None:
        """Query vectors from a collection using metadata filter."""
        pass

    @abstractmethod
    def get(self, collection_name: str) -> GetResult | None:
        """Retrieve all vectors from a collection."""
        pass

    @abstractmethod
    def delete(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        filter: dict | None = None,
    ) -> None:
        """Delete vectors by ID or filter from a collection."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the vector database by removing all collections or those matching a condition."""
        pass

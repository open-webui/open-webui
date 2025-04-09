from typing import Any, Dict, List, Optional

from open_webui.models.users import UserModel
from open_webui.retrieval.vector.main import GetResult, SearchResult, VectorItem


class VectorSearchClient:
    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: Optional[int] = None,
        user: UserModel | None = None,
    ) -> Optional[SearchResult]: ...

    def query(
        self,
        collection_name: str,
        filter: Dict[str, Any],
        limit: Optional[int] = None,
        user: UserModel | None = None,
    ) -> Optional[GetResult]: ...

    def get(
        self,
        collection_name: str,
        limit: Optional[int] = None,
        user: UserModel | None = None,
    ) -> Optional[GetResult]: ...

    def insert(self, collection_name: str, items: List[VectorItem]) -> None: ...

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None: ...

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    def reset(self) -> None: ...

    def has_collection(self, collection_name: str) -> bool: ...

    def delete_collection(self, collection_name: str) -> None: ...

    def close(self) -> None: ...

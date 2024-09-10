from pymilvus import MilvusClient as Milvus

from typing import Optional

from open_webui.apps.rag.vector.main import VectorItem, QueryResult


class MilvusClient:
    def __init__(self):
        self.client = Milvus()

    def list_collections(self) -> list[str]:
        pass

    def create_collection(self, collection_name: str):
        pass

    def delete_collection(self, collection_name: str):
        pass

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[QueryResult]:
        pass

    def get(self, collection_name: str) -> Optional[QueryResult]:
        pass

    def insert(self, collection_name: str, items: list[VectorItem]):
        pass

    def upsert(self, collection_name: str, items: list[VectorItem]):
        pass

    def delete(self, collection_name: str, ids: list[str]):
        pass

    def reset(self):
        pass

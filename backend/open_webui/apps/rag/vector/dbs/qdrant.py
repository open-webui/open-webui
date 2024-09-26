from qdrant_client import QdrantClient as Client
from qdrant_client.http.models import Distance, PointStruct, VectorParams
import json

from typing import Optional

from open_webui.apps.rag.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_URL,
)


class QdrantClient:
    def __init__(self):
        self.collection_prefix = "open_webui"
        self.client = Client(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )

    def _result_to_get_result(self, result) -> GetResult:
        print(result)

        ids = []
        documents = []
        metadatas = []

        for match in result:
            _ids = []
            _documents = []
            _metadatas = []

            for item in match:
                _ids.append(item.get("id"))
                _documents.append(item.get("data", {}).get("text"))
                _metadatas.append(item.get("metadata"))

            ids.append(_ids)
            documents.append(_documents)
            metadatas.append(_metadatas)

        return GetResult(
            **{
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def _result_to_search_result(self, result) -> SearchResult:
        print(result)

        ids = []
        distances = []
        documents = []
        metadatas = []

        for match in result:
            _ids = []
            _distances = []
            _documents = []
            _metadatas = []

            for item in match:
                _ids.append(item.get("id"))
                _distances.append(item.get("distance"))
                _documents.append(item.get("entity", {}).get("data", {}).get("text"))
                _metadatas.append(item.get("entity", {}).get("metadata"))

            ids.append(_ids)
            distances.append(_distances)
            documents.append(_documents)
            metadatas.append(_metadatas)

        return SearchResult(
            **{
                "ids": ids,
                "distances": distances,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        return self.client.collection_exists(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        result = self.client.query_points(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            query=vectors,
            limit=limit,
            with_payload=True
        )

        return self._result_to_search_result(result)

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        result = self.client.query(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            filter='id != ""',
        )
        return self._result_to_get_result([result])

    def insert(self, collection_name: str, items: list[VectorItem]):
        return self.upsert(collection_name=collection_name, items=items)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        if not self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        ):
            self.client.create_collection(
                collection_name=collection_name, vectors_config=VectorParams(size=len(items[0]["vector"][0]),distance=Distance.COSINE)
            )

        return self.client.upsert(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            points=[
                PointStruct(
                    id=item["id"],
                    vector=item["vector"],
                    payload={
                        "text": item["text"],
                        "metadata": item["metadata"]
                    }
                )
                for item in items
            ],
        )

    def delete(self, collection_name: str, ids: list[str]):
        # Delete the items from the collection based on the ids.

        return self.client.delete(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            points_selector=ids,
        )

    def reset(self):
        # Resets the database. This will delete all collections and item entries.

        collection_response = self.client.get_collections()

        for collection in collection_response["collections"]:
            if collection["name"].startswith(self.collection_prefix):
                self.client.drop_collection(collection_name=collection["name"])

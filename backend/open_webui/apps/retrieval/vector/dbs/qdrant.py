from qdrant_client import QdrantClient as Client, models
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)


from typing import Optional

from open_webui.apps.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_URL,
)


class QdrantClient:
    def __init__(self):
        self.client = Client(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )

    def _result_to_get_result(self, result) -> GetResult:
        ids = []
        documents = []
        metadatas = []

        # Iterate over the tuple of records
        for record in result[0]:
            ids.append([record.id])
            documents.append([record.payload["text"]])
            metadatas.append([record.payload["metadata"]])

        return GetResult(
            **{
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def _result_to_search_result(self, result) -> SearchResult:
        ids = []
        distances = []
        documents = []
        metadatas = []

        for point in result.points:
            ids.append([point.id])
            distances.append([point.score])
            documents.append([point.payload["text"]])
            metadatas.append([point.payload["metadata"]])

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
        return self.client.collection_exists(collection_name=collection_name)

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(collection_name=collection_name)

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        result = self.client.query_points(
            collection_name=collection_name,
            query=vectors,
            limit=limit,
            with_payload=True,
        )

        return self._result_to_search_result(result)

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        try:
            if not self.client.collection_exists(collection_name=collection_name):
                return None

            # Build the conditions if a filter is provided.
            qdrant_filter = None
            if filter:
                conditions = [
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in filter.items()
                ]
                qdrant_filter = Filter(must=conditions)

            points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=qdrant_filter,
                limit=limit or 1,
            )

            return self._result_to_get_result(points)

        except Exception as e:
            print(f"Error querying Qdrant: {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        points = self.client.count(
            collection_name=collection_name,
        )
        if points.count:
            # Get all the items in the collection.
            result = self.client.scroll(
                collection_name=collection_name,
                with_payload=True,
                limit=points.count,
            )

            return self._result_to_get_result(result)

        return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        return self.upsert(collection_name=collection_name, items=items)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        if not self.client.collection_exists(collection_name=collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=len(items[0]["vector"]),
                    distance=Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM
                    ),
                ),
            )

        points = [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item in items
        ]

        return self.client.upsert(
            collection_name=collection_name,
            points=points,
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the collection based on the ids.
        if ids:
            selector = ids
        elif filter:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter.items()
            ]
            selector = Filter(must=conditions)

        return self.client.delete(
            collection_name=collection_name,
            points_selector=selector,
        )

    def reset(self):
        # Resets the database. This will delete all collections and item entries.

        collection_response = self.client.get_collections()

        for collection in collection_response.collections:
            self.client.delete_collection(collection_name=collection.name)

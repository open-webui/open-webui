from typing import Optional
import logging
from urllib.parse import urlparse

from qdrant_client import QdrantClient as Qclient
from qdrant_client.http.models import PointStruct
from qdrant_client.models import models

from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import (
    QDRANT_URI,
    QDRANT_API_KEY,
    QDRANT_ON_DISK,
    QDRANT_GRPC_PORT,
    QDRANT_PREFER_GRPC,
)
from open_webui.env import SRC_LOG_LEVELS

NO_LIMIT = 999999999

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class QdrantClient(VectorDBBase):
    def __init__(self):
        self.collection_prefix = "open-webui"
        self.QDRANT_URI = QDRANT_URI
        self.QDRANT_API_KEY = QDRANT_API_KEY
        self.QDRANT_ON_DISK = QDRANT_ON_DISK
        self.PREFER_GRPC = QDRANT_PREFER_GRPC
        self.GRPC_PORT = QDRANT_GRPC_PORT

        if not self.QDRANT_URI:
            self.client = None
            return

        # Unified handling for either scheme
        parsed = urlparse(self.QDRANT_URI)
        host = parsed.hostname or self.QDRANT_URI
        http_port = parsed.port or 6333  # default REST port

        if self.PREFER_GRPC:
            self.client = Qclient(
                host=host,
                port=http_port,
                grpc_port=self.GRPC_PORT,
                prefer_grpc=self.PREFER_GRPC,
                api_key=self.QDRANT_API_KEY,
            )
        else:
            self.client = Qclient(url=self.QDRANT_URI, api_key=self.QDRANT_API_KEY)

    def _result_to_get_result(self, points) -> GetResult:
        ids = []
        documents = []
        metadatas = []

        for point in points:
            payload = point.payload
            ids.append(point.id)
            documents.append(payload["text"])
            metadatas.append(payload["metadata"])

        return GetResult(
            **{
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
            }
        )

    def _create_collection(self, collection_name: str, dimension: int):
        collection_name_with_prefix = f"{self.collection_prefix}_{collection_name}"
        self.client.create_collection(
            collection_name=collection_name_with_prefix,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
                on_disk=self.QDRANT_ON_DISK,
            ),
        )

        log.info(f"collection {collection_name_with_prefix} successfully created!")

    def _create_collection_if_not_exists(self, collection_name, dimension):
        if not self.has_collection(collection_name=collection_name):
            self._create_collection(
                collection_name=collection_name, dimension=dimension
            )

    def _create_points(self, items: list[VectorItem]):
        return [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item in items
        ]

    def has_collection(self, collection_name: str) -> bool:
        return self.client.collection_exists(
            f"{self.collection_prefix}_{collection_name}"
        )

    def delete_collection(self, collection_name: str):
        return self.client.delete_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        if limit is None:
            limit = NO_LIMIT  # otherwise qdrant would set limit to 10!

        query_response = self.client.query_points(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            query=vectors[0],
            limit=limit,
        )
        get_result = self._result_to_get_result(query_response.points)
        return SearchResult(
            ids=get_result.ids,
            documents=get_result.documents,
            metadatas=get_result.metadatas,
            # qdrant distance is [-1, 1], normalize to [0, 1]
            distances=[[(point.score + 1.0) / 2.0 for point in query_response.points]],
        )

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        # Construct the filter string for querying
        if not self.has_collection(collection_name):
            return None
        try:
            if limit is None:
                limit = NO_LIMIT  # otherwise qdrant would set limit to 10!

            field_conditions = []
            for key, value in filter.items():
                field_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}", match=models.MatchValue(value=value)
                    )
                )

            points = self.client.query_points(
                collection_name=f"{self.collection_prefix}_{collection_name}",
                query_filter=models.Filter(should=field_conditions),
                limit=limit,
            )
            return self._result_to_get_result(points.points)
        except Exception as e:
            log.exception(f"Error querying a collection '{collection_name}': {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        points = self.client.query_points(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            limit=NO_LIMIT,  # otherwise qdrant would set limit to 10!
        )
        return self._result_to_get_result(points.points)

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        self._create_collection_if_not_exists(collection_name, len(items[0]["vector"]))
        points = self._create_points(items)
        self.client.upload_points(f"{self.collection_prefix}_{collection_name}", points)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        self._create_collection_if_not_exists(collection_name, len(items[0]["vector"]))
        points = self._create_points(items)
        return self.client.upsert(f"{self.collection_prefix}_{collection_name}", points)

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the collection based on the ids.
        field_conditions = []

        if ids:
            for id_value in ids:
                field_conditions.append(
                    models.FieldCondition(
                        key="metadata.id",
                        match=models.MatchValue(value=id_value),
                    ),
                ),
        elif filter:
            for key, value in filter.items():
                field_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value),
                    ),
                ),

        return self.client.delete(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            points_selector=models.FilterSelector(
                filter=models.Filter(must=field_conditions)
            ),
        )

    def reset(self):
        # Resets the database. This will delete all collections and item entries.
        collection_names = self.client.get_collections().collections
        for collection_name in collection_names:
            if collection_name.name.startswith(self.collection_prefix):
                self.client.delete_collection(collection_name=collection_name.name)

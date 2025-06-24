import logging
from typing import Optional, Tuple
from urllib.parse import urlparse

import grpc
from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_GRPC_PORT,
    QDRANT_ON_DISK,
    QDRANT_PREFER_GRPC,
    QDRANT_URI,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from qdrant_client import QdrantClient as Qclient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import PointStruct
from qdrant_client.models import models

NO_LIMIT = 999999999
TENANT_ID_FIELD = "tenant_id"

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

        # Main collection types for multi-tenancy
        self.MEMORY_COLLECTION = f"{self.collection_prefix}_memories"
        self.KNOWLEDGE_COLLECTION = f"{self.collection_prefix}_knowledge"
        self.FILE_COLLECTION = f"{self.collection_prefix}_files"
        self.WEB_SEARCH_COLLECTION = f"{self.collection_prefix}_web-search"
        self.HASH_BASED_COLLECTION = f"{self.collection_prefix}_hash-based"

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

    def _get_collection_and_tenant_id(self, collection_name: str) -> Tuple[str, str]:
        """
        Maps the traditional collection name to multi-tenant collection and tenant ID.

        Returns:
            tuple: (collection_name, tenant_id)
        """
        # Check for user memory collections
        tenant_id = collection_name

        if collection_name.startswith("user-memory-"):
            return self.MEMORY_COLLECTION, tenant_id

        # Check for file collections
        elif collection_name.startswith("file-"):
            return self.FILE_COLLECTION, tenant_id

        # Check for web search collections
        elif collection_name.startswith("web-search-"):
            return self.WEB_SEARCH_COLLECTION, tenant_id

        # Handle hash-based collections (YouTube and web URLs)
        elif len(collection_name) == 63 and all(
            c in "0123456789abcdef" for c in collection_name
        ):
            return self.HASH_BASED_COLLECTION, tenant_id

        else:
            return self.KNOWLEDGE_COLLECTION, tenant_id

    def _create_multi_tenant_collection(
        self,
        mt_collection_name: str,
        dimension: int = 384,
    ):
        """
        Creates a collection with multi-tenancy configuration and payload indexes for tenant_id and metadata fields.
        """
        self.client.create_collection(
            collection_name=mt_collection_name,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
                on_disk=self.QDRANT_ON_DISK,
            ),
        )
        log.info(
            f"Multi-tenant collection {mt_collection_name} created with dimension {dimension}!"
        )

        self.client.create_payload_index(
            collection_name=mt_collection_name,
            field_name=TENANT_ID_FIELD,
            field_schema=models.KeywordIndexParams(
                type=models.KeywordIndexType.KEYWORD,
                is_tenant=True,
                on_disk=self.QDRANT_ON_DISK,
            ),
        )

    def _create_points(self, items: list[VectorItem], tenant_id: str):
        """
        Create point structs from vector items with tenant ID.
        """
        return [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={
                    "text": item["text"],
                    "metadata": item["metadata"],
                    TENANT_ID_FIELD: tenant_id,
                },
            )
            for item in items
        ]

    def _ensure_collection(
        self,
        mt_collection_name: str,
        dimension: int = 384,
    ):
        """
        Ensure the collection exists and payload indexes are created for tenant_id and metadata fields.
        """
        if self.client.collection_exists(collection_name=mt_collection_name):
            return
        self._create_multi_tenant_collection(mt_collection_name, dimension)

    def has_collection(self, collection_name: str) -> bool:
        """
        Check if a logical collection exists by checking for any points with the tenant ID.
        """
        if not self.client:
            return False
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            return False
        tenant_filter = models.FieldCondition(
            key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id)
        )
        count_result = self.client.count(
            collection_name=mt_collection,
            count_filter=models.Filter(must=[tenant_filter]),
        )
        return count_result.count > 0

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        """
        Delete vectors by ID or filter from a collection with tenant isolation.
        """
        if not self.client:
            return None

        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, nothing to delete")
            return None

        tenant_filter = models.FieldCondition(
            key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id)
        )
        must_conditions = [tenant_filter]
        should_conditions = []
        if ids:
            for id_value in ids:
                should_conditions.append(
                    models.FieldCondition(
                        key="metadata.id",
                        match=models.MatchValue(value=id_value),
                    ),
                )
        elif filter:
            for key, value in filter.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value),
                    ),
                )

        try:
            update_result = self.client.delete(
                collection_name=mt_collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=must_conditions, should=should_conditions)
                ),
            )

            return update_result
        except Exception as e:
            log.warning(f"Error deleting from collection {mt_collection}: {e}")
            return None

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """
        Search for the nearest neighbor items based on the vectors with tenant isolation.
        """
        if not self.client:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, search returns None")
            return None

        dimension = len(vectors[0]) if vectors and len(vectors) > 0 else None
        try:
            tenant_filter = models.FieldCondition(
                key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id)
            )
            collection_dim = self.client.get_collection(
                mt_collection
            ).config.params.vectors.size
            if collection_dim != dimension:
                if collection_dim < dimension:
                    vectors = [vector[:collection_dim] for vector in vectors]
                else:
                    vectors = [
                        vector + [0] * (collection_dim - dimension)
                        for vector in vectors
                    ]
            prefetch_query = models.Prefetch(
                filter=models.Filter(must=[tenant_filter]),
                limit=NO_LIMIT,
            )
            query_response = self.client.query_points(
                collection_name=mt_collection,
                query=vectors[0],
                prefetch=prefetch_query,
                limit=limit,
            )
            get_result = self._result_to_get_result(query_response.points)
            return SearchResult(
                ids=get_result.ids,
                documents=get_result.documents,
                metadatas=get_result.metadatas,
                distances=[
                    [(point.score + 1.0) / 2.0 for point in query_response.points]
                ],
            )
        except Exception as e:
            log.exception(f"Error searching collection '{collection_name}': {e}")
            return None

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        """
        Query points with filters and tenant isolation.
        """
        if not self.client:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, query returns None")
            return None

        if limit is None:
            limit = NO_LIMIT
        tenant_filter = models.FieldCondition(
            key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id)
        )
        field_conditions = []
        for key, value in filter.items():
            field_conditions.append(
                models.FieldCondition(
                    key=f"metadata.{key}", match=models.MatchValue(value=value)
                )
            )
        combined_filter = models.Filter(must=[tenant_filter, *field_conditions])
        try:
            points = self.client.query_points(
                collection_name=mt_collection,
                query_filter=combined_filter,
                limit=limit,
            )
            return self._result_to_get_result(points.points)
        except Exception as e:
            log.exception(f"Error querying collection '{collection_name}': {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """
        Get all items in a collection with tenant isolation.
        """
        if not self.client:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, get returns None")
            return None

        tenant_filter = models.FieldCondition(
            key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id)
        )
        try:
            points = self.client.query_points(
                collection_name=mt_collection,
                query_filter=models.Filter(must=[tenant_filter]),
                limit=NO_LIMIT,
            )

            return self._result_to_get_result(points.points)
        except Exception as e:
            log.exception(f"Error getting collection '{collection_name}': {e}")
            return None

    def upsert(self, collection_name: str, items: list[VectorItem]):
        """
        Upsert items with tenant ID.
        """
        if not self.client or not items:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        dimension = len(items[0]["vector"]) if items else None
        self._ensure_collection(mt_collection, dimension)
        points = self._create_points(items, tenant_id)
        self.client.upload_points(mt_collection, points)
        return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        """
        Insert items with tenant ID.
        """
        return self.upsert(collection_name, items)

    def reset(self):
        """
        Reset the database by deleting all collections.
        """
        if not self.client:
            return None

        collection_names = self.client.get_collections().collections
        for collection_name in collection_names:
            if collection_name.name.startswith(self.collection_prefix):
                self.client.delete_collection(collection_name=collection_name.name)

    def delete_collection(self, collection_name: str):
        """
        Delete a collection.
        """
        if not self.client:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, nothing to delete")
            return None

        self.client.delete(
            collection_name=mt_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key=TENANT_ID_FIELD,
                            match=models.MatchValue(value=tenant_id),
                        )
                    ]
                )
            ),
        )

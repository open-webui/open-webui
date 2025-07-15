import logging
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse

import grpc
from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_GRPC_PORT,
    QDRANT_ON_DISK,
    QDRANT_PREFER_GRPC,
    QDRANT_URI,
    QDRANT_COLLECTION_PREFIX,
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
DEFAULT_DIMENSION = 384

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def _tenant_filter(tenant_id: str) -> models.FieldCondition:
    return models.FieldCondition(
        key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id)
    )


def _metadata_filter(key: str, value: Any) -> models.FieldCondition:
    return models.FieldCondition(
        key=f"metadata.{key}", match=models.MatchValue(value=value)
    )


class QdrantClient(VectorDBBase):
    def __init__(self):
        self.collection_prefix = QDRANT_COLLECTION_PREFIX
        self.QDRANT_URI = QDRANT_URI
        self.QDRANT_API_KEY = QDRANT_API_KEY
        self.QDRANT_ON_DISK = QDRANT_ON_DISK
        self.PREFER_GRPC = QDRANT_PREFER_GRPC
        self.GRPC_PORT = QDRANT_GRPC_PORT

        if not self.QDRANT_URI:
            raise ValueError(
                "QDRANT_URI is not set. Please configure it in the environment variables."
            )

        # Unified handling for either scheme
        parsed = urlparse(self.QDRANT_URI)
        host = parsed.hostname or self.QDRANT_URI
        http_port = parsed.port or 6333  # default REST port

        self.client = (
            Qclient(
                host=host,
                port=http_port,
                grpc_port=self.GRPC_PORT,
                prefer_grpc=self.PREFER_GRPC,
                api_key=self.QDRANT_API_KEY,
            )
            if self.PREFER_GRPC
            else Qclient(url=self.QDRANT_URI, api_key=self.QDRANT_API_KEY)
        )

        # Main collection types for multi-tenancy
        self.MEMORY_COLLECTION = f"{self.collection_prefix}_memories"
        self.KNOWLEDGE_COLLECTION = f"{self.collection_prefix}_knowledge"
        self.FILE_COLLECTION = f"{self.collection_prefix}_files"
        self.WEB_SEARCH_COLLECTION = f"{self.collection_prefix}_web-search"
        self.HASH_BASED_COLLECTION = f"{self.collection_prefix}_hash-based"

    def _result_to_get_result(self, points) -> GetResult:
        ids, documents, metadatas = [], [], []
        for point in points:
            payload = point.payload
            ids.append(point.id)
            documents.append(payload["text"])
            metadatas.append(payload["metadata"])
        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

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
        self, mt_collection_name: str, dimension: int = DEFAULT_DIMENSION
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

        for field in ("metadata.hash", "metadata.file_id"):
            self.client.create_payload_index(
                collection_name=mt_collection_name,
                field_name=field,
                field_schema=models.KeywordIndexParams(
                    type=models.KeywordIndexType.KEYWORD,
                    on_disk=self.QDRANT_ON_DISK,
                ),
            )

    def _create_points(
        self, items: List[VectorItem], tenant_id: str
    ) -> List[PointStruct]:
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
        self, mt_collection_name: str, dimension: int = DEFAULT_DIMENSION
    ):
        """
        Ensure the collection exists and payload indexes are created for tenant_id and metadata fields.
        """
        if not self.client.collection_exists(collection_name=mt_collection_name):
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
        tenant_filter = _tenant_filter(tenant_id)
        count_result = self.client.count(
            collection_name=mt_collection,
            count_filter=models.Filter(must=[tenant_filter]),
        )
        return count_result.count > 0

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
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

        must_conditions = [_tenant_filter(tenant_id)]
        should_conditions = []
        if ids:
            should_conditions = [_metadata_filter("id", id_value) for id_value in ids]
        elif filter:
            must_conditions += [_metadata_filter(k, v) for k, v in filter.items()]

        return self.client.delete(
            collection_name=mt_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=must_conditions, should=should_conditions)
            ),
        )

    def search(
        self, collection_name: str, vectors: List[List[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """
        Search for the nearest neighbor items based on the vectors with tenant isolation.
        """
        if not self.client or not vectors:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, search returns None")
            return None

        tenant_filter = _tenant_filter(tenant_id)
        query_response = self.client.query_points(
            collection_name=mt_collection,
            query=vectors[0],
            limit=limit,
            query_filter=models.Filter(must=[tenant_filter]),
        )
        get_result = self._result_to_get_result(query_response.points)
        return SearchResult(
            ids=get_result.ids,
            documents=get_result.documents,
            metadatas=get_result.metadatas,
            distances=[[(point.score + 1.0) / 2.0 for point in query_response.points]],
        )

    def query(
        self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None
    ):
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
        tenant_filter = _tenant_filter(tenant_id)
        field_conditions = [_metadata_filter(k, v) for k, v in filter.items()]
        combined_filter = models.Filter(must=[tenant_filter, *field_conditions])
        points = self.client.query_points(
            collection_name=mt_collection,
            query_filter=combined_filter,
            limit=limit,
        )
        return self._result_to_get_result(points.points)

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
        tenant_filter = _tenant_filter(tenant_id)
        points = self.client.query_points(
            collection_name=mt_collection,
            query_filter=models.Filter(must=[tenant_filter]),
            limit=NO_LIMIT,
        )
        return self._result_to_get_result(points.points)

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """
        Upsert items with tenant ID.
        """
        if not self.client or not items:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        dimension = len(items[0]["vector"])
        self._ensure_collection(mt_collection, dimension)
        points = self._create_points(items, tenant_id)
        self.client.upload_points(mt_collection, points)
        return None

    def insert(self, collection_name: str, items: List[VectorItem]):
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
        for collection in self.client.get_collections().collections:
            if collection.name.startswith(self.collection_prefix):
                self.client.delete_collection(collection_name=collection.name)

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
                filter=models.Filter(must=[_tenant_filter(tenant_id)])
            ),
        )

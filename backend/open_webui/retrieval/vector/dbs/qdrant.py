from typing import Optional, Tuple
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

    def _create_multi_tenant_collection_if_not_exists(
        self, mt_collection_name: str, dimension: int = 384
    ):
        """
        Creates a collection with multi-tenancy configuration if it doesn't exist.
        Default dimension is set to 384 which corresponds to 'sentence-transformers/all-MiniLM-L6-v2'.
        When creating collections dynamically (insert/upsert), the actual vector dimensions will be used.
        """

        if not self.client.collection_exists(mt_collection_name):
            # Create collection with multi-tenancy config
            self.client.create_collection(
                collection_name=mt_collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                    on_disk=self.QDRANT_ON_DISK,
                ),
                hnsw_config=models.HnswConfigDiff(
                    payload_m=16,  # Enable per-tenant indexing
                    m=0,
                    on_disk=self.QDRANT_ON_DISK,
                ),
            )

            # Create tenant ID payload index
            self.client.create_payload_index(
                collection_name=mt_collection_name,
                field_name="tenant_id",
                field_schema=models.KeywordIndexParams(
                    type=models.KeywordIndexType.KEYWORD,
                    is_tenant=True,
                    on_disk=self.QDRANT_ON_DISK,
                ),
                wait=True,
            )

            log.info(
                f"Multi-tenant collection {mt_collection_name} created with dimension {dimension}!"
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
                    "tenant_id": tenant_id,
                },
            )
            for item in items
        ]

    def has_collection(self, collection_name: str) -> bool:
        """
        Check if a logical collection exists by checking for any points with the tenant ID.
        """
        if not self.client:
            return False

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        if not self.client.collection_exists(mt_collection):
            return False

        # Create tenant filter
        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
        )

        try:
            # Check if any points exist with this tenant ID
            response = self.client.query_points(
                collection_name=mt_collection,
                query_filter=models.Filter(must=[tenant_filter]),
                limit=1,
            )

            return len(response.points) > 0
        except Exception:
            return False

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

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        if not self.client.collection_exists(mt_collection):
            return None

        # Create tenant filter
        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
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

        update_result = self.client.delete(
            collection_name=mt_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=must_conditions, should=should_conditions)
            ),
        )

        if self.client.get_collection(mt_collection).points_count == 0:
            self.client.delete_collection(mt_collection)

        return update_result

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """
        Search for the nearest neighbor items based on the vectors with tenant isolation.
        """
        if not self.client:
            return None

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        # Get the vector dimension from the query vector
        dimension = len(vectors[0]) if vectors and len(vectors) > 0 else None

        collection_dim = self.client.get_collection(
            mt_collection
        ).config.params.vectors.size
        if collection_dim != dimension:
            if collection_dim < dimension:
                vectors = [vector[:collection_dim] for vector in vectors]
            else:
                vectors = [
                    vector + [0] * (collection_dim - dimension) for vector in vectors
                ]
        # Create tenant filter
        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
        )

        # Search with tenant filter

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
            # qdrant distance is [-1, 1], normalize to [0, 1]
            distances=[[(point.score + 1.0) / 2.0 for point in query_response.points]],
        )

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        """
        Query points with filters and tenant isolation.
        """
        if not self.client:
            return None

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        # When using OpenAI embedding models, ensure we get the correct dimension

        if not self.client.collection_exists(mt_collection):
            return None

        try:
            if limit is None:
                limit = NO_LIMIT

            # Create tenant filter
            tenant_filter = models.FieldCondition(
                key="tenant_id", match=models.MatchValue(value=tenant_id)
            )

            # Create metadata filters
            field_conditions = []
            for key, value in filter.items():
                field_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}", match=models.MatchValue(value=value)
                    )
                )

            # Combine tenant filter with metadata filters
            combined_filter = models.Filter(must=[tenant_filter, *field_conditions])

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

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        if not self.client.collection_exists(mt_collection):
            return None

        # Create tenant filter
        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
        )

        # Get all points with tenant filter
        points = self.client.query_points(
            collection_name=mt_collection,
            query_filter=models.Filter(must=[tenant_filter]),
            limit=NO_LIMIT,
        )

        return self._result_to_get_result(points.points)

    def insert(self, collection_name: str, items: list[VectorItem]):
        """
        Insert items with tenant ID.
        """
        if not self.client or not items:
            return None

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        # Get dimensions from the actual vectors
        dimension = len(items[0]["vector"]) if items else None

        # Create the collection if it doesn't exist
        if not self.client.collection_exists(mt_collection):
            self._create_multi_tenant_collection_if_not_exists(
                mt_collection_name=mt_collection, dimension=dimension
            )
        else:
            mt_collection_info = self.client.get_collection(mt_collection)
            if mt_collection_info.config.params.vectors.size < dimension:
                items = [
                    {
                        "id": item["id"],
                        "text": item["text"],
                        "vector": item["vector"][
                            : mt_collection_info.config.params.vectors.size
                        ],
                        "metadata": item["metadata"],
                    }
                    for item in items
                ]
            if mt_collection_info.config.params.vectors.size > dimension:
                target_dimension = mt_collection_info.config.params.vectors.size
                items = [
                    {
                        "id": item["id"],
                        "text": item["text"],
                        "vector": item["vector"]
                        + [0] * (target_dimension - len(item["vector"])),
                        "metadata": item["metadata"],
                    }
                    for item in items
                ]

        # Create points with tenant ID
        points = self._create_points(items, tenant_id)

        self.client.upload_points(mt_collection, points)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        """
        Upsert items with tenant ID.
        """
        if not self.client or not items:
            return None

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        # Get dimensions from the actual vectors
        dimension = len(items[0]["vector"]) if items else None

        # Create the collection if it doesn't exist
        if not self.client.collection_exists(mt_collection):
            self._create_multi_tenant_collection_if_not_exists(
                mt_collection_name=mt_collection, dimension=dimension
            )
        else:
            mt_collection_info = self.client.get_collection(mt_collection)
            if mt_collection_info.config.params.vectors.size < dimension:
                items = [
                    {
                        "id": item.id,
                        "text": item.text,
                        "vector": item.vector[
                            : mt_collection_info.config.params.vectors.size
                        ],
                        "metadata": item.metadata,
                    }
                    for item in items
                ]
            if mt_collection_info.config.params.vectors.size > dimension:
                target_dimension = mt_collection_info.config.params.vectors.size
                items = [
                    {
                        "id": item.id,
                        "text": item.text,
                        "vector": item.vector
                        + [0] * (target_dimension - len(item.vector)),
                        "metadata": item.metadata,
                    }
                    for item in items
                ]
        # Create points with tenant ID
        points = self._create_points(items, tenant_id)

        return self.client.upsert(mt_collection, points)

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

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
        )

        field_conditions = [tenant_filter]

        update_result = self.client.delete(
            collection_name=mt_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=field_conditions)
            ),
        )

        if self.client.get_collection(mt_collection).points_count == 0:
            self.client.delete_collection(mt_collection)

        return update_result

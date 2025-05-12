import logging
from typing import Optional, Tuple
from urllib.parse import urlparse

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
        try:
            # Try to create the collection directly - will fail if it already exists
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
        except UnexpectedResponse as e:
            # Check for the specific 409 Conflict status code for "already exists" errors
            if e.status_code == 409:
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                if "already exists" in error_msg:
                    log.debug(f"Collection {mt_collection_name} already exists")
                    return
            # If it's not an already exists error, re-raise
            raise e
        except Exception as e:
            raise e

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

        # Create tenant filter
        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
        )

        try:
            # Try directly querying - most of the time collection should exist
            response = self.client.query_points(
                collection_name=mt_collection,
                query_filter=models.Filter(must=[tenant_filter]),
                limit=1,
            )

            # Collection exists with this tenant ID if there are points
            return len(response.points) > 0
        except UnexpectedResponse as e:
            try:
                # Get structured error data - same approach as _handle_operation_with_error_retry
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                # Check for collection not found error - same pattern as in _handle_operation_with_error_retry
                if (
                    e.status_code == 404
                    and "Collection" in error_msg
                    and "doesn't exist" in error_msg
                ):
                    log.debug(f"Collection {mt_collection} doesn't exist")
                    return False
                else:
                    # For other API errors, log and return False
                    log.warning(
                        f"Unexpected Qdrant error: {error_msg} (status code: {e.status_code})"
                    )
                    return False
            except Exception as inner_e:
                # If structured parsing fails, log and return False
                log.error(f"Failed to handle Qdrant error: {inner_e}")
                return False
        except Exception as e:
            # For any other errors, log and return False
            log.debug(f"Error checking collection {mt_collection}: {e}")
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

        try:
            # Try to delete directly - most of the time collection should exist
            update_result = self.client.delete(
                collection_name=mt_collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=must_conditions, should=should_conditions)
                ),
            )

            return update_result
        except UnexpectedResponse as e:
            try:
                # Get structured error data
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                # Check for collection not found error
                if (
                    e.status_code == 404
                    and "Collection" in error_msg
                    and "doesn't exist" in error_msg
                ):
                    log.debug(
                        f"Collection {mt_collection} doesn't exist, nothing to delete"
                    )
                    return None
                else:
                    # For other API errors, log and re-raise
                    log.warning(
                        f"Unexpected Qdrant error: {error_msg} (status code: {e.status_code})"
                    )
                    raise
            except Exception as inner_e:
                # If structured parsing fails, log and raise original error
                log.error(f"Failed to handle Qdrant error: {inner_e}")
                raise e
        except Exception as e:
            # For non-Qdrant exceptions, re-raise
            raise

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

        try:
            # Try the search operation directly - most of the time collection should exist

            # Create tenant filter
            tenant_filter = models.FieldCondition(
                key="tenant_id", match=models.MatchValue(value=tenant_id)
            )

            # Ensure vector dimensions match the collection
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
                distances=[
                    [(point.score + 1.0) / 2.0 for point in query_response.points]
                ],
            )
        except UnexpectedResponse as e:
            try:
                # Get structured error data
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                # Check for collection not found error
                if (
                    e.status_code == 404
                    and "Collection" in error_msg
                    and "doesn't exist" in error_msg
                ):
                    log.debug(
                        f"Collection {mt_collection} doesn't exist, search returns None"
                    )
                    return None
                else:
                    # For other API errors, log and re-raise
                    log.warning(
                        f"Unexpected Qdrant error during search: {error_msg} (status code: {e.status_code})"
                    )
                    raise
            except Exception as inner_e:
                # If structured parsing fails, log and raise original error
                log.error(f"Failed to handle Qdrant error during search: {inner_e}")
                raise e
        except Exception as e:
            # For non-Qdrant exceptions, log and return None
            log.exception(f"Error searching collection '{collection_name}': {e}")
            return None

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        """
        Query points with filters and tenant isolation.
        """
        if not self.client:
            return None

        # Map to multi-tenant collection and tenant ID
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)

        # Set default limit if not provided
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

        try:
            # Try the query directly - most of the time collection should exist
            points = self.client.query_points(
                collection_name=mt_collection,
                query_filter=combined_filter,
                limit=limit,
            )

            return self._result_to_get_result(points.points)
        except UnexpectedResponse as e:
            try:
                # Get structured error data
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                # Check for collection not found error
                if (
                    e.status_code == 404
                    and "Collection" in error_msg
                    and "doesn't exist" in error_msg
                ):
                    log.debug(
                        f"Collection {mt_collection} doesn't exist, query returns None"
                    )
                    return None
                else:
                    # For other API errors, log and re-raise
                    log.warning(
                        f"Unexpected Qdrant error during query: {error_msg} (status code: {e.status_code})"
                    )
                    raise
            except Exception as inner_e:
                # If structured parsing fails, log and raise original error
                log.error(f"Failed to handle Qdrant error during query: {inner_e}")
                raise e
        except Exception as e:
            # For non-Qdrant exceptions, log and re-raise
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

        # Create tenant filter
        tenant_filter = models.FieldCondition(
            key="tenant_id", match=models.MatchValue(value=tenant_id)
        )

        try:
            # Try to get points directly - most of the time collection should exist
            points = self.client.query_points(
                collection_name=mt_collection,
                query_filter=models.Filter(must=[tenant_filter]),
                limit=NO_LIMIT,
            )

            return self._result_to_get_result(points.points)
        except UnexpectedResponse as e:
            try:
                # Get structured error data
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                # Check for collection not found error
                if (
                    e.status_code == 404
                    and "Collection" in error_msg
                    and "doesn't exist" in error_msg
                ):
                    log.debug(
                        f"Collection {mt_collection} doesn't exist, get returns None"
                    )
                    return None
                else:
                    # For other API errors, log and re-raise
                    log.warning(
                        f"Unexpected Qdrant error during get: {error_msg} (status code: {e.status_code})"
                    )
                    raise
            except Exception as inner_e:
                # If structured parsing fails, log and raise original error
                log.error(f"Failed to handle Qdrant error during get: {inner_e}")
                raise e
        except Exception as e:
            # For non-Qdrant exceptions, log and return None
            log.exception(f"Error getting collection '{collection_name}': {e}")
            return None

    def _handle_operation_with_error_retry(
        self, operation_name, mt_collection, points, dimension
    ):
        """
        Private helper to handle common error cases for insert and upsert operations.

        Args:
            operation_name: 'insert' or 'upsert'
            mt_collection: The multi-tenant collection name
            points: The vector points to insert/upsert
            dimension: The dimension of the vectors

        Returns:
            The operation result (for upsert) or None (for insert)
        """
        try:
            if operation_name == "insert":
                self.client.upload_points(mt_collection, points)
                return None
            else:  # upsert
                return self.client.upsert(mt_collection, points)
        except UnexpectedResponse as e:
            try:
                # Get structured error data
                error_data = e.structured()
                error_msg = error_data.get("status", {}).get("error", "")

                # Handle collection not found (status code 404)
                if (
                    e.status_code == 404
                    and "Collection" in error_msg
                    and "doesn't exist" in error_msg
                ):
                    log.info(
                        f"Collection {mt_collection} doesn't exist. Creating it with dimension {dimension}."
                    )
                    # Create collection with correct dimensions from our vectors
                    self._create_multi_tenant_collection_if_not_exists(
                        mt_collection_name=mt_collection, dimension=dimension
                    )
                    # Try operation again - no need for dimension adjustment since we just created with correct dimensions
                    if operation_name == "insert":
                        self.client.upload_points(mt_collection, points)
                        return None
                    else:  # upsert
                        return self.client.upsert(mt_collection, points)

                # Handle dimension mismatch (status code 400)
                elif e.status_code == 400 and "Vector dimension error" in error_msg:
                    # For dimension errors, the collection must exist, so get its configuration
                    mt_collection_info = self.client.get_collection(mt_collection)
                    existing_size = mt_collection_info.config.params.vectors.size

                    log.info(
                        f"Dimension mismatch: Collection {mt_collection} expects {existing_size}, got {dimension}"
                    )

                    if existing_size < dimension:
                        # Truncate vectors to fit
                        log.info(
                            f"Truncating vectors from {dimension} to {existing_size} dimensions"
                        )
                        points = [
                            PointStruct(
                                id=point.id,
                                vector=point.vector[:existing_size],
                                payload=point.payload,
                            )
                            for point in points
                        ]
                    elif existing_size > dimension:
                        # Pad vectors with zeros
                        log.info(
                            f"Padding vectors from {dimension} to {existing_size} dimensions with zeros"
                        )
                        points = [
                            PointStruct(
                                id=point.id,
                                vector=point.vector
                                + [0] * (existing_size - len(point.vector)),
                                payload=point.payload,
                            )
                            for point in points
                        ]
                    # Try operation again with adjusted dimensions
                    if operation_name == "insert":
                        self.client.upload_points(mt_collection, points)
                        return None
                    else:  # upsert
                        return self.client.upsert(mt_collection, points)
                else:
                    # Not a known error we can handle, re-raise
                    log.warning(
                        f"Unhandled Qdrant error: {error_msg} (status code: {e.status_code})"
                    )
                    raise
            except Exception as inner_e:
                # If structured parsing or handling fails, log and raise original error
                log.error(f"Failed to handle Qdrant error: {inner_e}")
                raise e
        except Exception as e:
            # For non-Qdrant exceptions, re-raise
            raise

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

        # Create points with tenant ID
        points = self._create_points(items, tenant_id)

        # Handle the operation with error retry
        return self._handle_operation_with_error_retry(
            "insert", mt_collection, points, dimension
        )

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

        # Create points with tenant ID
        points = self._create_points(items, tenant_id)

        # Handle the operation with error retry
        return self._handle_operation_with_error_retry(
            "upsert", mt_collection, points, dimension
        )

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

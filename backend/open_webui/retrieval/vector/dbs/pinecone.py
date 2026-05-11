"""
NOTE: This vector database integration is community-supported and maintained on a best-effort basis.
"""

from typing import Optional, List, Dict, Any, Union
import logging
import time  # for measuring elapsed time
from pinecone import Pinecone, ServerlessSpec

# Add gRPC support for better performance (Pinecone best practice)
try:
    from pinecone.grpc import PineconeGRPC

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False

import asyncio  # for async upserts
import functools  # for partial binding in async tasks

import concurrent.futures  # for parallel batch upserts
import random  # for jitter in retry backoff

from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import (
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
    PINECONE_DIMENSION,
    PINECONE_METRIC,
    PINECONE_CLOUD,
)
from open_webui.retrieval.vector.utils import process_metadata

NO_LIMIT = 10000  # Reasonable limit to avoid overwhelming the system
# Pinecone supports up to 1000 vectors/batch (official recommendation)
BATCH_SIZE = 1000
MAX_BATCH_SIZE_BYTES = 1_048_576  # 1 MB payload limit per Pinecone request

log = logging.getLogger(__name__)


class PineconeClient(VectorDBBase):
    def __init__(self):
        self.collection_prefix = "open-webui"

        # Validate required configuration
        self._validate_config()

        # Store configuration values - extract .value if PersistentConfig
        self.api_key = self._extract_value(PINECONE_API_KEY)
        self.environment = self._extract_value(PINECONE_ENVIRONMENT)
        self.index_name = self._extract_value(PINECONE_INDEX_NAME)
        self.dimension = int(self._extract_value(PINECONE_DIMENSION))
        self.metric = self._extract_value(PINECONE_METRIC)
        self.cloud = self._extract_value(PINECONE_CLOUD)

        # Initialize Pinecone client for improved performance
        if GRPC_AVAILABLE:
            # Use gRPC client for better performance (Pinecone recommendation)
            self.client = PineconeGRPC(
                api_key=self.api_key,
                pool_threads=20,  # Improved connection pool size
                timeout=30,  # Reasonable timeout for operations
            )
            self.using_grpc = True
            log.info("Using Pinecone gRPC client for optimal performance")
        else:
            # Fallback to HTTP client with enhanced connection pooling
            self.client = Pinecone(
                api_key=self.api_key,
                pool_threads=20,  # Improved connection pool size
                timeout=30,  # Reasonable timeout for operations
            )
            self.using_grpc = False
            log.info("Using Pinecone HTTP client (gRPC not available)")

        # Persistent executor for batch operations
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

        # Create index if it doesn't exist
        self._initialize_index()

    def _extract_value(self, config_value):
        """Extract the actual value from PersistentConfig or return the value as-is."""
        if hasattr(config_value, "value"):
            return config_value.value
        return config_value

    def _validate_config(self) -> None:
        """Validate that all required configuration variables are set."""
        missing_vars = []
        if not self._extract_value(PINECONE_API_KEY):
            missing_vars.append("PINECONE_API_KEY")
        if not self._extract_value(PINECONE_ENVIRONMENT):
            missing_vars.append("PINECONE_ENVIRONMENT")
        if not self._extract_value(PINECONE_INDEX_NAME):
            missing_vars.append("PINECONE_INDEX_NAME")
        if not self._extract_value(PINECONE_DIMENSION):
            missing_vars.append("PINECONE_DIMENSION")
        if not self._extract_value(PINECONE_CLOUD):
            missing_vars.append("PINECONE_CLOUD")

        if missing_vars:
            raise ValueError(f"Required configuration missing: {', '.join(missing_vars)}")

    def _initialize_index(self) -> None:
        """Initialize the Pinecone index."""
        try:
            # Check if index exists
            if self.index_name not in self.client.list_indexes().names():
                log.info(f"Creating Pinecone index '{self.index_name}'...")
                self.client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(cloud=self.cloud, region=self.environment),
                )
                log.info(f"Successfully created Pinecone index '{self.index_name}'")
            else:
                log.info(f"Using existing Pinecone index '{self.index_name}'")

            # Connect to the index
            self.index = self.client.Index(
                self.index_name,
                pool_threads=20,  # Enhanced connection pool for index operations
            )

        except Exception as e:
            log.error(f"Failed to initialize Pinecone index: {e}")
            raise RuntimeError(f"Failed to initialize Pinecone index: {e}")

    def _retry_pinecone_operation(self, operation_func, max_retries=3):
        """Retry Pinecone operations with exponential backoff for rate limits and network issues."""
        for attempt in range(max_retries):
            try:
                return operation_func()
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a retryable error (rate limits, network issues, timeouts)
                is_retryable = any(
                    keyword in error_str
                    for keyword in [
                        "rate limit",
                        "quota",
                        "timeout",
                        "network",
                        "connection",
                        "unavailable",
                        "internal error",
                        "429",
                        "500",
                        "502",
                        "503",
                        "504",
                    ]
                )

                if not is_retryable or attempt == max_retries - 1:
                    # Don't retry for non-retryable errors or on final attempt
                    raise

                # Exponential backoff with jitter
                delay = (2**attempt) + random.uniform(0, 1)
                log.warning(
                    f"Pinecone operation failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)

    def _create_points(self, items: List[VectorItem], collection_name_with_prefix: str) -> List[Dict[str, Any]]:
        """Convert VectorItem objects to Pinecone point format."""
        points = []
        for item in items:
            # Start with any existing metadata or an empty dict
            metadata = item.get("metadata", {}).copy() if item.get("metadata") else {}

            # Add text to metadata if available
            if "text" in item:
                metadata["text"] = item["text"]

            # CRITICAL: Always add collection_name to metadata for filtering
            # This MUST be set correctly for proper isolation
            metadata["collection_name"] = collection_name_with_prefix

            # Extract file_id from collection name if it's a file collection
            if collection_name_with_prefix.startswith(f"{self.collection_prefix}_file-"):
                # Extract the file ID from the collection name
                file_id_from_collection = collection_name_with_prefix.replace(f"{self.collection_prefix}_file-", "")

                # Verify consistency: if metadata has file_id, it must match
                if "file_id" in metadata and metadata["file_id"] != file_id_from_collection:
                    log.error(
                        f"FILE ID MISMATCH! Metadata file_id: {metadata.get('file_id')}, Collection file_id: {file_id_from_collection}"
                    )
                    log.error(
                        f"This will cause cross-contamination! Full collection name: {collection_name_with_prefix}"
                    )
                    # Force correct file_id to prevent contamination
                    metadata["file_id"] = file_id_from_collection

            point = {
                "id": item["id"],
                "values": item["vector"],
                "metadata": process_metadata(metadata),
            }
            points.append(point)
        return points

    def _batch_points_by_size(self, points: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Split points into batches respecting both count and size limits.

        Pinecone limits:
        - Max 1000 vectors per batch
        - Max 1 MB payload per request

        This ensures we never exceed either limit, especially important for
        high-dimensional embeddings (e.g., 3072 dims) or large metadata.
        """
        batches = []
        current_batch = []
        current_size = 0

        for point in points:
            # Estimate point size: vector (4 bytes per float) + metadata JSON
            vector_size = len(point["values"]) * 4  # 4 bytes per float32
            metadata_size = len(str(point["metadata"]).encode("utf-8"))
            point_size = vector_size + metadata_size + 100  # +100 for overhead

            # Check if adding this point would exceed limits
            would_exceed_count = len(current_batch) >= BATCH_SIZE
            would_exceed_size = current_size + point_size > MAX_BATCH_SIZE_BYTES

            if current_batch and (would_exceed_count or would_exceed_size):
                # Finalize current batch and start new one
                batches.append(current_batch)
                if would_exceed_size and len(current_batch) < BATCH_SIZE:
                    log.debug(
                        f"Batch size limit triggered: {current_size / 1024:.1f} KB "
                        f"with {len(current_batch)} vectors (high-dim embeddings)"
                    )
                current_batch = [point]
                current_size = point_size
            else:
                current_batch.append(point)
                current_size += point_size

        if current_batch:
            batches.append(current_batch)

        return batches

    def _get_collection_name_with_prefix(self, collection_name: str) -> str:
        """Get the collection name with prefix."""
        return f"{self.collection_prefix}_{collection_name}"

    def _normalize_distance(self, score: float) -> float:
        """Normalize distance score based on the metric used."""
        if self.metric.lower() == "cosine":
            # Cosine similarity ranges from -1 to 1, normalize to 0 to 1
            return (score + 1.0) / 2.0
        elif self.metric.lower() in ["euclidean", "dotproduct"]:
            # These are already suitable for ranking (smaller is better for Euclidean)
            return score
        else:
            # For other metrics, use as is
            return score

    def _result_to_get_result(self, matches: list) -> GetResult:
        """Convert Pinecone matches to GetResult format."""
        ids = []
        documents = []
        metadatas = []

        for match in matches:
            metadata = getattr(match, "metadata", {}) or {}
            ids.append(match.id if hasattr(match, "id") else match["id"])
            documents.append(metadata.get("text", ""))
            metadatas.append(metadata)

        return GetResult(
            **{
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
            }
        )

    def has_collection(self, collection_name: str, namespace: str = None) -> bool:
        """Check if a collection exists by querying for at least one item with optional namespace."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        try:
            # Note: describe_index_stats with filter doesn't work on serverless indexes
            # Using query with dummy vector instead (works for all index types)
            query_kwargs = {
                "vector": [0.0] * self.dimension,
                "top_k": 1,
                "filter": {"collection_name": collection_name_with_prefix},
                "include_metadata": False,
                "include_values": False,  # Don't need vector values
            }
            if namespace:
                query_kwargs["namespace"] = namespace

            response = self._retry_pinecone_operation(lambda: self.index.query(**query_kwargs))
            matches = getattr(response, "matches", []) or []
            return len(matches) > 0

        except Exception as e:
            log.exception(
                f"Error checking collection '{collection_name_with_prefix}'"
                + (f" in namespace '{namespace}'" if namespace else "")
                + f": {e}"
            )
            return False

    def delete_collection(self, collection_name: str, namespace: str = None) -> None:
        """Delete a collection by removing all vectors with the collection name in metadata."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)
        try:
            delete_kwargs = {"filter": {"collection_name": collection_name_with_prefix}}
            if namespace:
                delete_kwargs["namespace"] = namespace

            self._retry_pinecone_operation(lambda: self.index.delete(**delete_kwargs))
            log.info(
                f"Collection '{collection_name_with_prefix}' deleted (all vectors removed)"
                + (f" from namespace '{namespace}'" if namespace else "")
                + "."
            )
        except Exception as e:
            log.warning(
                f"Failed to delete collection '{collection_name_with_prefix}'"
                + (f" from namespace '{namespace}'" if namespace else "")
                + f": {e}"
            )
            raise

    def insert(self, collection_name: str, items: List[VectorItem], namespace: str = None) -> None:
        """Insert vectors into a collection with optimized batching and optional namespace support."""
        if not items:
            log.warning("No items to insert")
            return

        start_time = time.time()

        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        # Log detailed information about what's being inserted
        namespace_info = f" in namespace '{namespace}'" if namespace else " in default namespace"
        log.info(
            f"Inserting {len(items)} items to Pinecone collection: {collection_name} (with prefix: {collection_name_with_prefix}){namespace_info}"
        )

        points = self._create_points(items, collection_name_with_prefix)

        # Use dynamic batching to respect both count and size limits
        batches = self._batch_points_by_size(points)

        log.debug(
            f"Inserting {len(points)} vectors in {len(batches)} batches "
            f"(avg {len(points) // len(batches) if batches else 0} vectors/batch)"
        )

        # Parallelize batch inserts for performance with retry logic
        executor = self._executor
        futures = []
        for batch in batches:
            # Include namespace in insert call if provided
            if namespace:
                futures.append(
                    executor.submit(
                        self._retry_pinecone_operation,
                        lambda b=batch, ns=namespace: self.index.upsert(vectors=b, namespace=ns),
                    )
                )
            else:
                futures.append(
                    executor.submit(
                        self._retry_pinecone_operation,
                        lambda b=batch: self.index.upsert(vectors=b),
                    )
                )

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log.error(f"Error inserting batch: {e}")
                raise

        elapsed = time.time() - start_time
        log.debug(f"Insert of {len(points)} vectors took {elapsed:.2f} seconds")
        log.info(
            f"Successfully inserted {len(points)} vectors in {len(batches)} parallel batches "
            f"into '{collection_name_with_prefix}'{namespace_info}"
        )

    def upsert(self, collection_name: str, items: List[VectorItem], namespace: str = None) -> None:
        """Upsert (insert or update) vectors into a collection with optional namespace support."""
        if not items:
            log.warning("No items to upsert")
            return

        start_time = time.time()

        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        # Log detailed information about what's being upserted
        namespace_info = f" in namespace '{namespace}'" if namespace else " in default namespace"
        log.info(
            f"Upserting {len(items)} items to Pinecone collection: {collection_name} (with prefix: {collection_name_with_prefix}){namespace_info}"
        )
        if items and items[0].get("metadata"):
            sample_metadata = items[0]["metadata"]
            log.info(
                f"Sample metadata - file_id: {sample_metadata.get('file_id')}, name: {sample_metadata.get('name')}, user_id: {sample_metadata.get('user_id')}"
            )

        points = self._create_points(items, collection_name_with_prefix)

        # Use dynamic batching to respect both count and size limits
        batches = self._batch_points_by_size(points)

        log.debug(
            f"Upserting {len(points)} vectors in {len(batches)} batches "
            f"(avg {len(points) // len(batches) if batches else 0} vectors/batch)"
        )

        # Parallelize batch upserts for performance with retry logic
        executor = self._executor
        futures = []
        for batch in batches:
            # Include namespace in upsert call if provided
            if namespace:
                futures.append(
                    executor.submit(
                        self._retry_pinecone_operation,
                        lambda b=batch, ns=namespace: self.index.upsert(vectors=b, namespace=ns),
                    )
                )
            else:
                futures.append(
                    executor.submit(
                        self._retry_pinecone_operation,
                        lambda b=batch: self.index.upsert(vectors=b),
                    )
                )

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log.error(f"Error upserting batch: {e}")
                raise

        elapsed = time.time() - start_time
        log.debug(f"Upsert of {len(points)} vectors took {elapsed:.2f} seconds")
        log.info(
            f"Successfully upserted {len(points)} vectors in {len(batches)} parallel batches "
            f"into '{collection_name_with_prefix}'{namespace_info}"
        )

    async def insert_async(self, collection_name: str, items: List[VectorItem]) -> None:
        """Async version of insert using asyncio and run_in_executor for improved performance."""
        if not items:
            log.warning("No items to insert")
            return

        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)
        points = self._create_points(items, collection_name_with_prefix)

        # Use dynamic batching to respect both count and size limits
        batches = self._batch_points_by_size(points)

        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, functools.partial(self.index.upsert, vectors=batch)) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.error(f"Error in async insert batch: {result}")
                raise result
        log.info(
            f"Successfully async inserted {len(points)} vectors in {len(batches)} batches "
            f"into '{collection_name_with_prefix}'"
        )

    async def upsert_async(self, collection_name: str, items: List[VectorItem]) -> None:
        """Async version of upsert using asyncio and run_in_executor for improved performance."""
        if not items:
            log.warning("No items to upsert")
            return

        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)
        points = self._create_points(items, collection_name_with_prefix)

        # Use dynamic batching to respect both count and size limits
        batches = self._batch_points_by_size(points)

        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, functools.partial(self.index.upsert, vectors=batch)) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.error(f"Error in async upsert batch: {result}")
                raise result
        log.info(
            f"Successfully async upserted {len(points)} vectors in {len(batches)} batches "
            f"into '{collection_name_with_prefix}'"
        )

    def search(
        self,
        collection_name: str,
        vectors: List[List[Union[float, int]]],
        filter: Optional[dict] = None,
        limit: int = 10,
        namespace: str = None,
    ) -> Optional[SearchResult]:
        """Search for similar vectors in a collection with optional namespace support."""
        if not vectors or not vectors[0]:
            log.warning("No vectors provided for search")
            return None

        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        if limit is None or limit <= 0:
            limit = NO_LIMIT

        try:
            # Search using the first vector (assuming this is the intended behavior)
            query_vector = vectors[0]

            # Perform the search with optional namespace
            query_kwargs = {
                "vector": query_vector,
                "top_k": limit,
                "include_metadata": True,
                "include_values": False,  # Don't return vector values - saves bandwidth
                "filter": {"collection_name": collection_name_with_prefix},
            }
            if namespace:
                query_kwargs["namespace"] = namespace

            query_response = self._retry_pinecone_operation(lambda: self.index.query(**query_kwargs))

            matches = getattr(query_response, "matches", []) or []
            if not matches:
                # Return empty result if no matches
                return SearchResult(
                    ids=[[]],
                    documents=[[]],
                    metadatas=[[]],
                    distances=[[]],
                )

            # Convert to GetResult format
            get_result = self._result_to_get_result(matches)

            # Calculate normalized distances based on metric
            distances = [[self._normalize_distance(getattr(match, "score", 0.0)) for match in matches]]

            return SearchResult(
                ids=get_result.ids,
                documents=get_result.documents,
                metadatas=get_result.metadatas,
                distances=distances,
            )
        except Exception as e:
            log.error(f"Error searching in '{collection_name_with_prefix}': {e}")
            return None

    def query(
        self,
        collection_name: str,
        filter: Dict,
        limit: Optional[int] = None,
        namespace: str = None,
    ) -> Optional[GetResult]:
        """Query vectors by metadata filter with optional namespace support."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        if limit is None or limit <= 0:
            limit = NO_LIMIT

        try:
            # Create a zero vector for the dimension as Pinecone requires a vector
            zero_vector = [0.0] * self.dimension

            # Combine user filter with collection_name
            # CRITICAL: Ensure collection_name filter is ALWAYS present to prevent cross-contamination
            pinecone_filter = {"collection_name": collection_name_with_prefix}
            if filter:
                # Never allow overriding the collection_name filter
                for key, value in filter.items():
                    if key != "collection_name":
                        pinecone_filter[key] = value
                    else:
                        log.warning(f"Attempted to override collection_name filter! Ignoring.")

            # Perform metadata-only query with optional namespace
            query_kwargs = {
                "vector": zero_vector,
                "filter": pinecone_filter,
                "top_k": limit,
                "include_metadata": True,
                "include_values": False,  # Metadata-only query - no need for vector values
            }
            if namespace:
                query_kwargs["namespace"] = namespace

            query_response = self._retry_pinecone_operation(lambda: self.index.query(**query_kwargs))

            matches = getattr(query_response, "matches", []) or []
            return self._result_to_get_result(matches)

        except Exception as e:
            log.error(f"Error querying collection '{collection_name}': {e}")
            return None

    def get(self, collection_name: str, namespace: str = None) -> Optional[GetResult]:
        """Get all vectors in a collection with optional namespace support."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        try:
            # Use a zero vector for fetching all entries
            zero_vector = [0.0] * self.dimension

            # Add filter to only get vectors for this collection
            query_kwargs = {
                "vector": zero_vector,
                "top_k": NO_LIMIT,
                "include_metadata": True,
                "include_values": False,  # Metadata-only fetch - no need for vector values
                "filter": {"collection_name": collection_name_with_prefix},
            }
            if namespace:
                query_kwargs["namespace"] = namespace

            query_response = self._retry_pinecone_operation(lambda: self.index.query(**query_kwargs))

            matches = getattr(query_response, "matches", []) or []
            return self._result_to_get_result(matches)

        except Exception as e:
            log.error(f"Error getting collection '{collection_name}': {e}")
            return None

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
        namespace: str = None,
    ) -> None:
        """Delete vectors by IDs or filter with optional namespace support."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(collection_name)

        try:
            if ids:
                # Delete by IDs (in batches for large deletions)
                for i in range(0, len(ids), BATCH_SIZE):
                    batch_ids = ids[i : i + BATCH_SIZE]
                    # Note: When deleting by ID, we can't filter by collection_name
                    # This is a limitation of Pinecone - be careful with ID uniqueness
                    delete_kwargs = {"ids": batch_ids}
                    if namespace:
                        delete_kwargs["namespace"] = namespace

                    self._retry_pinecone_operation(lambda kwargs=delete_kwargs: self.index.delete(**kwargs))

                    log.debug(
                        f"Deleted batch of {len(batch_ids)} vectors by ID "
                        f"from '{collection_name_with_prefix}'" + (f" in namespace '{namespace}'" if namespace else "")
                    )
                log.info(
                    f"Successfully deleted {len(ids)} vectors by ID "
                    f"from '{collection_name_with_prefix}'" + (f" in namespace '{namespace}'" if namespace else "")
                )

            elif filter:
                # Combine user filter with collection_name
                pinecone_filter = {"collection_name": collection_name_with_prefix}
                if filter:
                    pinecone_filter.update(filter)
                # Delete by metadata filter with optional namespace
                delete_kwargs = {"filter": pinecone_filter}
                if namespace:
                    delete_kwargs["namespace"] = namespace

                self._retry_pinecone_operation(lambda: self.index.delete(**delete_kwargs))

                log.info(
                    f"Successfully deleted vectors by filter from '{collection_name_with_prefix}'"
                    + (f" in namespace '{namespace}'" if namespace else "")
                )

            elif namespace:
                # Delete ALL vectors in the namespace (for force sync/reset)
                log.info(f"Deleting ALL vectors in namespace '{namespace}'...")
                delete_kwargs = {"delete_all": True, "namespace": namespace}

                self._retry_pinecone_operation(lambda: self.index.delete(**delete_kwargs))

                log.info(f"Successfully deleted ALL vectors in namespace '{namespace}'")

            else:
                log.warning("No ids, filter, or namespace provided for delete operation")

        except Exception as e:
            log.error(f"Error deleting from collection '{collection_name}': {e}")
            raise

    def reset(self) -> None:
        """Reset the database by deleting all collections."""
        try:
            self._retry_pinecone_operation(lambda: self.index.delete(delete_all=True))
            log.info("All vectors successfully deleted from the index.")
        except Exception as e:
            log.error(f"Failed to reset Pinecone index: {e}")
            raise

    def close(self):
        """Shut down resources."""
        try:
            # The new Pinecone client doesn't need explicit closing
            pass
        except Exception as e:
            log.warning(f"Failed to clean up Pinecone resources: {e}")
        self._executor.shutdown(wait=True)

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager, ensuring resources are cleaned up."""
        self.close()

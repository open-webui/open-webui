from typing import Optional, List, Dict, Any, Union
import logging
import time  # for measuring elapsed time
from pinecone import Pinecone, ServerlessSpec

import asyncio  # for async upserts
import functools  # for partial binding in async tasks

import concurrent.futures  # for parallel batch upserts

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
from open_webui.env import SRC_LOG_LEVELS

NO_LIMIT = 10000  # Reasonable limit to avoid overwhelming the system
BATCH_SIZE = 100  # Recommended batch size for Pinecone operations

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class PineconeClient(VectorDBBase):
    def __init__(self):
        self.collection_prefix = "open-webui"

        # Validate required configuration
        self._validate_config()

        # Store configuration values
        self.api_key = PINECONE_API_KEY
        self.environment = PINECONE_ENVIRONMENT
        self.index_name = PINECONE_INDEX_NAME
        self.dimension = PINECONE_DIMENSION
        self.metric = PINECONE_METRIC
        self.cloud = PINECONE_CLOUD

        # Initialize Pinecone client for improved performance
        self.client = Pinecone(api_key=self.api_key)

        # Persistent executor for batch operations
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

        # Create index if it doesn't exist
        self._initialize_index()

    def _validate_config(self) -> None:
        """Validate that all required configuration variables are set."""
        missing_vars = []
        if not PINECONE_API_KEY:
            missing_vars.append("PINECONE_API_KEY")
        if not PINECONE_ENVIRONMENT:
            missing_vars.append("PINECONE_ENVIRONMENT")
        if not PINECONE_INDEX_NAME:
            missing_vars.append("PINECONE_INDEX_NAME")
        if not PINECONE_DIMENSION:
            missing_vars.append("PINECONE_DIMENSION")
        if not PINECONE_CLOUD:
            missing_vars.append("PINECONE_CLOUD")

        if missing_vars:
            raise ValueError(
                f"Required configuration missing: {', '.join(missing_vars)}"
            )

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
            self.index = self.client.Index(self.index_name)

        except Exception as e:
            log.error(f"Failed to initialize Pinecone index: {e}")
            raise RuntimeError(f"Failed to initialize Pinecone index: {e}")

    def _create_points(
        self, items: List[VectorItem], collection_name_with_prefix: str
    ) -> List[Dict[str, Any]]:
        """Convert VectorItem objects to Pinecone point format."""
        points = []
        for item in items:
            # Start with any existing metadata or an empty dict
            metadata = item.get("metadata", {}).copy() if item.get("metadata") else {}

            # Add text to metadata if available
            if "text" in item:
                metadata["text"] = item["text"]

            # Always add collection_name to metadata for filtering
            metadata["collection_name"] = collection_name_with_prefix

            point = {
                "id": item["id"],
                "values": item["vector"],
                "metadata": metadata,
            }
            points.append(point)
        return points

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

    def has_collection(self, collection_name: str) -> bool:
        """Check if a collection exists by searching for at least one item."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )

        try:
            # Search for at least 1 item with this collection name in metadata
            response = self.index.query(
                vector=[0.0] * self.dimension,  # dummy vector
                top_k=1,
                filter={"collection_name": collection_name_with_prefix},
                include_metadata=False,
            )
            matches = getattr(response, "matches", []) or []
            return len(matches) > 0
        except Exception as e:
            log.exception(
                f"Error checking collection '{collection_name_with_prefix}': {e}"
            )
            return False

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection by removing all vectors with the collection name in metadata."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )
        try:
            self.index.delete(filter={"collection_name": collection_name_with_prefix})
            log.info(
                f"Collection '{collection_name_with_prefix}' deleted (all vectors removed)."
            )
        except Exception as e:
            log.warning(
                f"Failed to delete collection '{collection_name_with_prefix}': {e}"
            )
            raise

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        """Insert vectors into a collection."""
        if not items:
            log.warning("No items to insert")
            return

        start_time = time.time()

        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )
        points = self._create_points(items, collection_name_with_prefix)

        # Parallelize batch inserts for performance
        executor = self._executor
        futures = []
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i : i + BATCH_SIZE]
            futures.append(executor.submit(self.index.upsert, vectors=batch))
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log.error(f"Error inserting batch: {e}")
                raise
        elapsed = time.time() - start_time
        log.debug(f"Insert of {len(points)} vectors took {elapsed:.2f} seconds")
        log.info(
            f"Successfully inserted {len(points)} vectors in parallel batches into '{collection_name_with_prefix}'"
        )

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        """Upsert (insert or update) vectors into a collection."""
        if not items:
            log.warning("No items to upsert")
            return

        start_time = time.time()

        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )
        points = self._create_points(items, collection_name_with_prefix)

        # Parallelize batch upserts for performance
        executor = self._executor
        futures = []
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i : i + BATCH_SIZE]
            futures.append(executor.submit(self.index.upsert, vectors=batch))
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log.error(f"Error upserting batch: {e}")
                raise
        elapsed = time.time() - start_time
        log.debug(f"Upsert of {len(points)} vectors took {elapsed:.2f} seconds")
        log.info(
            f"Successfully upserted {len(points)} vectors in parallel batches into '{collection_name_with_prefix}'"
        )

    async def insert_async(self, collection_name: str, items: List[VectorItem]) -> None:
        """Async version of insert using asyncio and run_in_executor for improved performance."""
        if not items:
            log.warning("No items to insert")
            return

        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )
        points = self._create_points(items, collection_name_with_prefix)

        # Create batches
        batches = [
            points[i : i + BATCH_SIZE] for i in range(0, len(points), BATCH_SIZE)
        ]
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                None, functools.partial(self.index.upsert, vectors=batch)
            )
            for batch in batches
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.error(f"Error in async insert batch: {result}")
                raise result
        log.info(
            f"Successfully async inserted {len(points)} vectors in batches into '{collection_name_with_prefix}'"
        )

    async def upsert_async(self, collection_name: str, items: List[VectorItem]) -> None:
        """Async version of upsert using asyncio and run_in_executor for improved performance."""
        if not items:
            log.warning("No items to upsert")
            return

        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )
        points = self._create_points(items, collection_name_with_prefix)

        # Create batches
        batches = [
            points[i : i + BATCH_SIZE] for i in range(0, len(points), BATCH_SIZE)
        ]
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                None, functools.partial(self.index.upsert, vectors=batch)
            )
            for batch in batches
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.error(f"Error in async upsert batch: {result}")
                raise result
        log.info(
            f"Successfully async upserted {len(points)} vectors in batches into '{collection_name_with_prefix}'"
        )

    def search(
        self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
    ) -> Optional[SearchResult]:
        """Search for similar vectors in a collection."""
        if not vectors or not vectors[0]:
            log.warning("No vectors provided for search")
            return None

        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )

        if limit is None or limit <= 0:
            limit = NO_LIMIT

        try:
            # Search using the first vector (assuming this is the intended behavior)
            query_vector = vectors[0]

            # Perform the search
            query_response = self.index.query(
                vector=query_vector,
                top_k=limit,
                include_metadata=True,
                filter={"collection_name": collection_name_with_prefix},
            )

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
            distances = [
                [
                    self._normalize_distance(getattr(match, "score", 0.0))
                    for match in matches
                ]
            ]

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
        self, collection_name: str, filter: Dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """Query vectors by metadata filter."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )

        if limit is None or limit <= 0:
            limit = NO_LIMIT

        try:
            # Create a zero vector for the dimension as Pinecone requires a vector
            zero_vector = [0.0] * self.dimension

            # Combine user filter with collection_name
            pinecone_filter = {"collection_name": collection_name_with_prefix}
            if filter:
                pinecone_filter.update(filter)

            # Perform metadata-only query
            query_response = self.index.query(
                vector=zero_vector,
                filter=pinecone_filter,
                top_k=limit,
                include_metadata=True,
            )

            matches = getattr(query_response, "matches", []) or []
            return self._result_to_get_result(matches)

        except Exception as e:
            log.error(f"Error querying collection '{collection_name}': {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Get all vectors in a collection."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )

        try:
            # Use a zero vector for fetching all entries
            zero_vector = [0.0] * self.dimension

            # Add filter to only get vectors for this collection
            query_response = self.index.query(
                vector=zero_vector,
                top_k=NO_LIMIT,
                include_metadata=True,
                filter={"collection_name": collection_name_with_prefix},
            )

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
    ) -> None:
        """Delete vectors by IDs or filter."""
        collection_name_with_prefix = self._get_collection_name_with_prefix(
            collection_name
        )

        try:
            if ids:
                # Delete by IDs (in batches for large deletions)
                for i in range(0, len(ids), BATCH_SIZE):
                    batch_ids = ids[i : i + BATCH_SIZE]
                    # Note: When deleting by ID, we can't filter by collection_name
                    # This is a limitation of Pinecone - be careful with ID uniqueness
                    self.index.delete(ids=batch_ids)
                    log.debug(
                        f"Deleted batch of {len(batch_ids)} vectors by ID from '{collection_name_with_prefix}'"
                    )
                log.info(
                    f"Successfully deleted {len(ids)} vectors by ID from '{collection_name_with_prefix}'"
                )

            elif filter:
                # Combine user filter with collection_name
                pinecone_filter = {"collection_name": collection_name_with_prefix}
                if filter:
                    pinecone_filter.update(filter)
                # Delete by metadata filter
                self.index.delete(filter=pinecone_filter)
                log.info(
                    f"Successfully deleted vectors by filter from '{collection_name_with_prefix}'"
                )

            else:
                log.warning("No ids or filter provided for delete operation")

        except Exception as e:
            log.error(f"Error deleting from collection '{collection_name}': {e}")
            raise

    def reset(self) -> None:
        """Reset the database by deleting all collections."""
        try:
            self.index.delete(delete_all=True)
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

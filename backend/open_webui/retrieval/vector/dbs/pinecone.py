from typing import Optional, List, Dict, Any, Union
import logging
import asyncio
from pinecone import Pinecone, ServerlessSpec

# Helper for building consistent metadata
def build_metadata(
    *,
    source: str,
    type_: str,
    user_id: str,
    chat_id: Optional[str] = None,
    filename: Optional[str] = None,
    text: Optional[str] = None,
    topic: Optional[str] = None,
    model: Optional[str] = None,
    vector_dim: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    collection_name: Optional[str] = None,
) -> Dict[str, Any]:
    from datetime import datetime

    metadata = {
        "source": source,
        "type": type_,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if chat_id:
        metadata["chat_id"] = chat_id
    if filename:
        metadata["filename"] = filename
    if text:
        metadata["text"] = text
    if topic:
        metadata["topic"] = topic
    if model:
        metadata["model"] = model
    if vector_dim:
        metadata["vector_dim"] = vector_dim
    if collection_name:
        metadata["collection_name"] = collection_name
    if extra:
        metadata.update(extra)
    return metadata

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
        from open_webui.config import PINECONE_NAMESPACE
        self.namespace = PINECONE_NAMESPACE

        # Validate required configuration
        self._validate_config()

        # Store configuration values
        self.api_key = PINECONE_API_KEY
        self.environment = PINECONE_ENVIRONMENT
        self.index_name = PINECONE_INDEX_NAME
        self.dimension = PINECONE_DIMENSION
        self.metric = PINECONE_METRIC
        self.cloud = PINECONE_CLOUD

        # Initialize Pinecone client
        self.client = Pinecone(api_key=self.api_key)

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
            user_id = item.get("metadata", {}).get("created_by", "unknown")
            chat_id = item.get("metadata", {}).get("chat_id")
            filename = item.get("metadata", {}).get("name")
            text = item.get("text")
            model = item.get("metadata", {}).get("model")
            topic = item.get("metadata", {}).get("topic")

            # Infer source from filename or fallback
            raw_source = item.get("metadata", {}).get("source", "")
            inferred_source = "knowledge"
            if raw_source == filename or (isinstance(raw_source, str) and raw_source.endswith((".pdf", ".txt", ".docx"))):
                inferred_source = "chat" if item.get("metadata", {}).get("created_by") else "knowledge"
            else:
                inferred_source = raw_source or "knowledge"

            metadata = build_metadata(
                source=inferred_source,
                type_="upload",
                user_id=user_id,
                chat_id=chat_id,
                filename=filename,
                text=text,
                model=model,
                topic=topic,
                collection_name=collection_name_with_prefix,
            )

            point = {
                "id": item["id"],
                "values": item["vector"],
                "metadata": metadata,
            }
            points.append(point)
        return points

    def _get_namespace(self) -> str:
        """Get the namespace from the environment variable."""
        return self.namespace

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
            metadata = match.get("metadata", {})
            ids.append(match["id"])
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
        collection_name_with_prefix = self._get_namespace()

        try:
            # Search for at least 1 item with this collection name in metadata
            response = self.index.query(
                vector=[0.0] * self.dimension,  # dummy vector
                top_k=1,
                filter={"collection_name": collection_name_with_prefix},
                include_metadata=False,
            )
            return len(response.matches) > 0
        except Exception as e:
            log.exception(
                f"Error checking collection '{collection_name_with_prefix}': {e}"
            )
            return False

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection by removing all vectors with the collection name in metadata."""
        collection_name_with_prefix = self._get_namespace()
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

    async def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        """Insert vectors into a collection."""
        import time
        if not items:
            log.warning("No items to insert")
            return

        collection_name_with_prefix = self._get_namespace()
        points = self._create_points(items, collection_name_with_prefix)

        # Insert in batches for better performance and reliability
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i : i + BATCH_SIZE]
            try:
                start = time.time()
                await asyncio.to_thread(self.index.upsert, vectors=batch)
                elapsed = int((time.time() - start) * 1000)
                # Log line removed as requested
            except Exception as e:
                log.error(
                    f"Error inserting batch into '{collection_name_with_prefix}': {e}"
                )
                raise

        log.info(
            f"Successfully inserted {len(items)} vectors into '{collection_name_with_prefix}'"
        )

    async def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        """Upsert (insert or update) vectors into a collection."""
        import time
        if not items:
            log.warning("No items to upsert")
            return

        collection_name_with_prefix = self._get_namespace()
        points = self._create_points(items, collection_name_with_prefix)

        # Upsert in batches
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i : i + BATCH_SIZE]
            try:
                start = time.time()
                await asyncio.to_thread(self.index.upsert, vectors=batch)
                elapsed = int((time.time() - start) * 1000)
                # Log line removed as requested
            except Exception as e:
                log.error(
                    f"Error upserting batch into '{collection_name_with_prefix}': {e}"
                )
                raise

        log.info(
            f"Successfully upserted {len(items)} vectors into '{collection_name_with_prefix}'"
        )

    def search(
        self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
    ) -> Optional[SearchResult]:
        """Search for similar vectors in a collection."""
        if not vectors or not vectors[0]:
            log.warning("No vectors provided for search")
            return None

        collection_name_with_prefix = self._get_namespace()

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

            if not query_response.matches:
                # Return empty result if no matches
                return SearchResult(
                    ids=[[]],
                    documents=[[]],
                    metadatas=[[]],
                    distances=[[]],
                )

            # Convert to GetResult format
            get_result = self._result_to_get_result(query_response.matches)

            # Calculate normalized distances based on metric
            distances = [
                [
                    self._normalize_distance(match.score)
                    for match in query_response.matches
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
        collection_name_with_prefix = self._get_namespace()

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

            return self._result_to_get_result(query_response.matches)

        except Exception as e:
            log.error(f"Error querying collection '{collection_name}': {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Get all vectors in a collection."""
        collection_name_with_prefix = self._get_namespace()

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

            return self._result_to_get_result(query_response.matches)

        except Exception as e:
            log.error(f"Error getting collection '{collection_name}': {e}")
            return None

    async def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
    ) -> None:
        """Delete vectors by IDs or filter."""
        import time
        collection_name_with_prefix = self._get_namespace()

        try:
            if ids:
                # Delete by IDs (in batches for large deletions)
                for i in range(0, len(ids), BATCH_SIZE):
                    batch_ids = ids[i : i + BATCH_SIZE]
                    # Note: When deleting by ID, we can't filter by collection_name
                    # This is a limitation of Pinecone - be careful with ID uniqueness
                    start = time.time()
                    await asyncio.to_thread(self.index.delete, ids=batch_ids)
                    elapsed = int((time.time() - start) * 1000)
                    # Log line removed as requested
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

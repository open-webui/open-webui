from open_webui.retrieval.vector.utils import stringify_metadata
from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    GetResult,
    SearchResult,
)
from open_webui.config import S3_VECTOR_BUCKET_NAME, S3_VECTOR_REGION
from open_webui.env import SRC_LOG_LEVELS
from typing import List, Optional, Dict, Any, Union
import logging
import boto3

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class S3VectorClient(VectorDBBase):
    """
    AWS S3 Vector integration for Open WebUI Knowledge.
    """

    def __init__(self):
        self.bucket_name = S3_VECTOR_BUCKET_NAME
        self.region = S3_VECTOR_REGION

        # Simple validation - log warnings instead of raising exceptions
        if not self.bucket_name:
            log.warning("S3_VECTOR_BUCKET_NAME not set - S3Vector will not work")
        if not self.region:
            log.warning("S3_VECTOR_REGION not set - S3Vector will not work")

        if self.bucket_name and self.region:
            try:
                self.client = boto3.client("s3vectors", region_name=self.region)
                log.info(
                    f"S3Vector client initialized for bucket '{self.bucket_name}' in region '{self.region}'"
                )
            except Exception as e:
                log.error(f"Failed to initialize S3Vector client: {e}")
                self.client = None
        else:
            self.client = None

    def _create_index(
        self,
        index_name: str,
        dimension: int,
        data_type: str = "float32",
        distance_metric: str = "cosine",
    ) -> None:
        """
        Create a new index in the S3 vector bucket for the given collection if it does not exist.
        """
        if self.has_collection(index_name):
            log.debug(f"Index '{index_name}' already exists, skipping creation")
            return

        try:
            self.client.create_index(
                vectorBucketName=self.bucket_name,
                indexName=index_name,
                dataType=data_type,
                dimension=dimension,
                distanceMetric=distance_metric,
            )
            log.info(
                f"Created S3 index: {index_name} (dim={dimension}, type={data_type}, metric={distance_metric})"
            )
        except Exception as e:
            log.error(f"Error creating S3 index '{index_name}': {e}")
            raise

    def _filter_metadata(
        self, metadata: Dict[str, Any], item_id: str
    ) -> Dict[str, Any]:
        """
        Filter vector metadata keys to comply with S3 Vector API limit of 10 keys maximum.
        """
        if not isinstance(metadata, dict) or len(metadata) <= 10:
            return metadata

        # Keep only the first 10 keys, prioritizing important ones based on actual Open WebUI metadata
        important_keys = [
            "text",  # The actual document content
            "file_id",  # File ID
            "source",  # Document source file
            "title",  # Document title
            "page",  # Page number
            "total_pages",  # Total pages in document
            "embedding_config",  # Embedding configuration
            "created_by",  # User who created it
            "name",  # Document name
            "hash",  # Content hash
        ]
        filtered_metadata = {}

        # First, add important keys if they exist
        for key in important_keys:
            if key in metadata:
                filtered_metadata[key] = metadata[key]
            if len(filtered_metadata) >= 10:
                break

        # If we still have room, add other keys
        if len(filtered_metadata) < 10:
            for key, value in metadata.items():
                if key not in filtered_metadata:
                    filtered_metadata[key] = value
                    if len(filtered_metadata) >= 10:
                        break

        log.warning(
            f"Metadata for key '{item_id}' had {len(metadata)} keys, limited to 10 keys"
        )
        return filtered_metadata

    def has_collection(self, collection_name: str) -> bool:
        """
        Check if a vector index (collection) exists in the S3 vector bucket.
        """

        try:
            response = self.client.list_indexes(vectorBucketName=self.bucket_name)
            indexes = response.get("indexes", [])
            return any(idx.get("indexName") == collection_name for idx in indexes)
        except Exception as e:
            log.error(f"Error listing indexes: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire S3 Vector index/collection.
        """

        if not self.has_collection(collection_name):
            log.warning(
                f"Collection '{collection_name}' does not exist, nothing to delete"
            )
            return

        try:
            log.info(f"Deleting collection '{collection_name}'")
            self.client.delete_index(
                vectorBucketName=self.bucket_name, indexName=collection_name
            )
            log.info(f"Successfully deleted collection '{collection_name}'")
        except Exception as e:
            log.error(f"Error deleting collection '{collection_name}': {e}")
            raise

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        """
        Insert vector items into the S3 Vector index. Create index if it does not exist.
        """
        if not items:
            log.warning("No items to insert")
            return

        dimension = len(items[0]["vector"])

        try:
            if not self.has_collection(collection_name):
                log.info(f"Index '{collection_name}' does not exist. Creating index.")
                self._create_index(
                    index_name=collection_name,
                    dimension=dimension,
                    data_type="float32",
                    distance_metric="cosine",
                )

            # Prepare vectors for insertion
            vectors = []
            for item in items:
                # Ensure vector data is in the correct format for S3 Vector API
                vector_data = item["vector"]
                if isinstance(vector_data, list):
                    # Convert list to float32 values as required by S3 Vector API
                    vector_data = [float(x) for x in vector_data]

                # Prepare metadata, ensuring the text field is preserved
                metadata = item.get("metadata", {}).copy()

                # Add the text field to metadata so it's available for retrieval
                metadata["text"] = item["text"]

                # Convert metadata to string format for consistency
                metadata = stringify_metadata(metadata)

                # Filter metadata to comply with S3 Vector API limit of 10 keys
                metadata = self._filter_metadata(metadata, item["id"])

                vectors.append(
                    {
                        "key": item["id"],
                        "data": {"float32": vector_data},
                        "metadata": metadata,
                    }
                )
            # Insert vectors
            self.client.put_vectors(
                vectorBucketName=self.bucket_name,
                indexName=collection_name,
                vectors=vectors,
            )
            log.info(f"Inserted {len(vectors)} vectors into index '{collection_name}'.")
        except Exception as e:
            log.error(f"Error inserting vectors: {e}")
            raise

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        """
        Insert or update vector items in the S3 Vector index. Create index if it does not exist.
        """
        if not items:
            log.warning("No items to upsert")
            return

        dimension = len(items[0]["vector"])
        log.info(f"Upsert dimension: {dimension}")

        try:
            if not self.has_collection(collection_name):
                log.info(
                    f"Index '{collection_name}' does not exist. Creating index for upsert."
                )
                self._create_index(
                    index_name=collection_name,
                    dimension=dimension,
                    data_type="float32",
                    distance_metric="cosine",
                )

            # Prepare vectors for upsert
            vectors = []
            for item in items:
                # Ensure vector data is in the correct format for S3 Vector API
                vector_data = item["vector"]
                if isinstance(vector_data, list):
                    # Convert list to float32 values as required by S3 Vector API
                    vector_data = [float(x) for x in vector_data]

                # Prepare metadata, ensuring the text field is preserved
                metadata = item.get("metadata", {}).copy()
                # Add the text field to metadata so it's available for retrieval
                metadata["text"] = item["text"]

                # Convert metadata to string format for consistency
                metadata = stringify_metadata(metadata)

                # Filter metadata to comply with S3 Vector API limit of 10 keys
                metadata = self._filter_metadata(metadata, item["id"])

                vectors.append(
                    {
                        "key": item["id"],
                        "data": {"float32": vector_data},
                        "metadata": metadata,
                    }
                )
            # Upsert vectors (using put_vectors for upsert semantics)
            log.info(
                f"Upserting {len(vectors)} vectors. First vector sample: key={vectors[0]['key']}, data_type={type(vectors[0]['data']['float32'])}, data_len={len(vectors[0]['data']['float32'])}"
            )
            self.client.put_vectors(
                vectorBucketName=self.bucket_name,
                indexName=collection_name,
                vectors=vectors,
            )
            log.info(f"Upserted {len(vectors)} vectors into index '{collection_name}'.")
        except Exception as e:
            log.error(f"Error upserting vectors: {e}")
            raise

    def search(
        self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
    ) -> Optional[SearchResult]:
        """
        Search for similar vectors in a collection using multiple query vectors.
        """

        if not self.has_collection(collection_name):
            log.warning(f"Collection '{collection_name}' does not exist")
            return None

        if not vectors:
            log.warning("No query vectors provided")
            return None

        try:
            log.info(
                f"Searching collection '{collection_name}' with {len(vectors)} query vectors, limit={limit}"
            )

            # Initialize result lists
            all_ids = []
            all_documents = []
            all_metadatas = []
            all_distances = []

            # Process each query vector
            for i, query_vector in enumerate(vectors):
                log.debug(f"Processing query vector {i+1}/{len(vectors)}")

                # Prepare the query vector in S3 Vector format
                query_vector_dict = {"float32": [float(x) for x in query_vector]}

                # Call S3 Vector query API
                response = self.client.query_vectors(
                    vectorBucketName=self.bucket_name,
                    indexName=collection_name,
                    topK=limit,
                    queryVector=query_vector_dict,
                    returnMetadata=True,
                    returnDistance=True,
                )

                # Process results for this query
                query_ids = []
                query_documents = []
                query_metadatas = []
                query_distances = []

                result_vectors = response.get("vectors", [])

                for vector in result_vectors:
                    vector_id = vector.get("key")
                    vector_metadata = vector.get("metadata", {})
                    vector_distance = vector.get("distance", 0.0)

                    # Extract document text from metadata
                    document_text = ""
                    if isinstance(vector_metadata, dict):
                        # Get the text field first (highest priority)
                        document_text = vector_metadata.get("text")
                        if not document_text:
                            # Fallback to other possible text fields
                            document_text = (
                                vector_metadata.get("content")
                                or vector_metadata.get("document")
                                or vector_id
                            )
                    else:
                        document_text = vector_id

                    query_ids.append(vector_id)
                    query_documents.append(document_text)
                    query_metadatas.append(vector_metadata)
                    query_distances.append(vector_distance)

                # Add this query's results to the overall results
                all_ids.append(query_ids)
                all_documents.append(query_documents)
                all_metadatas.append(query_metadatas)
                all_distances.append(query_distances)

            log.info(f"Search completed. Found results for {len(all_ids)} queries")

            # Return SearchResult format
            return SearchResult(
                ids=all_ids if all_ids else None,
                documents=all_documents if all_documents else None,
                metadatas=all_metadatas if all_metadatas else None,
                distances=all_distances if all_distances else None,
            )

        except Exception as e:
            log.error(f"Error searching collection '{collection_name}': {str(e)}")
            # Handle specific AWS exceptions
            if hasattr(e, "response") and "Error" in e.response:
                error_code = e.response["Error"]["Code"]
                if error_code == "NotFoundException":
                    log.warning(f"Collection '{collection_name}' not found")
                    return None
                elif error_code == "ValidationException":
                    log.error(f"Invalid query vector dimensions or parameters")
                    return None
                elif error_code == "AccessDeniedException":
                    log.error(
                        f"Access denied for collection '{collection_name}'. Check permissions."
                    )
                    return None
            raise

    def query(
        self, collection_name: str, filter: Dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """
        Query vectors from a collection using metadata filter.
        """

        if not self.has_collection(collection_name):
            log.warning(f"Collection '{collection_name}' does not exist")
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        if not filter:
            log.warning("No filter provided, returning all vectors")
            return self.get(collection_name)

        try:
            log.info(f"Querying collection '{collection_name}' with filter: {filter}")

            # For S3 Vector, we need to use list_vectors and then filter results
            # Since S3 Vector may not support complex server-side filtering,
            # we'll retrieve all vectors and filter client-side

            # Get all vectors first
            all_vectors_result = self.get(collection_name)

            if not all_vectors_result or not all_vectors_result.ids:
                log.warning("No vectors found in collection")
                return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

            # Extract the lists from the result
            all_ids = all_vectors_result.ids[0] if all_vectors_result.ids else []
            all_documents = (
                all_vectors_result.documents[0] if all_vectors_result.documents else []
            )
            all_metadatas = (
                all_vectors_result.metadatas[0] if all_vectors_result.metadatas else []
            )

            # Apply client-side filtering
            filtered_ids = []
            filtered_documents = []
            filtered_metadatas = []

            for i, metadata in enumerate(all_metadatas):
                if self._matches_filter(metadata, filter):
                    if i < len(all_ids):
                        filtered_ids.append(all_ids[i])
                    if i < len(all_documents):
                        filtered_documents.append(all_documents[i])
                    filtered_metadatas.append(metadata)

                    # Apply limit if specified
                    if limit and len(filtered_ids) >= limit:
                        break

            log.info(
                f"Filter applied: {len(filtered_ids)} vectors match out of {len(all_ids)} total"
            )

            # Return GetResult format
            if filtered_ids:
                return GetResult(
                    ids=[filtered_ids],
                    documents=[filtered_documents],
                    metadatas=[filtered_metadatas],
                )
            else:
                return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        except Exception as e:
            log.error(f"Error querying collection '{collection_name}': {str(e)}")
            # Handle specific AWS exceptions
            if hasattr(e, "response") and "Error" in e.response:
                error_code = e.response["Error"]["Code"]
                if error_code == "NotFoundException":
                    log.warning(f"Collection '{collection_name}' not found")
                    return GetResult(ids=[[]], documents=[[]], metadatas=[[]])
                elif error_code == "AccessDeniedException":
                    log.error(
                        f"Access denied for collection '{collection_name}'. Check permissions."
                    )
                    return GetResult(ids=[[]], documents=[[]], metadatas=[[]])
            raise

    def get(self, collection_name: str) -> Optional[GetResult]:
        """
        Retrieve all vectors from a collection.
        """

        if not self.has_collection(collection_name):
            log.warning(f"Collection '{collection_name}' does not exist")
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        try:
            log.info(f"Retrieving all vectors from collection '{collection_name}'")

            # Initialize result lists
            all_ids = []
            all_documents = []
            all_metadatas = []

            # Handle pagination
            next_token = None

            while True:
                # Prepare request parameters
                request_params = {
                    "vectorBucketName": self.bucket_name,
                    "indexName": collection_name,
                    "returnData": False,  # Don't include vector data (not needed for get)
                    "returnMetadata": True,  # Include metadata
                    "maxResults": 500,  # Use reasonable page size
                }

                if next_token:
                    request_params["nextToken"] = next_token

                # Call S3 Vector API
                response = self.client.list_vectors(**request_params)

                # Process vectors in this page
                vectors = response.get("vectors", [])

                for vector in vectors:
                    vector_id = vector.get("key")
                    vector_data = vector.get("data", {})
                    vector_metadata = vector.get("metadata", {})

                    # Extract the actual vector array
                    vector_array = vector_data.get("float32", [])

                    # For documents, we try to extract text from metadata or use the vector ID
                    document_text = ""
                    if isinstance(vector_metadata, dict):
                        # Get the text field first (highest priority)
                        document_text = vector_metadata.get("text")
                        if not document_text:
                            # Fallback to other possible text fields
                            document_text = (
                                vector_metadata.get("content")
                                or vector_metadata.get("document")
                                or vector_id
                            )

                        # Log the actual content for debugging
                        log.debug(
                            f"Document text preview (first 200 chars): {str(document_text)[:200]}"
                        )
                    else:
                        document_text = vector_id

                    all_ids.append(vector_id)
                    all_documents.append(document_text)
                    all_metadatas.append(vector_metadata)

                # Check if there are more pages
                next_token = response.get("nextToken")
                if not next_token:
                    break

            log.info(
                f"Retrieved {len(all_ids)} vectors from collection '{collection_name}'"
            )

            # Return in GetResult format
            # The Open WebUI GetResult expects lists of lists, so we wrap each list
            if all_ids:
                return GetResult(
                    ids=[all_ids], documents=[all_documents], metadatas=[all_metadatas]
                )
            else:
                return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        except Exception as e:
            log.error(
                f"Error retrieving vectors from collection '{collection_name}': {str(e)}"
            )
            # Handle specific AWS exceptions
            if hasattr(e, "response") and "Error" in e.response:
                error_code = e.response["Error"]["Code"]
                if error_code == "NotFoundException":
                    log.warning(f"Collection '{collection_name}' not found")
                    return GetResult(ids=[[]], documents=[[]], metadatas=[[]])
                elif error_code == "AccessDeniedException":
                    log.error(
                        f"Access denied for collection '{collection_name}'. Check permissions."
                    )
                    return GetResult(ids=[[]], documents=[[]], metadatas=[[]])
            raise

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
    ) -> None:
        """
        Delete vectors by ID or filter from a collection.
        """

        if not self.has_collection(collection_name):
            log.warning(
                f"Collection '{collection_name}' does not exist, nothing to delete"
            )
            return

        # Check if this is a knowledge collection (not file-specific)
        is_knowledge_collection = not collection_name.startswith("file-")

        try:
            if ids:
                # Delete by specific vector IDs/keys
                log.info(
                    f"Deleting {len(ids)} vectors by IDs from collection '{collection_name}'"
                )
                self.client.delete_vectors(
                    vectorBucketName=self.bucket_name,
                    indexName=collection_name,
                    keys=ids,
                )
                log.info(f"Deleted {len(ids)} vectors from index '{collection_name}'")

            elif filter:
                # Handle filter-based deletion
                log.info(
                    f"Deleting vectors by filter from collection '{collection_name}': {filter}"
                )

                # If this is a knowledge collection and we have a file_id filter,
                # also clean up the corresponding file-specific collection
                if is_knowledge_collection and "file_id" in filter:
                    file_id = filter["file_id"]
                    file_collection_name = f"file-{file_id}"
                    if self.has_collection(file_collection_name):
                        log.info(
                            f"Found related file-specific collection '{file_collection_name}', deleting it to prevent duplicates"
                        )
                        self.delete_collection(file_collection_name)

                # For the main collection, implement query-then-delete
                # First, query to get IDs matching the filter
                query_result = self.query(collection_name, filter)
                if query_result and query_result.ids and query_result.ids[0]:
                    matching_ids = query_result.ids[0]
                    log.info(
                        f"Found {len(matching_ids)} vectors matching filter, deleting them"
                    )

                    # Delete the matching vectors by ID
                    self.client.delete_vectors(
                        vectorBucketName=self.bucket_name,
                        indexName=collection_name,
                        keys=matching_ids,
                    )
                    log.info(
                        f"Deleted {len(matching_ids)} vectors from index '{collection_name}' using filter"
                    )
                else:
                    log.warning("No vectors found matching the filter criteria")
            else:
                log.warning("No IDs or filter provided for deletion")
        except Exception as e:
            log.error(
                f"Error deleting vectors from collection '{collection_name}': {e}"
            )
            raise

    def reset(self) -> None:
        """
        Reset/clear all vector data. For S3 Vector, this deletes all indexes.
        """

        try:
            log.warning(
                "Reset called - this will delete all vector indexes in the S3 bucket"
            )

            # List all indexes
            response = self.client.list_indexes(vectorBucketName=self.bucket_name)
            indexes = response.get("indexes", [])

            if not indexes:
                log.warning("No indexes found to delete")
                return

            # Delete all indexes
            deleted_count = 0
            for index in indexes:
                index_name = index.get("indexName")
                if index_name:
                    try:
                        self.client.delete_index(
                            vectorBucketName=self.bucket_name, indexName=index_name
                        )
                        deleted_count += 1
                        log.info(f"Deleted index: {index_name}")
                    except Exception as e:
                        log.error(f"Error deleting index '{index_name}': {e}")

            log.info(f"Reset completed: deleted {deleted_count} indexes")

        except Exception as e:
            log.error(f"Error during reset: {e}")
            raise

    def _matches_filter(self, metadata: Dict[str, Any], filter: Dict[str, Any]) -> bool:
        """
        Check if metadata matches the given filter conditions.
        """
        if not isinstance(metadata, dict) or not isinstance(filter, dict):
            return False

        # Check each filter condition
        for key, expected_value in filter.items():
            # Handle special operators
            if key.startswith("$"):
                if key == "$and":
                    # All conditions must match
                    if not isinstance(expected_value, list):
                        continue
                    for condition in expected_value:
                        if not self._matches_filter(metadata, condition):
                            return False
                elif key == "$or":
                    # At least one condition must match
                    if not isinstance(expected_value, list):
                        continue
                    any_match = False
                    for condition in expected_value:
                        if self._matches_filter(metadata, condition):
                            any_match = True
                            break
                    if not any_match:
                        return False
                continue

            # Get the actual value from metadata
            actual_value = metadata.get(key)

            # Handle different types of expected values
            if isinstance(expected_value, dict):
                # Handle comparison operators
                for op, op_value in expected_value.items():
                    if op == "$eq":
                        if actual_value != op_value:
                            return False
                    elif op == "$ne":
                        if actual_value == op_value:
                            return False
                    elif op == "$in":
                        if (
                            not isinstance(op_value, list)
                            or actual_value not in op_value
                        ):
                            return False
                    elif op == "$nin":
                        if isinstance(op_value, list) and actual_value in op_value:
                            return False
                    elif op == "$exists":
                        if bool(op_value) != (key in metadata):
                            return False
                    # Add more operators as needed
            else:
                # Simple equality check
                if actual_value != expected_value:
                    return False

        return True

import logging
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse

from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_GRPC_PORT,
    QDRANT_ON_DISK,
    QDRANT_PREFER_GRPC,
    QDRANT_URI,
    QDRANT_COLLECTION_PREFIX,
    QDRANT_TIMEOUT,
    QDRANT_HNSW_M,
    ENABLE_RAG_HYBRID_SEARCH,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from qdrant_client import QdrantClient as Qclient
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
        self.QDRANT_TIMEOUT = QDRANT_TIMEOUT
        self.QDRANT_HNSW_M = QDRANT_HNSW_M

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
                timeout=self.QDRANT_TIMEOUT,
            )
            if self.PREFER_GRPC
            else Qclient(
                url=self.QDRANT_URI,
                api_key=self.QDRANT_API_KEY,
                timeout=self.QDRANT_TIMEOUT,
            )
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

        WARNING: This mapping relies on current Open WebUI naming conventions for
        collection names. If Open WebUI changes how it generates collection names
        (e.g., "user-memory-" prefix, "file-" prefix, web search patterns, or hash
        formats), this mapping will break and route data to incorrect collections.
        POTENTIALLY CAUSING HUGE DATA CORRUPTION, DATA CONSISTENCY ISSUES AND INCORRECT
        DATA MAPPING INSIDE THE DATABASE.
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
        Also creates sparse vector configuration for hybrid search support.
        """
        # Create collection with both dense and sparse vector support
        self.client.create_collection(
            collection_name=mt_collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                    on_disk=self.QDRANT_ON_DISK,
                )
            },
            # Disable global index building due to multitenancy
            # For more details https://qdrant.tech/documentation/guides/multiple-partitions/#calibrate-performance
            hnsw_config=models.HnswConfigDiff(
                payload_m=self.QDRANT_HNSW_M,
                m=0,
            ),
            # Add sparse vectors configuration for BM25-like hybrid search
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                )
            },
        )
        log.info(
            f"Multi-tenant collection {mt_collection_name} created with dimension {dimension} and sparse vector support!"
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

    def _hybrid_search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: str,
        limit: int,
    ) -> Optional[SearchResult]:
        """
        Perform Qdrant native hybrid search using prefetch + RRF fusion.
        
        This method uses Qdrant's named vectors (dense + sparse) with prefetch queries
        and applies RRF (Reciprocal Rank Fusion) for optimal result combination.
        
        Args:
            collection_name: Name of the collection to search
            query_vector: Dense vector representation of the query
            query_text: Text query for sparse vector generation
            limit: Maximum number of results to return
            
        Returns:
            SearchResult with RRF-fused hybrid results
        """
        if not self.client or not query_vector:
            return None
            
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, hybrid search returns None")
            return None

        tenant_filter = _tenant_filter(tenant_id)
        
        try:
            # Use Qdrant's native hybrid search with prefetch + RRF fusion (like user's example)
            # Generate sparse vector from query text using FastEmbed or fallback
            sparse_vector = self._query_to_sparse_vector(query_text)
            
            # Create prefetch queries for both dense and sparse vectors
            prefetch_queries = [
                # Dense vector prefetch
                models.Prefetch(
                    query=query_vector,
                    using="dense",
                    limit=limit * 2,  # Get more candidates for better fusion
                    filter=models.Filter(must=[tenant_filter]),
                )
            ]
            
            # Add sparse vector prefetch if we have terms
            if sparse_vector["indices"]:
                prefetch_queries.append(
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_vector["indices"],
                            values=sparse_vector["values"],
                        ),
                        using="bm25",
                        limit=limit * 2,
                        filter=models.Filter(must=[tenant_filter]),
                    )
                )
            
            # Use Qdrant's native fusion - RRF is currently the most robust option
            # For custom weighting, Qdrant supports score formulas (see alternative implementation below)
            query_response = self.client.query_points(
                collection_name=mt_collection,
                prefetch=prefetch_queries,
                query=models.FusionQuery(
                    fusion=models.Fusion.RRF,
                ),
                limit=limit,
                with_payload=True,
            )
            
            get_result = self._result_to_get_result(query_response.points)
            return SearchResult(
                ids=get_result.ids,
                documents=get_result.documents,
                metadatas=get_result.metadatas,
                distances=[[(point.score + 1.0) / 2.0 for point in query_response.points]],
            )
            
        except Exception as e:
            log.warning(f"Qdrant native hybrid search failed, trying fallback: {e}")
            
            # Fallback to client-side hybrid scoring if native approach fails
            try:
                candidates_limit = max(limit * 3, 100)
                dense_results = self.client.query_points(
                    collection_name=mt_collection,
                    query=query_vector,
                    using="dense",  # Use named dense vector
                    limit=candidates_limit,
                    query_filter=models.Filter(must=[tenant_filter]),
                )
                
                # Apply simple score normalization for fallback
                get_result = self._result_to_get_result(dense_results.points)
                return SearchResult(
                    ids=get_result.ids,
                    documents=get_result.documents,
                    metadatas=get_result.metadatas,
                    distances=[[(point.score + 1.0) / 2.0 for point in dense_results.points]],
                )
                
            except Exception as e2:
                log.warning(f"Fallback hybrid search failed: {e2}")
                # Final fallback to regular dense search
                return self.search(collection_name, [query_vector], limit)


    def _get_bm25_embedding_model(self):
        """
        Get or create the BM25 embedding model using FastEmbed.
        """
        if not hasattr(self, '_bm25_model') or self._bm25_model is None:
            try:
                from fastembed import SparseTextEmbedding  # type: ignore
                self._bm25_model = SparseTextEmbedding("Qdrant/bm25")
                log.info("Initialized FastEmbed BM25 sparse embedding model")
            except ImportError:
                log.warning("FastEmbed not available, will use fallback sparse vector generation")
                self._bm25_model = None
            except Exception as e:
                log.warning(f"Failed to initialize FastEmbed BM25 model: {e}")
                self._bm25_model = None
        return self._bm25_model

    def _text_to_sparse_vector(self, text: str) -> Dict[str, List]:
        """
        Convert text to sparse vector representation using FastEmbed's BM25 model.
        Falls back to simple implementation if FastEmbed is not available.
        """
        if not text:
            return {"indices": [], "values": []}
        
        # Try to use FastEmbed's BM25 model first
        bm25_model = self._get_bm25_embedding_model()
        if bm25_model is not None:
            try:
                # Use FastEmbed to generate proper BM25 sparse embedding
                sparse_embeddings = list(bm25_model.passage_embed([text]))
                if sparse_embeddings and len(sparse_embeddings) > 0:
                    sparse_embedding = sparse_embeddings[0]
                    # Convert to the format expected by Qdrant
                    return {
                        "indices": sparse_embedding.indices.tolist(),
                        "values": sparse_embedding.values.tolist()
                    }
            except Exception as e:
                log.warning(f"FastEmbed BM25 embedding failed: {e}, using fallback")
        
        # No FastEmbed available, return empty sparse vector
        return {"indices": [], "values": []}

    def _query_to_sparse_vector(self, query_text: str) -> Dict[str, List]:
        """
        Convert query text to sparse vector representation using FastEmbed's BM25 model.
        Uses query_embed for better query representation vs passage_embed.
        """
        if not query_text:
            return {"indices": [], "values": []}
        
        # Try to use FastEmbed's BM25 model for query embedding
        bm25_model = self._get_bm25_embedding_model()
        if bm25_model is not None:
            try:
                # Use query_embed for queries (optimized for query representation)
                sparse_embeddings = list(bm25_model.query_embed([query_text]))
                if sparse_embeddings and len(sparse_embeddings) > 0:
                    sparse_embedding = sparse_embeddings[0]
                    # Convert to the format expected by Qdrant
                    return {
                        "indices": sparse_embedding.indices.tolist(),
                        "values": sparse_embedding.values.tolist()
                    }
            except Exception as e:
                log.warning(f"FastEmbed BM25 query embedding failed: {e}, using fallback")
        
        # No FastEmbed available, return empty sparse vector
        return {"indices": [], "values": []}



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
        self, collection_name: str, vectors: List[List[float | int]], limit: int, query_text: Optional[str] = None
    ) -> Optional[SearchResult]:
        """
        Search for the nearest neighbor items based on the vectors with tenant isolation.
        Uses hybrid search when ENABLE_RAG_HYBRID_SEARCH is True and query_text is provided.
        """
        if not self.client or not vectors:
            return None
        
        # Use hybrid search if enabled and query text is available
        if ENABLE_RAG_HYBRID_SEARCH and query_text:
            return self._hybrid_search(
                collection_name=collection_name,
                query_vector=vectors[0],
                query_text=query_text,
                limit=limit
            )
        
        # Fallback to regular dense vector search
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, search returns None")
            return None

        tenant_filter = _tenant_filter(tenant_id)
        try:
            # Try to use named dense vector first (for hybrid-enabled collections)
            query_response = self.client.query_points(
                collection_name=mt_collection,
                query=vectors[0],
                using="dense",
                limit=limit,
                query_filter=models.Filter(must=[tenant_filter]),
            )
        except Exception:
            # Fallback for collections without named vectors (legacy collections)
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
        points = self.client.scroll(
            collection_name=mt_collection,
            scroll_filter=combined_filter,
            limit=limit,
        )
        return self._result_to_get_result(points[0])

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
        points = self.client.scroll(
            collection_name=mt_collection,
            scroll_filter=models.Filter(must=[tenant_filter]),
            limit=NO_LIMIT,
        )
        return self._result_to_get_result(points[0])

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """
        Upsert items with tenant ID, dense vectors, and sparse vectors for hybrid search.
        """
        if not self.client or not items:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        dimension = len(items[0]["vector"])  # type: ignore  # Items are dicts, not VectorItem instances
        self._ensure_collection(mt_collection, dimension)
        
        # Create points with both dense and sparse vectors
        points = []
        for item in items:
            # Generate sparse vector from text content for BM25-like search
            sparse_vector = self._text_to_sparse_vector(item["text"])  # type: ignore
            
            # Create vector dict with named vectors (similar to user's example)
            vector_dict = {
                "dense": item["vector"],  # type: ignore  # Dense semantic vector
            }
            
            # Add sparse vector if we have terms
            if sparse_vector["indices"]:
                vector_dict["bm25"] = models.SparseVector(  # type: ignore
                    indices=sparse_vector["indices"],
                    values=sparse_vector["values"],
                )
            
            points.append(
                PointStruct(
                    id=item["id"],  # type: ignore
                    vector=vector_dict,  # type: ignore  # Qdrant client accepts dict for named vectors
                    payload={
                        "text": item["text"],  # type: ignore
                        "metadata": item["metadata"],  # type: ignore
                        TENANT_ID_FIELD: tenant_id,
                    },
                )
            )
        
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

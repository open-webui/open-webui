"""
NOTE: This vector database integration is community-supported and maintained on a best-effort basis.
"""

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
    QDRANT_TIMEOUT,
    QDRANT_HNSW_M,
    QDRANT_HYBRID_SEARCH_ENABLED,
    QDRANT_SPARSE_EMBEDDING_MODEL,
    QDRANT_DENSE_VECTOR_NAME,
    QDRANT_SPARSE_VECTOR_NAME,
    QDRANT_HYBRID_SEARCH_FUSION_TYPE,
    QDRANT_SPARSE_ON_DISK,
)

from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from qdrant_client import QdrantClient as Qclient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import PointStruct, SparseVector
from qdrant_client.models import models

try:
    from fastembed.sparse import SparseTextEmbedding

    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False

NO_LIMIT = 999999999
TENANT_ID_FIELD = 'tenant_id'
DEFAULT_DIMENSION = 384

log = logging.getLogger(__name__)


def _tenant_filter(tenant_id: str) -> models.FieldCondition:
    return models.FieldCondition(key=TENANT_ID_FIELD, match=models.MatchValue(value=tenant_id))


def _metadata_filter(key: str, value: Any) -> models.FieldCondition:
    return models.FieldCondition(key=f'metadata.{key}', match=models.MatchValue(value=value))


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
        self.QDRANT_HYBRID_SEARCH_ENABLED = QDRANT_HYBRID_SEARCH_ENABLED
        self.QDRANT_SPARSE_EMBEDDING_MODEL = QDRANT_SPARSE_EMBEDDING_MODEL
        self.QDRANT_DENSE_VECTOR_NAME = QDRANT_DENSE_VECTOR_NAME
        self.QDRANT_SPARSE_VECTOR_NAME = QDRANT_SPARSE_VECTOR_NAME
        self.QDRANT_HYBRID_SEARCH_FUSION_TYPE = QDRANT_HYBRID_SEARCH_FUSION_TYPE
        self.QDRANT_SPARSE_ON_DISK = QDRANT_SPARSE_ON_DISK

        if not self.QDRANT_URI:
            raise ValueError('QDRANT_URI is not set. Please configure it in the environment variables.')

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
        self.MEMORY_COLLECTION = f'{self.collection_prefix}_memories'
        self.KNOWLEDGE_COLLECTION = f'{self.collection_prefix}_knowledge'
        self.FILE_COLLECTION = f'{self.collection_prefix}_files'
        self.WEB_SEARCH_COLLECTION = f'{self.collection_prefix}_web-search'
        self.HASH_BASED_COLLECTION = f'{self.collection_prefix}_hash-based'

        # Initialize sparse encoder if hybrid search is enabled
        self.sparse_encoder = None
        if self.QDRANT_HYBRID_SEARCH_ENABLED:
            if FASTEMBED_AVAILABLE:
                try:
                    self.sparse_encoder = SparseTextEmbedding(model_name=self.QDRANT_SPARSE_EMBEDDING_MODEL)
                    log.info(f'Hybrid search enabled with sparse model: {self.QDRANT_SPARSE_EMBEDDING_MODEL}')
                except Exception as e:
                    log.warning(f'Failed to load sparse encoder, hybrid search disabled: {e}')
            else:
                log.warning(
                    "fastembed not installed, hybrid search disabled. Install with: pip install 'fastembed>=0.6.1'"
                )
    @property
    def _hybrid_enabled(self) -> bool:
        return self.QDRANT_HYBRID_SEARCH_ENABLED and self.sparse_encoder is not None

    def _is_hybrid_collection(self, mt_collection_name: str) -> bool:
        """Check if an existing collection has sparse vectors (i.e. was created as hybrid)."""
        try:
            info = self.client.get_collection(mt_collection_name)
            return bool(info.config.params.sparse_vectors)
        except Exception:
            return False

    def _encode_sparse(self, texts: list[str]) -> list[SparseVector]:
        """Encode texts into sparse vectors using fastembed."""
        embeddings = list(self.sparse_encoder.embed(texts))
        return [SparseVector(indices=e.indices.tolist(), values=e.values.tolist()) for e in embeddings]

    def _encode_sparse_query(self, text: str) -> SparseVector:
        """Encode a query text into a sparse vector."""
        embeddings = list(self.sparse_encoder.query_embed(text))
        e = embeddings[0]
        return SparseVector(indices=e.indices.tolist(), values=e.values.tolist())

    def _result_to_get_result(self, points) -> GetResult:
        ids, documents, metadatas = [], [], []
        for point in points:
            payload = point.payload
            ids.append(point.id)
            documents.append(payload['text'])
            metadatas.append(payload['metadata'])
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

        if collection_name.startswith('user-memory-'):
            return self.MEMORY_COLLECTION, tenant_id

        # Check for file collections
        elif collection_name.startswith('file-'):
            return self.FILE_COLLECTION, tenant_id

        # Check for web search collections
        elif collection_name.startswith('web-search-'):
            return self.WEB_SEARCH_COLLECTION, tenant_id

        # Handle hash-based collections (YouTube and web URLs)
        elif len(collection_name) == 63 and all(c in '0123456789abcdef' for c in collection_name):
            return self.HASH_BASED_COLLECTION, tenant_id

        else:
            return self.KNOWLEDGE_COLLECTION, tenant_id

    def _create_multi_tenant_collection(self, mt_collection_name: str, dimension: int = DEFAULT_DIMENSION):
        """
        Creates a collection with multi-tenancy configuration and payload indexes for tenant_id and metadata fields.
        """
        if self._hybrid_enabled:
            self.client.create_collection(
                collection_name=mt_collection_name,
                vectors_config={
                    self.QDRANT_DENSE_VECTOR_NAME: models.VectorParams(
                        size=dimension,
                        distance=models.Distance.COSINE,
                        on_disk=self.QDRANT_ON_DISK,
                    )
                },
                sparse_vectors_config={
                    self.QDRANT_SPARSE_VECTOR_NAME: models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=self.QDRANT_SPARSE_ON_DISK)
                    )
                },
                hnsw_config=models.HnswConfigDiff(
                    payload_m=self.QDRANT_HNSW_M,
                    m=0,
                ),
            )
            log.info(
                f'Multi-tenant hybrid collection {mt_collection_name} created with '
                f'dense ({dimension} dims) + sparse vectors'
            )
        else:
            self.client.create_collection(
                collection_name=mt_collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                    on_disk=self.QDRANT_ON_DISK,
                ),
                # Disable global index building due to multitenancy
                # For more details https://qdrant.tech/documentation/guides/multiple-partitions/#calibrate-performance
                hnsw_config=models.HnswConfigDiff(
                    payload_m=self.QDRANT_HNSW_M,
                    m=0,
                ),
            )
            log.info(f'Multi-tenant collection {mt_collection_name} created with dimension {dimension}')

        self.client.create_payload_index(
            collection_name=mt_collection_name,
            field_name=TENANT_ID_FIELD,
            field_schema=models.KeywordIndexParams(
                type=models.KeywordIndexType.KEYWORD,
                is_tenant=True,
                on_disk=self.QDRANT_ON_DISK,
            ),
        )

        for field in ('metadata.hash', 'metadata.file_id'):
            self.client.create_payload_index(
                collection_name=mt_collection_name,
                field_name=field,
                field_schema=models.KeywordIndexParams(
                    type=models.KeywordIndexType.KEYWORD,
                    on_disk=self.QDRANT_ON_DISK,
                ),
            )

    def _create_points(
        self, items: list[VectorItem], tenant_id: str, collection_is_hybrid: bool = False
    ) -> list[PointStruct]:
        """
        Create point structs from vector items with tenant ID.
        Uses named vectors when collection_is_hybrid is True.
        If hybrid is also enabled in config, adds sparse vectors; otherwise dense-only named vector.
        """
        if collection_is_hybrid:
            if self._hybrid_enabled:
                texts = [item['text'] for item in items]
                sparse_vectors = self._encode_sparse(texts)
                return [
                    PointStruct(
                        id=item['id'],
                        vector={
                            self.QDRANT_DENSE_VECTOR_NAME: item['vector'],
                            self.QDRANT_SPARSE_VECTOR_NAME: sparse_vec,
                        },
                        payload={
                            'text': item['text'],
                            'metadata': item['metadata'],
                            TENANT_ID_FIELD: tenant_id,
                        },
                    )
                    for item, sparse_vec in zip(items, sparse_vectors)
                ]
            else:
                # Collection is hybrid but encoder unavailable — store only dense named vector
                return [
                    PointStruct(
                        id=item['id'],
                        vector={self.QDRANT_DENSE_VECTOR_NAME: item['vector']},
                        payload={
                            'text': item['text'],
                            'metadata': item['metadata'],
                            TENANT_ID_FIELD: tenant_id,
                        },
                    )
                    for item in items
                ]
        else:
            return [
                PointStruct(
                    id=item['id'],
                    vector=item['vector'],
                    payload={
                        'text': item['text'],
                        'metadata': item['metadata'],
                        TENANT_ID_FIELD: tenant_id,
                    },
                )
                for item in items
            ]

    def _ensure_collection(self, mt_collection_name: str, dimension: int = DEFAULT_DIMENSION):
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
            should_conditions = [_metadata_filter('id', id_value) for id_value in ids]
        elif filter:
            must_conditions += [_metadata_filter(k, v) for k, v in filter.items()]

        return self.client.delete(
            collection_name=mt_collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=must_conditions, should=should_conditions)),
        )

    def search(
        self,
        collection_name: str,
        vectors: List[List[float | int]],
        filter: Optional[Dict] = None,
        limit: int = 10,
        query: Optional[str] = None,
    ) -> Optional[SearchResult]:
        """
        Search for the nearest neighbor items based on the vectors with tenant isolation.
        Uses hybrid search (dense + sparse RRF) when enabled and query is provided.
        """
        if not self.client or not vectors:
            return None
        if limit is None:
            limit = NO_LIMIT  # otherwise qdrant would set limit to 10!
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        if not self.client.collection_exists(collection_name=mt_collection):
            log.debug(f"Collection {mt_collection} doesn't exist, search returns None")
            return None

        tenant_filter = _tenant_filter(tenant_id)
        combined_filter = models.Filter(must=[tenant_filter])

        collection_is_hybrid = self._is_hybrid_collection(mt_collection)

        # Hybrid search with server-side fusion (RRF or DBSF)
        if collection_is_hybrid and self._hybrid_enabled and query:
            sparse_query = self._encode_sparse_query(query)
            fusion = (
                models.Fusion.DBSF
                if self.QDRANT_HYBRID_SEARCH_FUSION_TYPE == 'dbsf'
                else models.Fusion.RRF
            )
            query_response = self.client.query_points(
                collection_name=mt_collection,
                query=models.FusionQuery(fusion=fusion),
                prefetch=[
                    models.Prefetch(
                        query=vectors[0],
                        using=self.QDRANT_DENSE_VECTOR_NAME,
                        filter=combined_filter,
                        limit=limit * 2,
                    ),
                    models.Prefetch(
                        query=sparse_query,
                        using=self.QDRANT_SPARSE_VECTOR_NAME,
                        filter=combined_filter,
                        limit=limit * 2,
                    ),
                ],
                limit=limit,
            )
        else:
            # Dense-only search — use named vector if collection schema requires it
            query_vector = (self.QDRANT_DENSE_VECTOR_NAME, vectors[0]) if collection_is_hybrid else vectors[0]
            query_response = self.client.query_points(
                collection_name=mt_collection,
                query=query_vector,
                limit=limit,
                query_filter=combined_filter,
            )

        get_result = self._result_to_get_result(query_response.points)
        return SearchResult(
            ids=get_result.ids,
            documents=get_result.documents,
            metadatas=get_result.metadatas,
            distances=[[(point.score + 1.0) / 2.0 for point in query_response.points]],
        )

    def query(self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None):
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
        Upsert items with tenant ID.
        """
        if not self.client or not items:
            return None
        mt_collection, tenant_id = self._get_collection_and_tenant_id(collection_name)
        dimension = len(items[0]['vector'])
        self._ensure_collection(mt_collection, dimension)
        collection_is_hybrid = self._is_hybrid_collection(mt_collection)
        points = self._create_points(items, tenant_id, collection_is_hybrid)
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
            points_selector=models.FilterSelector(filter=models.Filter(must=[_tenant_filter(tenant_id)])),
        )

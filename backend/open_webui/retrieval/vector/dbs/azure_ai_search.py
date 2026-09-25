"""
Azure AI Search vector database backend for Open WebUI.

Integrates Azure AI Search as a VECTOR_DB backend.
Implements VectorDBBase interface for OWUI's RAG pipeline.

Environment variables:
    AZURE_SEARCH_ENDPOINT         – Azure AI Search service endpoint
    AZURE_SEARCH_ADMIN_KEY        – Admin API key (needed for CRUD operations)
    AZURE_SEARCH_API_VERSION      – API version (default: 2024-07-01)
    AZURE_SEARCH_TYPE             – vector | fulltext | hybrid | semantic (default: hybrid)
    AZURE_ENABLE_SEMANTIC_SEARCH  – true | false (default: false)
    AZURE_SEARCH_NAMESPACE_MODE   – true | false (default: false)
        When enabled, groups OWUI collections into shared indexes to avoid
        the 200-index limit.  KBs → "owui-knowledge", files → "owui-files",
        memory → "owui-memory".  Filtering is handled via a ``collection_key``
        field stored in each document.

Usage:
    export VECTOR_DB=azure-ai-search
    export AZURE_SEARCH_ENDPOINT=https://<service>.search.windows.net
    export AZURE_SEARCH_ADMIN_KEY=<your-key>
"""

import json
import logging
import re
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchProfile,
)
from azure.search.documents.models import QueryType, VectorizedQuery
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)

log = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────
MAX_BATCH_SIZE = 1000  # Azure AI Search upload batch limit
MAX_SEARCH_SIZE = 1000  # maximum documents returned per page
INDEX_PREFIX = 'open-webui-'  # reset must never delete unrelated service indexes
VALID_SEARCH_TYPES = frozenset({'vector', 'fulltext', 'hybrid', 'semantic'})
SEMANTIC_CONFIG_NAME = 'default-semantic-config'

# ── shared-index names (used when NAMESPACE_MODE=True) ───────────
SHARED_KB_INDEX = f'{INDEX_PREFIX}knowledge'
SHARED_FILE_INDEX = f'{INDEX_PREFIX}files'
SHARED_MEMORY_INDEX = f'{INDEX_PREFIX}memory'

# ── UUID pattern for Collection→Namespace detection ──────────────
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


class AzureAISearchClient(VectorDBBase):
    """Azure AI Search implementation of VectorDBBase."""

    # ----------------------------------------------------------------
    # init
    # ----------------------------------------------------------------
    def __init__(self):
        import os

        self.endpoint = os.environ.get('AZURE_SEARCH_ENDPOINT', '')
        self.api_key = os.environ.get('AZURE_SEARCH_ADMIN_KEY', '')
        self.api_version = os.environ.get('AZURE_SEARCH_API_VERSION', '2024-07-01')

        if not self.endpoint:
            raise ValueError('AZURE_SEARCH_ENDPOINT is required')
        if not self.api_key:
            raise ValueError('AZURE_SEARCH_ADMIN_KEY is required')

        # ── search type ────────────────────────────────────────
        _raw = os.environ.get('AZURE_SEARCH_TYPE', 'hybrid').strip().lower()
        if _raw not in VALID_SEARCH_TYPES:
            raise ValueError(f"AZURE_SEARCH_TYPE must be one of {sorted(VALID_SEARCH_TYPES)}, got '{_raw}'")
        self.search_type: str = _raw

        _sem = os.environ.get('AZURE_ENABLE_SEMANTIC_SEARCH', 'false').strip().lower()
        self.enable_semantic_search: bool = _sem in ('true', '1', 'yes')

        # ── namespace mode (shared-index consolidation) ──────────
        _ns = os.environ.get('AZURE_SEARCH_NAMESPACE_MODE', 'false').strip().lower()
        self.namespace_mode: bool = _ns in ('true', '1', 'yes')

        log.info(
            '[AzureAISearch] init — type=%s semantic=%s namespace=%s',
            self.search_type,
            self.enable_semantic_search,
            self.namespace_mode,
        )

        self.credential = AzureKeyCredential(self.api_key)
        self._index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
            api_version=self.api_version,
        )

    # ----------------------------------------------------------------
    # helpers
    # ----------------------------------------------------------------
    def _get_search_client(self, index_name: str) -> SearchClient:
        return SearchClient(
            endpoint=self.endpoint,
            index_name=index_name,
            credential=self.credential,
            api_version=self.api_version,
        )

    def _dimension_from_items(self, items: list[Any]) -> int:
        if not items:
            return 384
        first = items[0]
        vec = first.get('vector') if isinstance(first, dict) else getattr(first, 'vector', None)
        return len(vec) if vec else 384

    # ── namespace resolution ────────────────────────────────────
    def _index_name(self, collection_name: str) -> str:
        """Map an Open WebUI collection to a valid, owned Azure index name."""
        normalized = re.sub(r'[^a-z0-9-]+', '-', collection_name.lower()).strip('-')
        return f'{INDEX_PREFIX}{normalized[:120]}'

    def _resolve_collection(self, collection_name: str) -> tuple[str, str | None]:
        """Map OWUI collection name → (index_name, odata_filter).

        When ``namespace_mode=True``, KB / file / memory collections are
        routed to shared indexes with a ``collection_key`` filter.

        Returns:
            (index_name, odata_filter_or_None)
        """
        if not self.namespace_mode:
            return self._index_name(collection_name), None

        if UUID_RE.match(collection_name):
            # Knowledge Base UUID
            return SHARED_KB_INDEX, f"collection_key eq 'kb:{collection_name}'"

        if collection_name.startswith('file-'):
            return SHARED_FILE_INDEX, f"collection_key eq '{collection_name}'"

        if collection_name.startswith('user-memory-'):
            return SHARED_MEMORY_INDEX, f"collection_key eq '{collection_name}'"

        # legacy / unknown — keep a dedicated index under our prefix
        return self._index_name(collection_name), None

    def _build_documents(self, items: list[Any], collection_name: str) -> list[dict[str, Any]]:
        """Convert items (dict or VectorItem) → Azure AI Search documents.

        OWUI may pass plain dicts with keys ``id``, ``text``, ``vector``,
        ``metadata``, NOT ``VectorItem`` objects.
        """
        index_name, ns_filter = self._resolve_collection(collection_name)
        is_namespaced = ns_filter is not None

        docs = []
        for item in items:
            # Support both dict and VectorItem access patterns
            def _get(key):
                return item.get(key) if isinstance(item, dict) else getattr(item, key, None)

            meta = _get('metadata') or {}
            doc = {
                'id': _get('id') or '',
                'text': _get('text') or '',
                'vector': _get('vector') or [],
                'metadata': json.dumps(meta) if isinstance(meta, dict) else str(meta),
            }
            if is_namespaced:
                if UUID_RE.match(collection_name):
                    doc['collection_key'] = f'kb:{collection_name}'
                else:
                    doc['collection_key'] = collection_name
            docs.append(doc)
        return docs

    def _match_metadata(self, metadata_str: str, filter_dict: dict) -> bool:
        if not filter_dict:
            return True
        try:
            meta = json.loads(metadata_str) if metadata_str else {}
        except (json.JSONDecodeError, TypeError):
            return False
        for key, value in filter_dict.items():
            if key == '*':
                continue
            if key not in meta:
                return False
            if meta[key] != value:
                return False
        return True

    # ── index creation ──────────────────────────────────────────
    def _index_has_field(self, index_name: str, field_name: str) -> bool:
        """Check if an index has a specific field in its schema."""
        try:
            idx = self._index_client.get_index(index_name)
            return any(f.name == field_name for f in idx.fields)
        except Exception:
            return False

    def _index_dimension(self, index_name: str) -> int:
        """Get vector dimension of an index, or 0 if unknown."""
        try:
            idx = self._index_client.get_index(index_name)
            for f in idx.fields:
                if f.vector_search_dimensions:
                    return f.vector_search_dimensions
            return 0
        except Exception:
            return 0

    def _make_fields(self, vector_dimension: int, include_collection_key: bool = False) -> list[SearchField]:
        """Build field list; optionally includes ``collection_key``."""
        fields: list[SearchField] = [
            SimpleField(
                name='id',
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SearchableField(name='text', type=SearchFieldDataType.String),
            SearchField(
                name='vector',
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=vector_dimension,
                vector_search_profile_name='default-profile',
            ),
            SimpleField(
                name='metadata',
                type=SearchFieldDataType.String,
                filterable=True,
            ),
        ]
        if include_collection_key:
            fields.append(
                SimpleField(
                    name='collection_key',
                    type=SearchFieldDataType.String,
                    filterable=True,
                )
            )
        return fields

    def _create_index_if_not_exists(
        self,
        index_name: str,
        vector_dimension: int = 384,
        include_collection_key: bool = False,
    ) -> None:
        """Create index if missing, or recreate if dimensions or schema mismatch."""
        if self._index_exists(index_name):
            mismatch = False
            if include_collection_key and not self._index_has_field(index_name, 'collection_key'):
                mismatch = True
            if not mismatch and self._index_dimension(index_name) != vector_dimension:
                mismatch = True
            if mismatch:
                log.info(
                    '[AzureAISearch] Index %s mismatch (dim or schema) — recreating',
                    index_name,
                )
                self._index_client.delete_index(index_name)
            else:
                return

        fields = self._make_fields(vector_dimension, include_collection_key)

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name='default-algorithm',
                    kind=VectorSearchAlgorithmKind.HNSW,
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name='default-profile',
                    algorithm_configuration_name='default-algorithm',
                )
            ],
        )

        semantic_search = None
        if self.enable_semantic_search:
            semantic_search = SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name=SEMANTIC_CONFIG_NAME,
                        prioritized_fields=SemanticPrioritizedFields(
                            content_fields=[SemanticField(field_name='text')],
                        ),
                    )
                ],
                default_configuration_name=SEMANTIC_CONFIG_NAME,
            )

        idx = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )
        self._index_client.create_index(idx)
        log.info(
            '[AzureAISearch] Created index: %s (dim=%d, namespace=%s)',
            index_name,
            vector_dimension,
            include_collection_key,
        )

    # ── search kwargs builder ────────────────────────────────────
    def _build_search_kwargs(  # noqa: C901
        self,
        search_text: str = '*',
        vectors: list[list[float | int]] | None = None,
        limit: int = 10,
        odata_filter: str | None = None,
    ) -> dict[str, Any]:
        """Compose ``SearchClient.search(**kwargs)`` dict."""
        effective_type = self.search_type
        # No text for vector-only search? Fall back to vector.
        # (hybrid_search passes real text, search() passes "*")
        if effective_type == 'fulltext' and search_text == '*':
            effective_type = 'vector'

        kwargs: dict[str, Any] = {'top': limit}
        if odata_filter:
            kwargs['filter'] = odata_filter

        match effective_type:
            case 'fulltext':
                kwargs['search_text'] = search_text
                kwargs['query_type'] = QueryType.SIMPLE
            case 'vector':
                kwargs['search_text'] = '*'
                if vectors:
                    kwargs['vector_queries'] = [
                        VectorizedQuery(vector=v, k_nearest_neighbors=limit, fields='vector') for v in vectors
                    ]
            case 'hybrid':
                kwargs['search_text'] = search_text if search_text else '*'
                kwargs['query_type'] = QueryType.SIMPLE
                if vectors:
                    kwargs['vector_queries'] = [
                        VectorizedQuery(vector=v, k_nearest_neighbors=limit, fields='vector') for v in vectors
                    ]
            case 'semantic':
                kwargs['search_text'] = search_text if search_text else '*'
                if self.enable_semantic_search:
                    kwargs['query_type'] = QueryType.SEMANTIC
                    kwargs['semantic_configuration_name'] = SEMANTIC_CONFIG_NAME
                else:
                    kwargs['query_type'] = QueryType.SIMPLE
                if vectors:
                    kwargs['vector_queries'] = [
                        VectorizedQuery(vector=v, k_nearest_neighbors=limit, fields='vector') for v in vectors
                    ]
            case _:
                kwargs['search_text'] = search_text if search_text else '*'
                if vectors:
                    kwargs['vector_queries'] = [
                        VectorizedQuery(vector=v, k_nearest_neighbors=limit, fields='vector') for v in vectors
                    ]
        return kwargs

    # ── result extraction ────────────────────────────────────────
    def _extract_search(
        self,
        results,
        metadata_filter: dict | None = None,
    ) -> SearchResult:
        ids: list[list[str]] = [[]]
        docs: list[list[str]] = [[]]
        meta: list[list[Any]] = [[]]
        dist: list[list[float]] = [[]]
        for doc in results:
            meta_str = doc.get('metadata', '{}')
            if metadata_filter and not self._match_metadata(meta_str, metadata_filter):
                continue
            ids[0].append(doc.get('id', ''))
            docs[0].append(doc.get('text', ''))
            meta[0].append(json.loads(meta_str) if meta_str else {})
            dist[0].append(doc.get('@search.score', 0.0))
        return SearchResult(
            ids=ids,
            documents=docs,
            metadatas=meta,
            distances=dist,
        )

    def _extract_get(self, results) -> GetResult:
        ids: list[list[str]] = [[]]
        docs: list[list[str]] = [[]]
        meta: list[list[Any]] = [[]]
        for doc in results:
            meta_str = doc.get('metadata', '{}')
            ids[0].append(doc.get('id', ''))
            docs[0].append(doc.get('text', ''))
            meta[0].append(json.loads(meta_str) if meta_str else {})
        return GetResult(
            ids=ids,
            documents=docs,
            metadatas=meta,
        )

    # ════════════════════════════════════════════════════════════
    # VectorDBBase interface
    # ════════════════════════════════════════════════════════════

    def has_collection(self, collection_name: str) -> bool:
        """Check if a collection (or its namespace-shared index) exists."""
        index_name, ns_filter = self._resolve_collection(collection_name)

        if ns_filter:
            # shared-index mode — check if any doc matches collection_key
            if not self._index_exists(index_name):
                return False
            client = self._get_search_client(index_name)
            try:
                results = list(
                    client.search(
                        search_text='*',
                        filter=ns_filter,
                        top=1,
                    )
                )
                return len(results) > 0
            except Exception:
                return False
        else:
            return self._index_exists(index_name)

    def _index_exists(self, index_name: str) -> bool:
        try:
            self._index_client.get_index(index_name)
            return True
        except Exception:
            return False

    def delete_collection(self, collection_name: str) -> None:
        index_name, ns_filter = self._resolve_collection(collection_name)

        if ns_filter:
            # shared mode — delete matching docs only
            if not self._index_exists(index_name):
                return
            self._delete_by_filter(index_name, ns_filter)
        else:
            try:
                self._index_client.delete_index(index_name)
            except Exception:
                pass

    def _delete_by_filter(self, index_name: str, odata_filter: str) -> None:
        """Delete documents matching an OData filter (used in namespace mode)."""
        client = self._get_search_client(index_name)
        try:
            # Azure doesn't have "delete by filter" — we query then delete
            results = list(
                client.search(
                    search_text='*',
                    filter=odata_filter,
                    top=MAX_SEARCH_SIZE,
                    select=['id'],
                )
            )
            if results:
                ids = [{'id': d['id']} for d in results]
                client.delete_documents(ids)
        except Exception as e:
            log.warning('[AzureAISearch] _delete_by_filter error: %s', e)

    def insert(self, collection_name: str, items: list[VectorItem]) -> None:
        if not items:
            return

        index_name, _ = self._resolve_collection(collection_name)
        dim = self._dimension_from_items(items)
        include_ck = self.namespace_mode and collection_name != index_name

        newly_created = not self._index_exists(index_name)
        self._create_index_if_not_exists(index_name, dim, include_collection_key=include_ck)

        if newly_created and include_ck:
            # Azure AI Search needs time for the new index schema to propagate
            # before documents with new fields can be uploaded.
            import time as _time

            _time.sleep(3.0)

        docs = self._build_documents(items, collection_name)
        client = self._get_search_client(index_name)
        for i in range(0, len(docs), MAX_BATCH_SIZE):
            client.merge_or_upload_documents(docs[i : i + MAX_BATCH_SIZE])

    def upsert(self, collection_name: str, items: list[VectorItem]) -> None:
        self.insert(collection_name, items)

    # ── search ──────────────────────────────────────────────────
    def search(
        self,
        collection_name: str,
        vectors: list[list[float | int]],
        filter: dict | None = None,
        limit: int = 10,
    ) -> SearchResult | None:
        index_name, ns_filter = self._resolve_collection(collection_name)
        if ns_filter and not self._index_exists(index_name):
            return SearchResult(ids=[[]], documents=[[]], metadatas=[[]], distances=[[]])
        if not ns_filter and not self.has_collection(index_name):
            return SearchResult(ids=[[]], documents=[[]], metadatas=[[]], distances=[[]])

        client = self._get_search_client(index_name)

        all_ids = []
        all_docs = []
        all_meta = []
        all_dist = []
        for v in vectors:
            try:
                kwargs = self._build_search_kwargs(
                    search_text='*',
                    vectors=[v],
                    limit=limit,
                    odata_filter=ns_filter,
                )
                results = client.search(**kwargs)
                q_ids = []
                q_docs = []
                q_meta = []
                q_dist = []
                for doc in results:
                    meta_str = doc.get('metadata', '{}')
                    if filter and not self._match_metadata(meta_str, filter):
                        continue
                    q_ids.append(doc.get('id', ''))
                    q_docs.append(doc.get('text', ''))
                    q_meta.append(json.loads(meta_str) if meta_str else {})
                    q_dist.append(doc.get('@search.score', 0.0))
                all_ids.append(q_ids)
                all_docs.append(q_docs)
                all_meta.append(q_meta)
                all_dist.append(q_dist)
            except Exception as e:
                log.error('[AzureAISearch] search error: %s', e)
                all_ids.append([])
                all_docs.append([])
                all_meta.append([])
                all_dist.append([])

        return SearchResult(
            ids=all_ids,
            documents=all_docs,
            metadatas=all_meta,
            distances=all_dist,
        )

    def hybrid_search(
        self,
        collection_name: str,
        query: str,
        vectors: list[list[float | int]],
        filter: dict | None = None,
        limit: int = 10,
        hybrid_bm25_weight: float = 0.5,
    ) -> SearchResult | None:
        """Azure-native hybrid: combines keyword (full-text) + vector."""
        index_name, ns_filter = self._resolve_collection(collection_name)
        if ns_filter and not self._index_exists(index_name):
            return SearchResult(ids=[[]], documents=[[]], metadatas=[[]], distances=[[]])
        if not ns_filter and not self.has_collection(index_name):
            return SearchResult(ids=[[]], documents=[[]], metadatas=[[]], distances=[[]])

        client = self._get_search_client(index_name)

        all_ids = []
        all_docs = []
        all_meta = []
        all_dist = []
        for v in vectors:
            try:
                kwargs = self._build_search_kwargs(
                    search_text=query,
                    vectors=[v],
                    limit=limit,
                    odata_filter=ns_filter,
                )
                results = client.search(**kwargs)
                q_ids = []
                q_docs = []
                q_meta = []
                q_dist = []
                for doc in results:
                    meta_str = doc.get('metadata', '{}')
                    if filter and not self._match_metadata(meta_str, filter):
                        continue
                    q_ids.append(doc.get('id', ''))
                    q_docs.append(doc.get('text', ''))
                    q_meta.append(json.loads(meta_str) if meta_str else {})
                    q_dist.append(doc.get('@search.score', 0.0))
                all_ids.append(q_ids)
                all_docs.append(q_docs)
                all_meta.append(q_meta)
                all_dist.append(q_dist)
            except Exception as e:
                log.error('[AzureAISearch] hybrid_search error: %s', e)
                all_ids.append([])
                all_docs.append([])
                all_meta.append([])
                all_dist.append([])

        return SearchResult(
            ids=all_ids,
            documents=all_docs,
            metadatas=all_meta,
            distances=all_dist,
        )

    def query(
        self,
        collection_name: str,
        filter: dict,
        limit: int | None = None,
    ) -> GetResult | None:
        index_name, ns_filter = self._resolve_collection(collection_name)
        # OWUI expects result.ids[0] to work; return empty shell, not None
        if ns_filter and not self._index_exists(index_name):
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])
        if not ns_filter and not self.has_collection(index_name):
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        client = self._get_search_client(index_name)
        effective_limit = limit or MAX_SEARCH_SIZE

        try:
            results = (
                client.search(
                    search_text='*',
                    top=effective_limit,
                    filter=ns_filter,
                )
                if ns_filter
                else client.search(search_text='*', top=effective_limit)
            )

            ids = [[]]
            docs = [[]]
            meta = [[]]
            for doc in results:
                meta_str = doc.get('metadata', '{}')
                if not self._match_metadata(meta_str, filter):
                    continue
                if len(ids[0]) >= effective_limit:
                    break
                ids[0].append(doc.get('id', ''))
                docs[0].append(doc.get('text', ''))
                meta[0].append(json.loads(meta_str) if meta_str else {})
            return GetResult(
                ids=ids,
                documents=docs,
                metadatas=meta,
            )
        except Exception as e:
            log.error('[AzureAISearch] query error: %s', e)
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

    def get(self, collection_name: str) -> GetResult | None:
        index_name, ns_filter = self._resolve_collection(collection_name)
        if ns_filter and not self._index_exists(index_name):
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])
        if not ns_filter and not self.has_collection(index_name):
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

        client = self._get_search_client(index_name)
        try:
            kwargs = {'search_text': '*', 'top': MAX_SEARCH_SIZE}
            if ns_filter:
                kwargs['filter'] = ns_filter
            results = client.search(**kwargs)
            return self._extract_get(results)
        except Exception as e:
            log.error('[AzureAISearch] get error: %s', e)
            return GetResult(ids=[[]], documents=[[]], metadatas=[[]])

    def delete(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        filter: dict | None = None,
    ) -> None:
        index_name, ns_filter = self._resolve_collection(collection_name)
        if ns_filter and not self._index_exists(index_name):
            return
        if not ns_filter and not self.has_collection(index_name):
            return

        client = self._get_search_client(index_name)

        if ids:
            client.delete_documents([{'id': id_} for id_ in ids])
        elif filter:
            result = self.query(collection_name, filter, limit=MAX_SEARCH_SIZE)
            if result and result.ids and result.ids[0]:
                client.delete_documents([{'id': id_} for id_ in result.ids[0]])

    def reset(self) -> None:
        try:
            for index in self._index_client.list_indexes():
                if not index.name.startswith(INDEX_PREFIX):
                    continue
                log.info('[AzureAISearch] Deleting index: %s', index.name)
                self._index_client.delete_index(index.name)
        except Exception as e:
            log.error('[AzureAISearch] reset error: %s', e)

"""
NOTE: This vector database integration is community-supported and maintained on a best-effort basis.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from open_webui.config import (
    MILVUS_COLLECTION_PREFIX,
    MILVUS_DB,
    MILVUS_HNSW_EFCONSTRUCTION,
    MILVUS_HNSW_M,
    MILVUS_INDEX_TYPE,
    MILVUS_IVF_FLAT_NLIST,
    MILVUS_METRIC_TYPE,
    MILVUS_TOKEN,
    MILVUS_URI,
)
from open_webui.env import ENABLE_DB_MIGRATIONS
from open_webui.retrieval.vector.dbs.milvus import (
    BM25_COLLECTION_SUFFIX,
    BM25_STAGING_SUFFIX,
    _backfill_bm25_collection,
    _metadata_exprs,
    _update_bm25_collection,
)
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from open_webui.retrieval.vector.utils import merge_hybrid_search_results, process_metadata
from pymilvus import DataType, Function, FunctionType
from pymilvus import MilvusClient as Client
from pymilvus.exceptions import MilvusException

log = logging.getLogger(__name__)

RESOURCE_ID_FIELD = 'resource_id'
# Milvus VARCHAR hard cap for the `text` field (see _create_shared_collection).
# Chunks longer than this are truncated before insert so one oversized chunk
# can't fail the whole batch (and leave the file with zero embeddings).
MILVUS_TEXT_MAX_LENGTH = 65535

# Milvus expressions are SQL-like strings with no parameterized-query API;
# values get interpolated into single-quoted literals. Reject anything that
# can't be a legitimate Open WebUI collection name.
_SAFE_RESOURCE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,255}$')
_SAFE_METADATA_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')


def _validate_resource_id(resource_id: str) -> str:
    if not isinstance(resource_id, str) or not _SAFE_RESOURCE_ID_RE.match(resource_id):
        raise ValueError(f'Invalid Milvus resource_id (collection name): {resource_id!r}')
    return resource_id


def _validate_metadata_key(key: str) -> str:
    if not isinstance(key, str) or not _SAFE_METADATA_KEY_RE.match(key):
        raise ValueError(f'Invalid Milvus metadata filter key: {key!r}')
    return key


def _escape_milvus_string(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f'Expected str for Milvus expression value, got {type(value).__name__}')
    return value.replace('\\', '\\\\').replace("'", "\\'")


class MilvusClient(VectorDBBase):
    def __init__(self):
        # Milvus collection names can only contain numbers, letters, and underscores.
        self.collection_prefix = MILVUS_COLLECTION_PREFIX.replace('-', '_')
        self.client = Client(uri=MILVUS_URI, token=MILVUS_TOKEN, db_name=MILVUS_DB)

        # Main collection types for multi-tenancy
        self.MEMORY_COLLECTION = f'{self.collection_prefix}_memories'
        self.KNOWLEDGE_COLLECTION = f'{self.collection_prefix}_knowledge'
        self.FILE_COLLECTION = f'{self.collection_prefix}_files'
        self.WEB_SEARCH_COLLECTION = f'{self.collection_prefix}_web_search'
        self.HASH_BASED_COLLECTION = f'{self.collection_prefix}_hash_based'
        self.shared_collections = [
            self.MEMORY_COLLECTION,
            self.KNOWLEDGE_COLLECTION,
            self.FILE_COLLECTION,
            self.WEB_SEARCH_COLLECTION,
            self.HASH_BASED_COLLECTION,
        ]
        if ENABLE_DB_MIGRATIONS:
            self._backfill_bm25_collections()

    def _get_collection_and_resource_id(self, collection_name: str) -> Tuple[str, str]:
        """
        Maps the traditional collection name to multi-tenant collection and resource ID.

        WARNING: This mapping relies on current Open WebUI naming conventions for
        collection names. If Open WebUI changes how it generates collection names
        (e.g., "user-memory-" prefix, "file-" prefix, web search patterns, or hash
        formats), this mapping will break and route data to incorrect collections.
        POTENTIALLY CAUSING HUGE DATA CORRUPTION, DATA CONSISTENCY ISSUES AND INCORRECT
        DATA MAPPING INSIDE THE DATABASE.
        """
        resource_id = collection_name

        if collection_name.startswith('user-memory-'):
            return self.MEMORY_COLLECTION, resource_id
        elif collection_name.startswith('file-'):
            return self.FILE_COLLECTION, resource_id
        elif collection_name.startswith('web-search-'):
            return self.WEB_SEARCH_COLLECTION, resource_id
        elif len(collection_name) == 63 and all(c in '0123456789abcdef' for c in collection_name):
            return self.HASH_BASED_COLLECTION, resource_id
        else:
            return self.KNOWLEDGE_COLLECTION, resource_id

    def _create_shared_collection(self, mt_collection_name: str, dimension: int):
        schema = self.client.create_schema(auto_id=False, description='Shared collection for multi-tenancy')
        schema.add_field(field_name='id', datatype=DataType.VARCHAR, is_primary=True, max_length=36)
        schema.add_field(field_name='vector', datatype=DataType.FLOAT_VECTOR, dim=dimension)
        schema.add_field(field_name='text', datatype=DataType.VARCHAR, max_length=MILVUS_TEXT_MAX_LENGTH)
        schema.add_field(field_name='metadata', datatype=DataType.JSON)
        schema.add_field(field_name=RESOURCE_ID_FIELD, datatype=DataType.VARCHAR, max_length=255)

        index_build_params = {}
        if MILVUS_INDEX_TYPE == 'HNSW':
            index_build_params = {
                'M': MILVUS_HNSW_M,
                'efConstruction': MILVUS_HNSW_EFCONSTRUCTION,
            }
        elif MILVUS_INDEX_TYPE == 'IVF_FLAT':
            index_build_params = {'nlist': MILVUS_IVF_FLAT_NLIST}

        vector_index = self.client.prepare_index_params(
            field_name='vector',
            index_type=MILVUS_INDEX_TYPE,
            metric_type=MILVUS_METRIC_TYPE,
            params=index_build_params,
        )

        self.client.create_collection(collection_name=mt_collection_name, schema=schema)
        self.client.create_index(collection_name=mt_collection_name, index_params=vector_index)
        self._create_resource_id_index(mt_collection_name)
        log.info('Created shared collection: %s', mt_collection_name)

    def _create_resource_id_index(self, mt_collection_name: str):
        try:
            # A Milvus server auto-selects the scalar index type from a parameterless call.
            self.client.create_index(
                collection_name=mt_collection_name,
                index_params=self.client.prepare_index_params(field_name=RESOURCE_ID_FIELD),
            )
        except MilvusException:
            try:
                self.client.create_index(
                    collection_name=mt_collection_name,
                    index_params=self.client.prepare_index_params(field_name=RESOURCE_ID_FIELD, index_type='INVERTED'),
                )
            except MilvusException as e:
                # The index only accelerates resource_id filters; never fail
                # collection creation over it.
                log.warning(f'Could not create {RESOURCE_ID_FIELD} index on {mt_collection_name}: {e}')

    def _create_bm25_collection(self, bm25_collection: str):
        schema = self.client.create_schema(auto_id=False)
        schema.add_field(field_name='id', datatype=DataType.VARCHAR, is_primary=True, max_length=36)
        schema.add_field(
            field_name='text', datatype=DataType.VARCHAR, max_length=MILVUS_TEXT_MAX_LENGTH, enable_analyzer=True
        )
        schema.add_field(field_name='sparse', datatype=DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(field_name='metadata', datatype=DataType.JSON)
        schema.add_field(field_name=RESOURCE_ID_FIELD, datatype=DataType.VARCHAR, max_length=255)
        schema.add_function(
            Function(
                name='text_bm25',
                function_type=FunctionType.BM25,
                input_field_names=['text'],
                output_field_names=['sparse'],
            )
        )
        self.client.create_collection(collection_name=bm25_collection, schema=schema)
        try:
            self.client.create_index(
                collection_name=bm25_collection,
                index_params=self.client.prepare_index_params(
                    field_name='sparse', index_type='SPARSE_INVERTED_INDEX', metric_type='BM25'
                ),
            )
        except MilvusException:
            self.client.drop_collection(bm25_collection)
            raise
        self._create_resource_id_index(bm25_collection)

    def _backfill_bm25_collections(self):
        for mt_collection in self.shared_collections:
            if self.client.has_collection(mt_collection) and not self.client.has_collection(
                f'{mt_collection}{BM25_COLLECTION_SUFFIX}'
            ):
                _backfill_bm25_collection(
                    self.client,
                    mt_collection,
                    self._create_bm25_collection,
                    ['id', 'text', 'metadata', RESOURCE_ID_FIELD],
                    lambda rows: rows,
                )

    def _ensure_collection(self, mt_collection_name: str, dimension: int):
        if not self.client.has_collection(mt_collection_name):
            self._create_shared_collection(mt_collection_name, dimension)
            try:
                self._create_bm25_collection(f'{mt_collection_name}{BM25_COLLECTION_SUFFIX}')
            except MilvusException as e:
                log.warning('Could not create BM25 collection for %s (needs Milvus 2.5+): %s', mt_collection_name, e)

    def has_collection(self, collection_name: str) -> bool:
        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        if not self.client.has_collection(mt_collection):
            return False

        self.client.load_collection(mt_collection)
        res = self.client.query(
            collection_name=mt_collection,
            filter=f"{RESOURCE_ID_FIELD} == '{resource_id}'",
            output_fields=['id'],
            limit=1,
        )
        return len(res) > 0

    def upsert(self, collection_name: str, items: List[VectorItem]):
        if not items:
            return
        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        dimension = len(items[0]['vector'])
        self._ensure_collection(mt_collection, dimension)

        entities = []
        for item in items:
            text = item['text'] or ''
            if len(text) > MILVUS_TEXT_MAX_LENGTH:
                log.warning(
                    f'Milvus: truncating text id={item["id"]} '
                    f'{len(text)}->{MILVUS_TEXT_MAX_LENGTH} chars '
                    f'(collection={mt_collection}, resource_id={resource_id})'
                )
                text = text[:MILVUS_TEXT_MAX_LENGTH]
            entities.append(
                {
                    'id': item['id'],
                    'vector': item['vector'],
                    'text': text,
                    'metadata': process_metadata(item['metadata']),
                    RESOURCE_ID_FIELD: resource_id,
                }
            )

        try:
            self.client.insert(collection_name=mt_collection, data=entities)
            _update_bm25_collection(
                self.client,
                f'{mt_collection}{BM25_COLLECTION_SUFFIX}',
                'insert',
                data=[{key: value for key, value in entity.items() if key != 'vector'} for entity in entities],
            )
        except MilvusException as e:
            log.error(
                f'Milvus insert failed (collection={mt_collection}, '
                f'resource_id={resource_id}, items={len(entities)}): {e}'
            )
            raise

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        filter: Optional[Dict] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        if not vectors:
            return None

        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        if not self.client.has_collection(mt_collection):
            return None

        self.client.load_collection(mt_collection)

        expr = [f"{RESOURCE_ID_FIELD} == '{resource_id}'", *_metadata_exprs(filter)]
        results = self.client.search(
            collection_name=mt_collection,
            data=vectors,
            anns_field='vector',
            search_params={'metric_type': MILVUS_METRIC_TYPE, 'params': {}},
            limit=limit,
            filter=' and '.join(expr),
            output_fields=['id', 'text', 'metadata'],
        )

        ids, documents, metadatas, distances = [], [], [], []
        for hits in results:
            batch_ids, batch_docs, batch_metadatas, batch_dists = [], [], [], []
            for hit in hits:
                entity = hit.get('entity', {})
                batch_ids.append(entity.get('id'))
                batch_docs.append(entity.get('text'))
                batch_metadatas.append(entity.get('metadata'))
                batch_dists.append(hit.get('distance'))
            ids.append(batch_ids)
            documents.append(batch_docs)
            metadatas.append(batch_metadatas)
            distances.append(batch_dists)

        return SearchResult(ids=ids, documents=documents, metadatas=metadatas, distances=distances)

    def hybrid_search(
        self,
        collection_name: str,
        query: str,
        vectors: List[List[float]],
        filter: Optional[Dict] = None,
        limit: int = 10,
        hybrid_bm25_weight: float = 0.5,
    ) -> Optional[SearchResult]:
        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        bm25_collection = f'{mt_collection}{BM25_COLLECTION_SUFFIX}'
        if not self.client.has_collection(bm25_collection):
            return None

        vector_result = None
        if hybrid_bm25_weight < 1 and vectors:
            vector_result = self.search(collection_name=collection_name, vectors=vectors, filter=filter, limit=limit)

        fts_results = []
        if hybrid_bm25_weight > 0 and query.strip():
            self.client.load_collection(mt_collection)
            self.client.load_collection(bm25_collection)
            expr = [f"{RESOURCE_ID_FIELD} == '{resource_id}'", *_metadata_exprs(filter)]
            results = self.client.search(
                collection_name=bm25_collection,
                data=[query],
                anns_field='sparse',
                limit=limit,
                filter=' and '.join(expr),
            )
            id_list_str = ', '.join([f"'{_escape_milvus_string(str(hit['id']))}'" for hit in results[0]])
            items = self.client.query(
                collection_name=mt_collection,
                filter=' and '.join([*expr, f'id in [{id_list_str}]']),
                output_fields=['id', 'text', 'metadata'],
            )
            items_by_id = {item['id']: item for item in items}
            fts_results = [
                {
                    'id': hit['id'],
                    'text': items_by_id[hit['id']]['text'],
                    'vmetadata': items_by_id[hit['id']]['metadata'],
                }
                for hit in results[0]
                if hit['id'] in items_by_id
            ]

        return merge_hybrid_search_results(
            vector_result=vector_result,
            fts_results=fts_results,
            num_queries=len(vectors) or 1,
            limit=limit,
            hybrid_bm25_weight=hybrid_bm25_weight,
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ):
        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        if not self.client.has_collection(mt_collection):
            return

        expr = [f"{RESOURCE_ID_FIELD} == '{resource_id}'"]
        if ids:
            # Milvus expects a string list for 'in' operator
            id_list_str = ', '.join([f"'{_escape_milvus_string(str(id_val))}'" for id_val in ids])
            expr.append(f'id in [{id_list_str}]')

        if filter:
            for key, value in filter.items():
                _validate_metadata_key(key)
                expr.append(f"metadata['{key}'] == '{_escape_milvus_string(str(value))}'")

        self.client.delete(collection_name=mt_collection, filter=' and '.join(expr))
        _update_bm25_collection(
            self.client, f'{mt_collection}{BM25_COLLECTION_SUFFIX}', 'delete', filter=' and '.join(expr)
        )

    def reset(self):
        for collection_name in self.shared_collections:
            if self.client.has_collection(collection_name):
                self.client.drop_collection(collection_name)
            self.client.drop_collection(f'{collection_name}{BM25_COLLECTION_SUFFIX}')
            self.client.drop_collection(f'{collection_name}{BM25_STAGING_SUFFIX}')

    def delete_collection(self, collection_name: str):
        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        if not self.client.has_collection(mt_collection):
            return

        self.client.delete(collection_name=mt_collection, filter=f"{RESOURCE_ID_FIELD} == '{resource_id}'")
        _update_bm25_collection(
            self.client,
            f'{mt_collection}{BM25_COLLECTION_SUFFIX}',
            'delete',
            filter=f"{RESOURCE_ID_FIELD} == '{resource_id}'",
        )

    def query(self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None) -> Optional[GetResult]:
        mt_collection, resource_id = self._get_collection_and_resource_id(collection_name)
        _validate_resource_id(resource_id)
        if not self.client.has_collection(mt_collection):
            return None

        self.client.load_collection(mt_collection)

        expr = [f"{RESOURCE_ID_FIELD} == '{resource_id}'"]
        if filter:
            for key, value in filter.items():
                _validate_metadata_key(key)
                if isinstance(value, str):
                    expr.append(f"metadata['{key}'] == '{_escape_milvus_string(value)}'")
                elif isinstance(value, bool):
                    expr.append(f"metadata['{key}'] == {str(value).lower()}")
                elif isinstance(value, (int, float)):
                    expr.append(f"metadata['{key}'] == {value}")
                else:
                    raise TypeError(f'Unsupported Milvus filter value type for key {key!r}: {type(value).__name__}')

        iterator = self.client.query_iterator(
            collection_name=mt_collection,
            filter=' and '.join(expr),
            output_fields=['id', 'text', 'metadata'],
            limit=limit if limit else -1,
        )

        all_results = []
        while True:
            batch = iterator.next()
            if not batch:
                iterator.close()
                break
            all_results.extend(batch)

        ids = [res['id'] for res in all_results]
        documents = [res['text'] for res in all_results]
        metadatas = [res['metadata'] for res in all_results]

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def get(self, collection_name: str) -> Optional[GetResult]:
        return self.query(collection_name, filter={}, limit=None)

    def insert(self, collection_name: str, items: List[VectorItem]):
        return self.upsert(collection_name, items)

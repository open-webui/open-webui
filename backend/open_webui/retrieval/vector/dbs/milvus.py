"""
NOTE: This vector database integration is community-supported and maintained on a best-effort basis.
"""

import logging
import re
from typing import Any, Optional

from open_webui.config import (
    MILVUS_DB,
    MILVUS_DISKANN_MAX_DEGREE,
    MILVUS_DISKANN_SEARCH_LIST_SIZE,
    MILVUS_HNSW_EFCONSTRUCTION,
    MILVUS_HNSW_M,
    MILVUS_INDEX_TYPE,
    MILVUS_IVF_FLAT_NLIST,
    MILVUS_METRIC_TYPE,
    MILVUS_TOKEN,
    MILVUS_URI,
)
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from open_webui.retrieval.vector.utils import iter_filter_conditions, process_metadata
from open_webui.utils.json_codec import JSONCodec
from pymilvus import DataType
from pymilvus import MilvusClient as Client
from pymilvus.exceptions import MilvusException

log = logging.getLogger(__name__)

# Milvus caps stored text length (here the chunk lives under the JSON `data`
# field). Clamp long chunks before insert so one oversized chunk can't fail the
# whole batch and leave the file with zero embeddings.
MILVUS_TEXT_MAX_LENGTH = 65535
_SAFE_METADATA_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')


def _escape_milvus_string(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f'Expected str, got {type(value).__name__}')
    return value.replace('\\', '\\\\').replace("'", "\\'")


def _milvus_literal(value: Any) -> str:
    if isinstance(value, str):
        return f"'{_escape_milvus_string(value)}'"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    raise TypeError(f'Unsupported Milvus filter value type: {type(value).__name__}')


def _metadata_exprs(filter: Optional[dict]) -> list[str]:
    exprs = []
    for key, op, value in iter_filter_conditions(filter):
        if not isinstance(key, str) or not _SAFE_METADATA_KEY_RE.fullmatch(key):
            raise ValueError(f'Invalid Milvus metadata filter key: {key!r}')
        if op == '$in':
            items = [f"metadata['{key}'] == {_milvus_literal(item)}" for item in value]
            exprs.append(f'({" or ".join(items)})' if items else 'false')
        else:
            exprs.append(f"metadata['{key}'] == {_milvus_literal(value)}")
    return exprs


class MilvusClient(VectorDBBase):
    def __init__(self):
        self.collection_prefix = 'open_webui'
        if MILVUS_TOKEN is None:
            self.client = Client(uri=MILVUS_URI, db_name=MILVUS_DB)
        else:
            self.client = Client(uri=MILVUS_URI, db_name=MILVUS_DB, token=MILVUS_TOKEN)

    def _result_to_get_result(self, result) -> GetResult:
        ids = []
        documents = []
        metadatas = []
        for match in result:
            _ids = []
            _documents = []
            _metadatas = []
            for item in match:
                _ids.append(item.get('id'))
                _documents.append(item.get('data', {}).get('text'))
                _metadatas.append(item.get('metadata'))
            ids.append(_ids)
            documents.append(_documents)
            metadatas.append(_metadatas)
        return GetResult(
            **{
                'ids': ids,
                'documents': documents,
                'metadatas': metadatas,
            }
        )

    def _result_to_search_result(self, result) -> SearchResult:
        ids = []
        distances = []
        documents = []
        metadatas = []
        for match in result:
            _ids = []
            _distances = []
            _documents = []
            _metadatas = []
            for item in match:
                _ids.append(item.get('id'))
                # normalize milvus score from [-1, 1] to [0, 1] range
                # https://milvus.io/docs/de/metric.md
                _dist = (item.get('distance') + 1.0) / 2.0
                _distances.append(_dist)
                _documents.append(item.get('entity', {}).get('data', {}).get('text'))
                _metadatas.append(item.get('entity', {}).get('metadata'))
            ids.append(_ids)
            distances.append(_distances)
            documents.append(_documents)
            metadatas.append(_metadatas)
        return SearchResult(
            **{
                'ids': ids,
                'distances': distances,
                'documents': documents,
                'metadatas': metadatas,
            }
        )

    def _create_collection(self, collection_name: str, dimension: int):
        schema = self.client.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )
        schema.add_field(
            field_name='id',
            datatype=DataType.VARCHAR,
            is_primary=True,
            max_length=65535,
        )
        schema.add_field(
            field_name='vector',
            datatype=DataType.FLOAT_VECTOR,
            dim=dimension,
            description='vector',
        )
        schema.add_field(field_name='data', datatype=DataType.JSON, description='data')
        schema.add_field(field_name='metadata', datatype=DataType.JSON, description='metadata')

        index_params = self.client.prepare_index_params()

        # Use configurations from config.py
        index_type = MILVUS_INDEX_TYPE.upper()
        metric_type = MILVUS_METRIC_TYPE.upper()

        log.info('Using Milvus index type: %s, metric type: %s', index_type, metric_type)

        index_creation_params = {}
        if index_type == 'HNSW':
            index_creation_params = {
                'M': MILVUS_HNSW_M,
                'efConstruction': MILVUS_HNSW_EFCONSTRUCTION,
            }
            log.info('HNSW params: %s', index_creation_params)
        elif index_type == 'IVF_FLAT':
            index_creation_params = {'nlist': MILVUS_IVF_FLAT_NLIST}
            log.info('IVF_FLAT params: %s', index_creation_params)
        elif index_type == 'DISKANN':
            index_creation_params = {
                'max_degree': MILVUS_DISKANN_MAX_DEGREE,
                'search_list_size': MILVUS_DISKANN_SEARCH_LIST_SIZE,
            }
            log.info('DISKANN params: %s', index_creation_params)
        elif index_type in ['FLAT', 'AUTOINDEX']:
            log.info('Using %s index with no specific build-time params.', index_type)
        else:
            log.warning(
                f"Unsupported MILVUS_INDEX_TYPE: '{index_type}'. "
                f'Supported types: HNSW, IVF_FLAT, DISKANN, FLAT, AUTOINDEX. '
                f'Milvus will use its default for the collection if this type is not directly supported for index creation.'
            )
            # For unsupported types, pass the type directly to Milvus; it might handle it or use a default.
            # If Milvus errors out, the user needs to correct the MILVUS_INDEX_TYPE env var.

        index_params.add_index(
            field_name='vector',
            index_type=index_type,
            metric_type=metric_type,
            params=index_creation_params,
        )

        self.client.create_collection(
            collection_name=f'{self.collection_prefix}_{collection_name}',
            schema=schema,
            index_params=index_params,
        )
        log.info(
            "Successfully created collection '%s_%s' with index type '%s' and metric '%s'.",
            self.collection_prefix,
            collection_name,
            index_type,
            metric_type,
        )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collection_name = collection_name.replace('-', '_')
        return self.client.has_collection(collection_name=f'{self.collection_prefix}_{collection_name}')

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        collection_name = collection_name.replace('-', '_')
        return self.client.drop_collection(collection_name=f'{self.collection_prefix}_{collection_name}')

    def search(
        self,
        collection_name: str,
        vectors: list[list[float | int]],
        filter: Optional[dict] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        collection_name = collection_name.replace('-', '_')
        kwargs = {}
        if filter:
            kwargs['filter'] = ' and '.join(_metadata_exprs(filter))
        # For some index types like IVF_FLAT, search params like nprobe can be set.
        # Example: search_params = {"nprobe": 10} if using IVF_FLAT
        # For simplicity, not adding configurable search_params here, but could be extended.
        result = self.client.search(
            collection_name=f'{self.collection_prefix}_{collection_name}',
            data=vectors,
            limit=limit,
            output_fields=['data', 'metadata'],
            **kwargs,
            # search_params=search_params # Potentially add later if needed
        )
        return self._result_to_search_result(result)

    def query(self, collection_name: str, filter: dict, limit: int = -1):
        collection_name = collection_name.replace('-', '_')
        if not self.has_collection(collection_name):
            log.warning(f'Query attempted on non-existent collection: {self.collection_prefix}_{collection_name}')
            return None

        filter_expressions = []
        for key, value in filter.items():
            if isinstance(value, str):
                filter_expressions.append(f'metadata["{key}"] == "{value}"')
            else:
                filter_expressions.append(f'metadata["{key}"] == {value}')

        filter_string = ' && '.join(filter_expressions)

        self.client.load_collection(collection_name=f'{self.collection_prefix}_{collection_name}')

        try:
            log.info(
                "Querying collection %s_%s with filter: '%s', limit: %s",
                self.collection_prefix,
                collection_name,
                filter_string,
                limit,
            )

            iterator = self.client.query_iterator(
                collection_name=f'{self.collection_prefix}_{collection_name}',
                filter=filter_string,
                output_fields=[
                    'id',
                    'data',
                    'metadata',
                ],
                limit=limit if limit > 0 else -1,
            )

            all_results = []
            while True:
                batch = iterator.next()
                if not batch:
                    iterator.close()
                    break
                all_results.extend(batch)

            log.debug('Total results from query: %s', len(all_results))
            return self._result_to_get_result([all_results] if all_results else [[]])

        except Exception as e:
            log.exception(
                f"Error querying collection {self.collection_prefix}_{collection_name} with filter '{filter_string}' and limit {limit}: {e}"
            )
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection. This can be very resource-intensive for large collections.
        collection_name = collection_name.replace('-', '_')
        log.warning(
            f"Fetching ALL items from collection '{self.collection_prefix}_{collection_name}'. This might be slow for large collections."
        )
        # Using query with a trivial filter to get all items.
        # This will use the paginated query logic.
        return self.query(collection_name=collection_name, filter={}, limit=-1)

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection_name = collection_name.replace('-', '_')
        if not self.client.has_collection(collection_name=f'{self.collection_prefix}_{collection_name}'):
            log.info('Collection %s_%s does not exist. Creating now.', self.collection_prefix, collection_name)
            if not items:
                log.error(
                    f'Cannot create collection {self.collection_prefix}_{collection_name} without items to determine dimension.'
                )
                raise ValueError('Cannot create Milvus collection without items to determine vector dimension.')
            self._create_collection(collection_name=collection_name, dimension=len(items[0]['vector']))

        log.info('Inserting %s items into collection %s_%s.', len(items), self.collection_prefix, collection_name)
        data = []
        for item in items:
            text = item['text'] or ''
            if len(text) > MILVUS_TEXT_MAX_LENGTH:
                log.warning(f'Milvus: truncating text id={item["id"]} {len(text)}->{MILVUS_TEXT_MAX_LENGTH} chars')
                text = text[:MILVUS_TEXT_MAX_LENGTH]
            data.append(
                {
                    'id': item['id'],
                    'vector': item['vector'],
                    'data': {'text': text},
                    'metadata': process_metadata(item['metadata']),
                }
            )
        try:
            return self.client.insert(
                collection_name=f'{self.collection_prefix}_{collection_name}',
                data=data,
            )
        except MilvusException as e:
            log.error(f'Milvus insert failed for {self.collection_prefix}_{collection_name} ({len(items)} items): {e}')
            raise

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        collection_name = collection_name.replace('-', '_')
        if not self.client.has_collection(collection_name=f'{self.collection_prefix}_{collection_name}'):
            log.info(
                'Collection %s_%s does not exist for upsert. Creating now.', self.collection_prefix, collection_name
            )
            if not items:
                log.error(
                    f'Cannot create collection {self.collection_prefix}_{collection_name} for upsert without items to determine dimension.'
                )
                raise ValueError(
                    'Cannot create Milvus collection for upsert without items to determine vector dimension.'
                )
            self._create_collection(collection_name=collection_name, dimension=len(items[0]['vector']))

        log.info('Upserting %s items into collection %s_%s.', len(items), self.collection_prefix, collection_name)
        data = []
        for item in items:
            text = item['text'] or ''
            if len(text) > MILVUS_TEXT_MAX_LENGTH:
                log.warning(f'Milvus: truncating text id={item["id"]} {len(text)}->{MILVUS_TEXT_MAX_LENGTH} chars')
                text = text[:MILVUS_TEXT_MAX_LENGTH]
            data.append(
                {
                    'id': item['id'],
                    'vector': item['vector'],
                    'data': {'text': text},
                    'metadata': process_metadata(item['metadata']),
                }
            )
        try:
            return self.client.upsert(
                collection_name=f'{self.collection_prefix}_{collection_name}',
                data=data,
            )
        except MilvusException as e:
            log.error(f'Milvus upsert failed for {self.collection_prefix}_{collection_name} ({len(items)} items): {e}')
            raise

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the collection based on the ids or filter.
        collection_name = collection_name.replace('-', '_')
        if not self.has_collection(collection_name):
            log.warning(f'Delete attempted on non-existent collection: {self.collection_prefix}_{collection_name}')
            return None

        if ids:
            log.info('Deleting items by IDs from %s_%s. IDs: %s', self.collection_prefix, collection_name, ids)
            return self.client.delete(
                collection_name=f'{self.collection_prefix}_{collection_name}',
                ids=ids,
            )
        elif filter:
            filter_string = ' && '.join(
                [f'metadata["{key}"] == {JSONCodec.dumps(value)}' for key, value in filter.items()]
            )
            log.info(
                'Deleting items by filter from %s_%s. Filter: %s',
                self.collection_prefix,
                collection_name,
                filter_string,
            )
            return self.client.delete(
                collection_name=f'{self.collection_prefix}_{collection_name}',
                filter=filter_string,
            )
        else:
            log.warning(
                f'Delete operation on {self.collection_prefix}_{collection_name} called without IDs or filter. No action taken.'
            )
            return None

    def reset(self):
        # Resets the database. This will delete all collections and item entries that match the prefix.
        log.warning(f"Resetting Milvus: Deleting all collections with prefix '{self.collection_prefix}'.")
        collection_names = self.client.list_collections()
        deleted_collections = []
        for collection_name_full in collection_names:
            if collection_name_full.startswith(self.collection_prefix):
                try:
                    self.client.drop_collection(collection_name=collection_name_full)
                    deleted_collections.append(collection_name_full)
                    log.info('Deleted collection: %s', collection_name_full)
                except Exception as e:
                    log.error(f'Error deleting collection {collection_name_full}: {e}')
        log.info('Milvus reset complete. Deleted collections: %s', deleted_collections)

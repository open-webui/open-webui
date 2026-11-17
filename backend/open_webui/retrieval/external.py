import asyncio
import logging
import re
import time
from itertools import zip_longest
from typing import Any, Optional
from urllib.parse import quote

import aiohttp
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.models.config import Config
from open_webui.models.knowledge import KnowledgeModel
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

EXTERNAL_KNOWLEDGE_CONNECTIONS_CONFIG_KEY = 'external_knowledge.connections'
IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

# OpenAI caps vector store search at 50 results and list pages at 100 stores.
OPENAI_VECTOR_STORE_MAX_RESULTS = 50
OPENAI_VECTOR_STORE_PAGE_SIZE = 100
# Stops a server that always reports more pages; allows 10,000 stores.
OPENAI_VECTOR_STORE_MAX_PAGES = 100


async def _get_external_connection(connection_id: str) -> Optional[dict]:
    connections = await Config.get(EXTERNAL_KNOWLEDGE_CONNECTIONS_CONFIG_KEY, []) or []
    return next((connection for connection in connections if connection.get('id') == connection_id), None)


def _get_path(data: Any, path: Optional[str], default=None):
    if not path:
        return default
    value = data
    for part in path.split('.'):
        if isinstance(value, dict):
            value = value.get(part, default)
        else:
            return default
    return value


def _normalize_result(result: dict, mapping: dict, knowledge: KnowledgeModel, distance: Optional[float] = None) -> dict:
    content = _get_path(result, mapping.get('content_field', 'content'), '')
    title = _get_path(result, mapping.get('title_field', 'title'), None)
    source = _get_path(result, mapping.get('source_field', 'source'), None)
    url = _get_path(result, mapping.get('url_field', 'url'), None)
    document_id = _get_path(result, mapping.get('document_id_field', 'document_id'), None)
    page = _get_path(result, mapping.get('page_field', 'page'), None)
    metadata = _get_path(result, mapping.get('metadata_field', 'metadata'), {}) or {}
    score = _get_path(result, mapping.get('score_field', 'score'), distance)

    if not isinstance(metadata, dict):
        metadata = {'external_metadata': metadata}

    source_name = source or title or metadata.get('source') or metadata.get('name') or knowledge.name
    metadata.update(
        {
            'name': title or metadata.get('name') or source_name,
            'source': source_name,
            'url': url,
            'knowledge_id': knowledge.id,
            'knowledge_name': knowledge.name,
            'external': True,
        }
    )
    # external results are not Open WebUI files, even when the payload carries a file_id
    metadata.pop('file_id', None)
    if page is not None:
        metadata['page'] = page
    if document_id is not None:
        metadata['document_id'] = document_id

    return {
        'content': content,
        'metadata': metadata,
        'distance': score,
    }


def _source_config(knowledge: KnowledgeModel) -> dict:
    external = (knowledge.meta or {}).get('external', {})
    source = external.get('source') or {}
    return source.get('config') or {}


def _root_field(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return path.split('.')[0]


def _safe_identifier(value: str, label: str) -> str:
    if not value or not IDENTIFIER_RE.match(value):
        raise RuntimeError(f'Invalid {label}')
    return value


async def _retrieve_qdrant(connection, auth_config, knowledge, query, count, embedding_function) -> list[dict]:
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        raise RuntimeError('qdrant-client is not installed') from exc

    if not embedding_function:
        raise RuntimeError('Embedding function is not configured')

    config = connection.get('config') or {}
    external = (knowledge.meta or {}).get('external', {})
    source = external.get('source') or {}
    collection_name = source.get('name')
    if not collection_name:
        raise RuntimeError('External source collection is not configured')
    source_config = _source_config(knowledge)
    vector_field = source_config.get('vector_field') or None

    vector = await embedding_function(query, prefix=await Config.get('rag.embedding_query_prefix'))

    def _search():
        client = QdrantClient(
            url=connection.get('endpoint'),
            api_key=(auth_config or {}).get('api_key'),
            timeout=config.get('timeout') or 30,
        )
        return client.query_points(
            collection_name=collection_name,
            query=vector,
            using=vector_field,
            limit=count,
        )

    response = await asyncio.to_thread(_search)
    mapping = {
        'content_field': source_config.get('content_field') or 'payload.text',
        'metadata_field': source_config.get('metadata_field') or 'payload.metadata',
        'document_id_field': source_config.get('document_id_field') or 'id',
        'score_field': 'score',
    }

    normalized = []
    for point in response.points:
        normalized.append(_normalize_result(point.model_dump(), mapping, knowledge, distance=point.score))
    return normalized


async def _retrieve_milvus(connection, auth_config, knowledge, query, count, embedding_function) -> list[dict]:
    try:
        from pymilvus import MilvusClient
    except ImportError as exc:
        raise RuntimeError('pymilvus is not installed') from exc

    if not embedding_function:
        raise RuntimeError('Embedding function is not configured')

    config = connection.get('config') or {}
    external = (knowledge.meta or {}).get('external', {})
    source = external.get('source') or {}
    collection_name = source.get('name')
    if not collection_name:
        raise RuntimeError('Milvus collection is not configured')
    source_config = _source_config(knowledge)
    vector_field = source_config.get('vector_field') or 'vector'
    content_field = source_config.get('content_field') or 'data.text'
    metadata_field = source_config.get('metadata_field') or 'metadata'

    vector = await embedding_function(query, prefix=await Config.get('rag.embedding_query_prefix'))

    def _search():
        client_kwargs = {
            'uri': connection.get('endpoint'),
        }
        token = (auth_config or {}).get('api_key') or (auth_config or {}).get('token')
        if token:
            client_kwargs['token'] = token
        if config.get('db_name'):
            client_kwargs['db_name'] = config.get('db_name')

        client = MilvusClient(**client_kwargs)
        output_fields = {
            field
            for field in (
                _root_field(content_field),
                _root_field(metadata_field),
                _root_field(source_config.get('document_id_field')),
            )
            if field and field != vector_field
        }
        kwargs = {
            'collection_name': collection_name,
            'data': [vector],
            'anns_field': vector_field,
            'limit': count,
            'output_fields': list(output_fields),
        }
        return client.search(**kwargs)

    response = await asyncio.to_thread(_search)
    mapping = {
        'content_field': content_field,
        'metadata_field': metadata_field,
        'document_id_field': source_config.get('document_id_field') or 'id',
        'score_field': 'distance',
    }

    normalized = []
    for hit in response[0] if response else []:
        item = dict(hit)
        entity = item.get('entity') or {}
        result = {
            **entity,
            'id': item.get('id') or entity.get('id'),
            'distance': item.get('distance'),
        }
        normalized.append(_normalize_result(result, mapping, knowledge, distance=item.get('distance')))
    return normalized


async def _retrieve_pgvector(connection, auth_config, knowledge, query, count, embedding_function) -> list[dict]:
    try:
        import psycopg
        from pgvector import Vector
        from pgvector.psycopg import register_vector
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError('psycopg and pgvector are required for pgvector retrieval') from exc

    if not embedding_function:
        raise RuntimeError('Embedding function is not configured')

    config = connection.get('config') or {}
    external = (knowledge.meta or {}).get('external', {})
    source = external.get('source') or {}
    collection_name = source.get('name')
    if not collection_name:
        raise RuntimeError('pgvector collection is not configured')
    source_config = _source_config(knowledge)
    table_name = source_config.get('table_name') or 'document_chunk'
    collection_field = source_config.get('collection_field') or 'collection_name'
    content_field = source_config.get('content_field') or 'text'
    vector_field = source_config.get('vector_field') or 'vector'
    metadata_field = source_config.get('metadata_field') or 'vmetadata'
    document_id_field = source_config.get('document_id_field') or 'id'

    vector = await embedding_function(query, prefix=await Config.get('rag.embedding_query_prefix'))

    def _search():
        from psycopg import sql

        table_identifier = sql.SQL('.').join(
            sql.Identifier(_safe_identifier(part, 'table name')) for part in table_name.split('.')
        )
        collection_identifier = sql.Identifier(_safe_identifier(collection_field, 'collection field'))
        content_identifier = sql.Identifier(_safe_identifier(content_field, 'content field'))
        vector_identifier = sql.Identifier(_safe_identifier(vector_field, 'vector field'))
        document_id_identifier = sql.Identifier(_safe_identifier(document_id_field, 'document id field'))
        metadata_sql = (
            sql.Identifier(_safe_identifier(metadata_field, 'metadata field'))
            if metadata_field
            else sql.SQL("'{}'::jsonb")
        )

        with psycopg.connect(
            connection.get('endpoint'),
            row_factory=dict_row,
            connect_timeout=config.get('timeout') or 30,
        ) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        """
                    SELECT {document_id} AS id,
                           {content} AS content,
                           {metadata} AS metadata,
                           {vector_column} <=> %s AS distance
                    FROM {table_name}
                    WHERE {collection} = %s
                    ORDER BY distance ASC
                    LIMIT %s
                    """
                    ).format(
                        document_id=document_id_identifier,
                        content=content_identifier,
                        metadata=metadata_sql,
                        vector_column=vector_identifier,
                        table_name=table_identifier,
                        collection=collection_identifier,
                    ),
                    (Vector(vector), collection_name, count),
                )
                return cur.fetchall()

    rows = await asyncio.to_thread(_search)
    mapping = {
        'content_field': 'content',
        'metadata_field': 'metadata',
        'document_id_field': 'id',
        'score_field': 'distance',
    }
    return [_normalize_result(row, mapping, knowledge, distance=row.get('distance')) for row in rows]


async def _openai_vector_store_request(
    connection: dict,
    auth_config: Optional[dict],
    method: str,
    path: str,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
) -> dict:
    """Call an OpenAI-compatible vector store API (OpenAI, LiteLLM, Azure OpenAI v1 at /openai/v1)."""
    base_url = (connection.get('endpoint') or '').strip().rstrip('/')
    if not base_url:
        raise RuntimeError('Endpoint is not configured')

    headers = {'Accept': 'application/json'}
    api_key = (auth_config or {}).get('api_key')
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    timeout = aiohttp.ClientTimeout(total=(connection.get('config') or {}).get('timeout') or 30)
    session = await get_session()
    try:
        async with session.request(
            method,
            f'{base_url}{path}',
            headers=headers,
            params=params,
            json=json,
            timeout=timeout,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            if r.status >= 400:
                detail = (await r.text())[:500]
                raise RuntimeError(f'Vector store request failed ({r.status}): {detail}')
            try:
                data = await r.json(content_type=None)
            except ValueError as exc:
                raise RuntimeError(f'Vector store endpoint returned a non-JSON response ({r.status})') from exc
    except aiohttp.ClientError as exc:
        raise RuntimeError(f'Vector store request failed: {exc}') from exc

    if not isinstance(data, dict):
        raise RuntimeError('Vector store endpoint returned an unexpected response')
    return data


def get_vector_store_ids(source: dict) -> list[str]:
    """Store IDs a text-search source covers; older sources keep a single ID in `name`."""
    ids = (source.get('config') or {}).get('vector_store_ids')
    if not isinstance(ids, list):
        ids = (source.get('name') or '').split(',')
    return list(dict.fromkeys(str(store_id).strip() for store_id in ids if str(store_id).strip()))


async def _search_openai_vector_store(connection, auth_config, knowledge, vector_store_id, query, count) -> list[dict]:
    data = await _openai_vector_store_request(
        connection,
        auth_config,
        'POST',
        f'/vector_stores/{quote(vector_store_id, safe="")}/search',
        json={
            'query': query,
            'max_num_results': max(1, min(count, OPENAI_VECTOR_STORE_MAX_RESULTS)),
        },
    )

    normalized = []
    for item in data.get('data') or []:
        if not isinstance(item, dict):
            continue
        content = '\n'.join(
            part['text']
            for part in item.get('content') or []
            if isinstance(part, dict) and isinstance(part.get('text'), str) and part['text']
        )
        if not content:
            continue
        attributes = item.get('attributes') if isinstance(item.get('attributes'), dict) else {}
        result = {
            'content': content,
            'title': item.get('filename'),
            # Kept from the file's attributes, which _normalize_result would otherwise overwrite.
            'url': attributes.get('url'),
            'document_id': item.get('file_id'),
            'metadata': attributes,
            'score': item.get('score'),
        }
        normalized.append(_normalize_result(result, {}, knowledge, distance=item.get('score')))
    return normalized[:count]


async def _retrieve_openai(connection, auth_config, knowledge, query, count, embedding_function) -> list[dict]:
    # The server embeds the query, so the Open WebUI embedding model is not involved.
    source = (knowledge.meta or {}).get('external', {}).get('source') or {}
    vector_store_ids = get_vector_store_ids(source)
    if not vector_store_ids:
        raise RuntimeError('Vector store ID is not configured')

    results = await asyncio.gather(
        *(
            _search_openai_vector_store(connection, auth_config, knowledge, store_id, query, count)
            for store_id in vector_store_ids
        ),
        return_exceptions=True,
    )
    # One unreachable store should not hide the others; fail only when every store failed.
    failures = [result for result in results if isinstance(result, BaseException)]
    for store_id, result in zip(vector_store_ids, results):
        if isinstance(result, BaseException):
            log.warning('Vector store %s search failed: %s', store_id, result)
    if len(failures) == len(results):
        raise failures[0]

    # Stores may sit on different backends with incomparable scores, so interleave by rank.
    merged = [
        chunk
        for chunks_at_rank in zip_longest(*(result for result in results if not isinstance(result, BaseException)))
        for chunk in chunks_at_rank
        if chunk
    ]
    return merged[:count]


async def list_openai_vector_stores(connection: dict) -> list[dict]:
    """List the vector stores a connection can search, as {id, name}.

    LiteLLM's registry comes first since it covers every backend LiteLLM proxies; servers without
    it (OpenAI, Azure) are listed through the OpenAI vector stores API.
    """
    auth_config = connection.get('auth_config') or {}

    try:
        data = await _openai_vector_store_request(
            connection, auth_config, 'GET', '/vector_store/list', params={'page_size': 1000}
        )
        if isinstance(data.get('data'), list):
            return [
                {'id': item['vector_store_id'], 'name': item.get('vector_store_name') or item['vector_store_id']}
                for item in data['data']
                if isinstance(item, dict) and item.get('vector_store_id')
            ]
    except RuntimeError:
        pass

    stores = []
    after = None
    for _ in range(OPENAI_VECTOR_STORE_MAX_PAGES):
        data = await _openai_vector_store_request(
            connection,
            auth_config,
            'GET',
            '/vector_stores',
            params={'limit': OPENAI_VECTOR_STORE_PAGE_SIZE, **({'after': after} if after else {})},
        )
        items = [item for item in data.get('data') or [] if isinstance(item, dict) and item.get('id')]
        stores.extend({'id': item['id'], 'name': item.get('name') or item['id']} for item in items)
        if not data.get('has_more') or not items:
            break
        after = data.get('last_id') or items[-1]['id']
    return stores


async def retrieve_external_knowledge(
    request,
    knowledge: KnowledgeModel,
    queries: list[str],
    count: int,
    user=None,
) -> dict:
    external = (knowledge.meta or {}).get('external', {})
    connection_id = external.get('connection_id')
    if not connection_id:
        raise RuntimeError('External knowledge connection is not configured')

    connection = await _get_external_connection(connection_id)
    if not connection:
        raise RuntimeError('External knowledge connection not found')

    return await retrieve_external_knowledge_for_connection(request, knowledge, connection, queries, count, user=user)


async def retrieve_external_knowledge_for_connection(
    request,
    knowledge: KnowledgeModel,
    connection: dict,
    queries: list[str],
    count: int,
    user=None,
) -> dict:
    auth_config = connection.get('auth_config') or {}
    if not connection.get('enabled', True):
        raise RuntimeError('External knowledge connection is disabled')

    started_at = time.monotonic()
    chunks = []
    provider = (connection.get('provider') or '').lower()

    retrieve = {
        'qdrant': _retrieve_qdrant,
        'milvus': _retrieve_milvus,
        'pgvector': _retrieve_pgvector,
        'openai': _retrieve_openai,
    }.get(provider)
    if not retrieve:
        raise RuntimeError(f'Unsupported external knowledge provider: {connection.get("provider")}')

    embedding_function = getattr(request.app.state, 'EMBEDDING_FUNCTION', None)
    query_chunks = await asyncio.gather(
        *(retrieve(connection, auth_config, knowledge, query, count, embedding_function) for query in queries)
    )

    # Score direction differs per provider and metric, so merge by rank
    seen_contents = set()
    for chunks_at_rank in zip_longest(*query_chunks):
        for chunk in chunks_at_rank:
            if chunk and chunk['content'] not in seen_contents:
                seen_contents.add(chunk['content'])
                chunks.append(chunk)

    chunks = chunks[:count]
    log.info(
        'external_knowledge_retrieval knowledge_id=%s connection_id=%s provider=%s user_id=%s latency_ms=%s result_count=%s',
        knowledge.id,
        connection.get('id'),
        connection.get('provider'),
        getattr(user, 'id', None),
        round((time.monotonic() - started_at) * 1000),
        len(chunks),
    )

    return {
        'documents': [[chunk['content'] for chunk in chunks]],
        'metadatas': [[chunk['metadata'] for chunk in chunks]],
        'distances': [[chunk['distance'] for chunk in chunks]],
    }

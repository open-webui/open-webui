import asyncio
import logging
import re
import time
from typing import Any, Optional

from open_webui.models.config import Config
from open_webui.models.knowledge import KnowledgeModel

log = logging.getLogger(__name__)

EXTERNAL_KNOWLEDGE_CONNECTIONS_CONFIG_KEY = 'external_knowledge.connections'
IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


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
            'name': title or source_name,
            'source': source_name,
            'url': url,
            'file_id': document_id or f'external-{knowledge.id}',
            'knowledge_id': knowledge.id,
            'knowledge_name': knowledge.name,
            'external': True,
        }
    )
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

    vector = await embedding_function(query)

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

    vector = await embedding_function(query)

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

    vector = await embedding_function(query)

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
                    (vector, collection_name, count),
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

    for query in queries:
        if provider == 'qdrant':
            chunks.extend(
                await _retrieve_qdrant(
                    connection,
                    auth_config,
                    knowledge,
                    query,
                    count,
                    getattr(request.app.state, 'EMBEDDING_FUNCTION', None),
                )
            )
        elif provider == 'milvus':
            chunks.extend(
                await _retrieve_milvus(
                    connection,
                    auth_config,
                    knowledge,
                    query,
                    count,
                    getattr(request.app.state, 'EMBEDDING_FUNCTION', None),
                )
            )
        elif provider == 'pgvector':
            chunks.extend(
                await _retrieve_pgvector(
                    connection,
                    auth_config,
                    knowledge,
                    query,
                    count,
                    getattr(request.app.state, 'EMBEDDING_FUNCTION', None),
                )
            )
        else:
            raise RuntimeError(f'Unsupported external knowledge provider: {connection.get("provider")}')

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

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
import uuid
import zipfile
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.files import FileMetadataResponse, FileModel, FileModelResponse, Files
from open_webui.models.groups import Groups
from open_webui.models.knowledge import (
    KnowledgeDirectoryForm,
    KnowledgeDirectoryModel,
    KnowledgeFileListResponse,
    KnowledgeForm,
    KnowledgeResponse,
    Knowledges,
    KnowledgeUserResponse,
)
from open_webui.models.models import ModelForm, Models
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.retrieval.external import retrieve_external_knowledge, retrieve_external_knowledge_for_connection
from open_webui.routers.retrieval import (
    BatchProcessFilesForm,
    ProcessFileForm,
    process_file,
    process_files_batch,
)
from open_webui.storage.provider import Storage
from open_webui.utils.access_control import filter_allowed_access_grants, has_permission
from open_webui.utils.access_control.files import has_access_to_file
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()

############################
# getKnowledgeBases
############################

PAGE_ITEM_COUNT = 30

############################
# Knowledge Base Embedding
############################

# Knowledge that sits unread serves no one. Let what is
# stored here find the ones who need it.
KNOWLEDGE_BASES_COLLECTION = 'knowledge-bases'


async def embed_knowledge_base_metadata(
    request: Request,
    knowledge_base_id: str,
    name: str,
    description: str,
) -> bool:
    """Generate and store embedding for knowledge base."""
    try:
        content = f'{name}\n\n{description}' if description else name
        embedding = await request.app.state.EMBEDDING_FUNCTION(content)
        await ASYNC_VECTOR_DB_CLIENT.upsert(
            collection_name=KNOWLEDGE_BASES_COLLECTION,
            items=[
                {
                    'id': knowledge_base_id,
                    'text': content,
                    'vector': embedding,
                    'metadata': {
                        'knowledge_base_id': knowledge_base_id,
                    },
                }
            ],
        )
        return True
    except Exception as e:
        log.error(f'Failed to embed knowledge base {knowledge_base_id}: {e}')
        return False


async def remove_knowledge_base_metadata_embedding(knowledge_base_id: str) -> bool:
    """Remove knowledge base embedding."""
    try:
        await ASYNC_VECTOR_DB_CLIENT.delete(
            collection_name=KNOWLEDGE_BASES_COLLECTION,
            ids=[knowledge_base_id],
        )
        return True
    except Exception as e:
        log.debug(f'Failed to remove embedding for {knowledge_base_id}: {e}')
        return False


class KnowledgeAccessResponse(KnowledgeUserResponse):
    write_access: bool | None = False


class KnowledgeAccessListResponse(BaseModel):
    items: list[KnowledgeAccessResponse]
    total: int


def is_external_knowledge(knowledge) -> bool:
    return (knowledge.meta or {}).get('source') == 'external'


def external_knowledge_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='External knowledge bases are read-only.',
    )


@router.get('/', response_model=KnowledgeAccessListResponse)
async def get_knowledge_bases(
    page: int | None = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    page = max(page, 1)
    limit = PAGE_ITEM_COUNT
    skip = (page - 1) * limit

    filter = {}
    groups = await Groups.get_groups_by_member_id(user.id, db=db)
    user_group_ids = {group.id for group in groups}

    if not user.role == 'admin' or not BYPASS_ADMIN_ACCESS_CONTROL:
        if groups:
            filter['group_ids'] = [group.id for group in groups]

        filter['user_id'] = user.id

    result = await Knowledges.search_knowledge_bases(user.id, filter=filter, skip=skip, limit=limit, db=db)

    # Batch-fetch writable knowledge IDs in a single query instead of N has_access calls
    knowledge_base_ids = [knowledge_base.id for knowledge_base in result.items]
    writable_knowledge_base_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type='knowledge',
        resource_ids=knowledge_base_ids,
        permission='write',
        user_group_ids=user_group_ids,
        db=db,
    )

    return KnowledgeAccessListResponse(
        items=[
            KnowledgeAccessResponse(
                **knowledge_base.model_dump(),
                write_access=(
                    user.id == knowledge_base.user_id
                    or (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
                    or knowledge_base.id in writable_knowledge_base_ids
                ),
            )
            for knowledge_base in result.items
        ],
        total=result.total,
    )


@router.get('/search', response_model=KnowledgeAccessListResponse)
async def search_knowledge_bases(
    query: str | None = None,
    view_option: str | None = None,
    source: str | None = None,
    page: int | None = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    page = max(page, 1)
    limit = PAGE_ITEM_COUNT
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if view_option:
        filter['view_option'] = view_option
    if source in {'local', 'external'}:
        filter['source'] = source

    groups = await Groups.get_groups_by_member_id(user.id, db=db)
    user_group_ids = {group.id for group in groups}

    if not user.role == 'admin' or not BYPASS_ADMIN_ACCESS_CONTROL:
        if groups:
            filter['group_ids'] = [group.id for group in groups]

        filter['user_id'] = user.id

    result = await Knowledges.search_knowledge_bases(user.id, filter=filter, skip=skip, limit=limit, db=db)

    # Batch-fetch writable knowledge IDs in a single query instead of N has_access calls
    knowledge_base_ids = [knowledge_base.id for knowledge_base in result.items]
    writable_knowledge_base_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type='knowledge',
        resource_ids=knowledge_base_ids,
        permission='write',
        user_group_ids=user_group_ids,
        db=db,
    )

    return KnowledgeAccessListResponse(
        items=[
            KnowledgeAccessResponse(
                **knowledge_base.model_dump(),
                write_access=(
                    user.id == knowledge_base.user_id
                    or (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
                    or knowledge_base.id in writable_knowledge_base_ids
                ),
            )
            for knowledge_base in result.items
        ],
        total=result.total,
    )


@router.get('/search/files', response_model=KnowledgeFileListResponse)
async def search_knowledge_files(
    query: str | None = None,
    include_content: bool = Query(False, description='Include file content in search (expensive).'),
    page: int | None = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    page = max(page, 1)
    limit = PAGE_ITEM_COUNT
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if include_content:
        filter['include_content'] = True

    groups = await Groups.get_groups_by_member_id(user.id, db=db)
    if groups:
        filter['group_ids'] = [group.id for group in groups]

    filter['user_id'] = user.id

    return await Knowledges.search_knowledge_files(filter=filter, skip=skip, limit=limit, db=db)


############################
# CreateNewKnowledge
############################


@router.post('/create', response_model=KnowledgeResponse | None)
async def create_new_knowledge(
    request: Request,
    form_data: KnowledgeForm,
    user=Depends(get_verified_user),
):
    # NOTE: We intentionally do NOT use Depends(get_async_session) here.
    # Database operations (has_permission, filter_allowed_access_grants, insert_new_knowledge) manage their own sessions.
    # This prevents holding a connection during embed_knowledge_base_metadata()
    # which makes external embedding API calls (1-5+ seconds).
    if user.role != 'admin' and not await has_permission(
        user.id, 'workspace.knowledge', await Config.get('user.permissions')
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    knowledge = await Knowledges.insert_new_knowledge(user.id, form_data)

    if knowledge:
        # Embed knowledge base for semantic search
        await embed_knowledge_base_metadata(
            request,
            knowledge.id,
            knowledge.name,
            knowledge.description,
        )
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_CREATED,
            actor=user,
            subject_id=knowledge.id,
            data={'name': knowledge.name},
        )
        return knowledge
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_EXISTS,
        )


############################
# ReindexKnowledgeFiles
############################


@router.post('/reindex', response_model=bool)
async def reindex_knowledge_files(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge_bases = await Knowledges.get_knowledge_bases(db=db)
    knowledge_base_files = [
        (knowledge_base, await Knowledges.get_files_by_id(knowledge_base.id, db=db))
        for knowledge_base in knowledge_bases
    ]
    total_files = sum(len(files) for _, files in knowledge_base_files)
    processed_files = 0
    failed_files = []
    start_time = time.monotonic()

    log.info(f'Starting reindexing for {len(knowledge_bases)} knowledge bases ({total_files} files)')

    for kb_idx, (knowledge_base, files) in enumerate(knowledge_base_files, start=1):
        try:
            try:
                if await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name=knowledge_base.id):
                    await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=knowledge_base.id)
            except Exception as e:
                log.error(f'Error deleting collection {knowledge_base.id}: {str(e)}')
                continue  # Skip, don't raise

            for file in files:
                processed_files += 1
                eta = ''
                if processed_files > 1:
                    elapsed = time.monotonic() - start_time
                    remaining_files = total_files - processed_files + 1
                    eta = f', ETA: {round(elapsed / (processed_files - 1) * remaining_files)}s'

                log.info(
                    f'Reindexing knowledge base {kb_idx}/{len(knowledge_bases)} '
                    f'file {processed_files}/{total_files}{eta}: {file.filename}'
                )

                try:
                    await process_file(
                        request,
                        ProcessFileForm(file_id=file.id, collection_name=knowledge_base.id),
                        user=user,
                        db=db,
                    )
                except Exception as e:
                    log.error(f'Error processing file {file.filename} (ID: {file.id}): {str(e)}')
                    failed_files.append({'file_id': file.id, 'error': str(e)})
                    continue

        except Exception as e:
            log.error(f'Error processing knowledge base {knowledge_base.id}: {str(e)}')
            # Don't raise, just continue
            continue

    if failed_files:
        log.warning(f'Failed to process {len(failed_files)} files')
        for failed in failed_files:
            log.warning(f'File ID: {failed["file_id"]}, Error: {failed["error"]}')

    log.info(f'Reindexing completed in {round(time.monotonic() - start_time)}s.')
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_REINDEXED,
        actor=user,
        subject_id='all',
        data={'count': len(knowledge_bases)},
    )
    return True


############################
# ReindexKnowledgeBases
############################


@router.post('/metadata/reindex', response_model=dict)
async def reindex_knowledge_base_metadata_embeddings(
    request: Request,
    user=Depends(get_admin_user),
):
    """Batch embed all existing knowledge bases. Admin only.

    NOTE: We intentionally do NOT use Depends(get_async_session) here.
    This endpoint loops through ALL knowledge bases and calls embed_knowledge_base_metadata()
    for each one, making N external embedding API calls. Holding a session during
    this entire operation would exhaust the connection pool.
    """
    knowledge_bases = await Knowledges.get_knowledge_bases()
    log.info(f'Reindexing embeddings for {len(knowledge_bases)} knowledge bases')

    success_count = 0
    for kb in knowledge_bases:
        if await embed_knowledge_base_metadata(request, kb.id, kb.name, kb.description):
            success_count += 1

    log.info(f'Embedding reindex complete: {success_count}/{len(knowledge_bases)}')
    return {'total': len(knowledge_bases), 'success': success_count}


############################
# External Knowledge Sources
############################


class ExternalKnowledgeSourceForm(BaseModel):
    type: str = 'collection'
    name: str
    config: Optional[dict] = None


class ExternalKnowledgeCreateForm(BaseModel):
    name: str
    description: str = ''
    connection_id: str
    source: ExternalKnowledgeSourceForm
    access_grants: Optional[list[dict]] = None


class ExternalKnowledgeSourceCreateForm(BaseModel):
    name: str
    description: str = ''
    connection: ExternalKnowledgeConnectionForm
    source: ExternalKnowledgeSourceForm
    access_grants: Optional[list[dict]] = None
    test_query: str
    test_count: int = 5


class ExternalKnowledgeSourceUpdateForm(ExternalKnowledgeSourceCreateForm):
    pass


class ExternalKnowledgeSourceTestForm(BaseModel):
    connection_id: Optional[str] = None
    connection: ExternalKnowledgeConnectionForm
    source: ExternalKnowledgeSourceForm
    query: str
    count: int = 5


class ExternalKnowledgeRetrieveTestForm(BaseModel):
    query: str
    source: Optional[ExternalKnowledgeSourceForm] = None
    count: int = 5


class ExternalKnowledgeConnectionForm(BaseModel):
    name: str
    provider: str
    endpoint: str
    auth_config: Optional[dict] = None
    config: Optional[dict] = None
    capabilities: Optional[dict] = None
    enabled: bool = True


class ExternalKnowledgeConnectionListResponse(BaseModel):
    items: list[dict]
    total: int


EXTERNAL_KNOWLEDGE_CONNECTIONS_CONFIG_KEY = 'external_knowledge.connections'
EXTERNAL_KNOWLEDGE_PROVIDERS = {'qdrant', 'milvus', 'pgvector'}


def _validate_external_connection_form(form_data: ExternalKnowledgeConnectionForm) -> tuple[str, dict]:
    provider = form_data.provider.lower().strip()
    if provider not in EXTERNAL_KNOWLEDGE_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Unsupported external knowledge provider.',
        )

    if not form_data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Knowledge source name is required.')

    if not form_data.endpoint.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Knowledge source endpoint is required.')

    config = form_data.config or {}
    allowed_config_keys = {'timeout'}
    if provider == 'milvus':
        allowed_config_keys.add('db_name')

    return provider, {key: value for key, value in config.items() if key in allowed_config_keys}


def _external_auth_config(provider: str, incoming: Optional[dict], existing: Optional[dict] = None) -> dict:
    if provider == 'pgvector':
        return {}
    return existing if incoming is None else incoming or {}


def _normalize_external_source(source: ExternalKnowledgeSourceForm, provider: str) -> ExternalKnowledgeSourceForm:
    source.type = (source.type or 'collection').strip()
    source.name = source.name.strip()

    if source.type != 'collection':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Only collection sources are supported.')
    if not source.name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Collection name is required.')

    config = source.config or {}
    allowed_keys = {'content_field', 'metadata_field', 'document_id_field'}
    if provider in {'qdrant', 'milvus'}:
        allowed_keys.add('vector_field')
    if provider == 'pgvector':
        allowed_keys.update({'table_name', 'collection_field', 'vector_field'})

    normalized_config = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in config.items()
        if key in allowed_keys and value is not None and (not isinstance(value, str) or value.strip())
    }

    if not normalized_config.get('content_field'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Content field is required.')
    if provider in {'milvus', 'pgvector'} and not normalized_config.get('vector_field'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Vector field is required.')

    source.config = normalized_config
    return source


def _sanitize_external_connection(connection: dict) -> dict:
    sanitized = {**connection}
    sanitized.pop('auth_config', None)
    sanitized['auth_configured'] = bool(connection.get('auth_config'))
    return sanitized


async def _get_external_connections() -> list[dict]:
    return await Config.get(EXTERNAL_KNOWLEDGE_CONNECTIONS_CONFIG_KEY, []) or []


async def _set_external_connections(connections: list[dict]) -> None:
    await Config.upsert({EXTERNAL_KNOWLEDGE_CONNECTIONS_CONFIG_KEY: connections})


def _external_connection_dict(
    form_data: ExternalKnowledgeConnectionForm, user_id: str, id: Optional[str] = None
) -> dict:
    provider, config = _validate_external_connection_form(form_data)
    now = int(time.time())
    return {
        'id': id or str(uuid.uuid4()),
        'name': form_data.name.strip(),
        'provider': provider,
        'endpoint': form_data.endpoint.strip(),
        'auth_config': _external_auth_config(provider, form_data.auth_config),
        'config': config,
        'capabilities': form_data.capabilities or {'retrieve': True},
        'health': None,
        'enabled': form_data.enabled,
        'created_by': user_id,
        'created_at': now,
        'updated_at': now,
    }


def _external_connection_update_dict(
    form_data: ExternalKnowledgeConnectionForm,
    existing: dict,
) -> dict:
    provider, config = _validate_external_connection_form(form_data)
    return {
        **existing,
        'name': form_data.name.strip(),
        'provider': provider,
        'endpoint': form_data.endpoint.strip(),
        'auth_config': _external_auth_config(provider, form_data.auth_config, existing.get('auth_config')) or {},
        'config': config,
        'capabilities': form_data.capabilities or {'retrieve': True},
        'enabled': form_data.enabled,
        'updated_at': int(time.time()),
    }


async def _get_external_connection(id: str) -> Optional[dict]:
    connections = await _get_external_connections()
    return next((connection for connection in connections if connection.get('id') == id), None)


async def _count_external_connection_mappings(connection_id: str, db: Optional[AsyncSession] = None) -> int:
    count = 0
    for knowledge in await Knowledges.get_knowledge_bases(db=db):
        if (knowledge.meta or {}).get('external', {}).get('connection_id') == connection_id:
            count += 1
    return count


@router.get('/external/connections', response_model=ExternalKnowledgeConnectionListResponse)
async def get_external_knowledge_connections(
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    connections = [_sanitize_external_connection(connection) for connection in await _get_external_connections()]
    return ExternalKnowledgeConnectionListResponse(items=connections, total=len(connections))


@router.post('/external/connections', response_model=dict)
async def create_external_knowledge_connection(
    request: Request,
    form_data: ExternalKnowledgeConnectionForm,
    user=Depends(get_admin_user),
):
    connections = await _get_external_connections()
    connection = _external_connection_dict(form_data, user.id)
    connections.append(connection)
    await _set_external_connections(connections)
    sanitized = _sanitize_external_connection(connection)
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_EXTERNAL_CONNECTION_CREATED,
        actor=user,
        subject_id=connection.get('id'),
        data={'name': sanitized.get('name'), 'provider': sanitized.get('provider')},
    )
    return sanitized


@router.get('/external/connections/{id}', response_model=dict)
async def get_external_knowledge_connection(
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    connection = await _get_external_connection(id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return _sanitize_external_connection(connection)


@router.patch('/external/connections/{id}', response_model=dict)
async def update_external_knowledge_connection(
    request: Request,
    id: str,
    form_data: ExternalKnowledgeConnectionForm,
    user=Depends(get_admin_user),
):
    connections = await _get_external_connections()
    idx = next((idx for idx, connection in enumerate(connections) if connection.get('id') == id), None)
    if idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    connection = _external_connection_update_dict(form_data, connections[idx])
    connections[idx] = connection
    await _set_external_connections(connections)
    sanitized = _sanitize_external_connection(connection)
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_EXTERNAL_CONNECTION_UPDATED,
        actor=user,
        subject_id=id,
        data={'name': sanitized.get('name'), 'provider': sanitized.get('provider')},
    )
    return sanitized


@router.delete('/external/connections/{id}', response_model=bool)
async def delete_external_knowledge_connection(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    connection = await _get_external_connection(id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if await _count_external_connection_mappings(id, db=db) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='External connection is still used by knowledge bases.',
        )

    connections = [connection for connection in await _get_external_connections() if connection.get('id') != id]
    await _set_external_connections(connections)
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_EXTERNAL_CONNECTION_DELETED,
        actor=user,
        subject_id=id,
        data={'name': connection.get('name'), 'provider': connection.get('provider')},
    )
    return True


@router.post('/external/connections/{id}/test', response_model=dict)
async def test_external_knowledge_connection(
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    connection = await _get_external_connection(id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    health = {
        'ok': bool(connection.get('enabled') and connection.get('endpoint')),
        'provider': connection.get('provider'),
        'checked_at': int(time.time()),
    }
    connections = await _get_external_connections()
    for item in connections:
        if item.get('id') == id:
            item['health'] = health
            item['updated_at'] = int(time.time())
            break
    await _set_external_connections(connections)
    return health


async def _test_external_source_definition(
    request: Request,
    connection: dict,
    source: ExternalKnowledgeSourceForm,
    query: str,
    count: int,
    user,
) -> dict:
    if not query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Test query is required.')

    source = _normalize_external_source(source, connection.get('provider'))
    test_knowledge = KnowledgeResponse(
        id='external-test',
        user_id=user.id,
        name=connection.get('name'),
        description='',
        meta={
            'source': 'external',
            'read_only': True,
            'external': {
                'connection_id': connection.get('id'),
                'source': source.model_dump(),
                'provider': connection.get('provider'),
                'auth_mode': 'service_account',
                'capabilities': {'retrieve': True},
            },
        },
        access_grants=[],
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )
    result = await retrieve_external_knowledge_for_connection(
        request,
        test_knowledge,
        connection,
        [query.strip()],
        count,
        user=user,
    )
    return {
        'documents': result.get('documents', [[]])[0],
        'metadatas': result.get('metadatas', [[]])[0],
        'distances': result.get('distances', [[]])[0],
    }


@router.post('/external/source/test', response_model=dict)
async def test_external_knowledge_source(
    request: Request,
    form_data: ExternalKnowledgeSourceTestForm,
    user=Depends(get_admin_user),
):
    if form_data.connection_id:
        existing_connection = await _get_external_connection(form_data.connection_id)
        if not existing_connection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='External connection not found.')
        connection = _external_connection_update_dict(form_data.connection, existing_connection)
    else:
        connection = _external_connection_dict(form_data.connection, user.id, id='external-test')

    return await _test_external_source_definition(
        request,
        connection,
        form_data.source,
        form_data.query,
        form_data.count,
        user,
    )


@router.post('/external/connections/{id}/retrieve-test', response_model=dict)
async def test_external_knowledge_retrieval(
    request: Request,
    id: str,
    form_data: ExternalKnowledgeRetrieveTestForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    connection = await _get_external_connection(id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    source = form_data.source or ExternalKnowledgeSourceForm(name='test', config={'content_field': 'payload.text'})
    return await _test_external_source_definition(request, connection, source, form_data.query, form_data.count, user)


@router.post('/external/knowledge/create', response_model=KnowledgeResponse | None)
async def create_external_knowledge(
    request: Request,
    form_data: ExternalKnowledgeCreateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    connection = await _get_external_connection(form_data.connection_id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not form_data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Knowledge name is required.')
    source = _normalize_external_source(form_data.source, connection.get('provider'))

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    knowledge = await Knowledges.insert_new_knowledge(
        user.id,
        KnowledgeForm(
            name=form_data.name.strip(),
            description=form_data.description,
            access_grants=form_data.access_grants,
        ),
        db=db,
    )
    if not knowledge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.FILE_EXISTS)

    meta = {
        'source': 'external',
        'read_only': True,
        'external': {
            'connection_id': form_data.connection_id,
            'source': source.model_dump(),
            'provider': connection.get('provider'),
            'auth_mode': 'service_account',
            'capabilities': {'retrieve': True},
        },
    }
    knowledge = await Knowledges.update_knowledge_meta_by_id(knowledge.id, meta, db=db)
    await embed_knowledge_base_metadata(request, knowledge.id, knowledge.name, knowledge.description)
    return knowledge


@router.post('/external/source/create', response_model=KnowledgeResponse | None)
async def create_external_knowledge_source(
    request: Request,
    form_data: ExternalKnowledgeSourceCreateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not form_data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Knowledge name is required.')

    connection = _external_connection_dict(form_data.connection, user.id)
    source = _normalize_external_source(form_data.source, connection.get('provider'))
    test_result = await _test_external_source_definition(
        request,
        connection,
        source,
        form_data.test_query,
        form_data.test_count,
        user,
    )
    if not test_result.get('documents'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Test query returned no results.')

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    connections = await _get_external_connections()
    connections.append(connection)
    await _set_external_connections(connections)

    knowledge = await Knowledges.insert_new_knowledge(
        user.id,
        KnowledgeForm(
            name=form_data.name.strip(),
            description=form_data.description,
            access_grants=form_data.access_grants,
        ),
        db=db,
    )
    if not knowledge:
        connections = [item for item in await _get_external_connections() if item.get('id') != connection.get('id')]
        await _set_external_connections(connections)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.FILE_EXISTS)

    meta = {
        'source': 'external',
        'read_only': True,
        'external': {
            'connection_id': connection.get('id'),
            'source': source.model_dump(),
            'provider': connection.get('provider'),
            'auth_mode': 'service_account',
            'capabilities': {'retrieve': True},
        },
    }
    knowledge = await Knowledges.update_knowledge_meta_by_id(knowledge.id, meta, db=db)
    await embed_knowledge_base_metadata(request, knowledge.id, knowledge.name, knowledge.description)
    return knowledge


@router.patch('/external/source/{id}', response_model=KnowledgeResponse | None)
async def update_external_knowledge_source(
    request: Request,
    id: str,
    form_data: ExternalKnowledgeSourceUpdateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge or not is_external_knowledge(knowledge):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not form_data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Knowledge name is required.')

    connection_id = (knowledge.meta or {}).get('external', {}).get('connection_id')
    connections = await _get_external_connections()
    idx = next((idx for idx, connection in enumerate(connections) if connection.get('id') == connection_id), None)
    if idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='External connection not found.')

    existing_connection = connections[idx]
    connection = _external_connection_update_dict(form_data.connection, existing_connection)
    source = _normalize_external_source(form_data.source, connection.get('provider'))
    test_result = await _test_external_source_definition(
        request,
        connection,
        source,
        form_data.test_query,
        form_data.test_count,
        user,
    )
    if not test_result.get('documents'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Test query returned no results.')

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    connections[idx] = connection
    await _set_external_connections(connections)

    updated = await Knowledges.update_knowledge_by_id(
        id=id,
        form_data=KnowledgeForm(
            name=form_data.name.strip(),
            description=form_data.description,
            access_grants=form_data.access_grants,
        ),
        db=db,
    )
    if not updated:
        connections[idx] = existing_connection
        await _set_external_connections(connections)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    meta = {
        'source': 'external',
        'read_only': True,
        'external': {
            'connection_id': connection.get('id'),
            'source': source.model_dump(),
            'provider': connection.get('provider'),
            'auth_mode': 'service_account',
            'capabilities': {'retrieve': True},
        },
    }
    updated = await Knowledges.update_knowledge_meta_by_id(id, meta, db=db)
    if not updated:
        connections[idx] = existing_connection
        await _set_external_connections(connections)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    await embed_knowledge_base_metadata(request, id, updated.name, updated.description)
    return updated


############################
# GetKnowledgeById
############################


class KnowledgeFilesResponse(KnowledgeResponse):
    files: list[FileMetadataResponse | None] = None
    write_access: bool | None = False


@router.get('/{id}', response_model=KnowledgeFilesResponse | None)
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)

    if knowledge:
        if (
            user.role == 'admin'
            or knowledge.user_id == user.id
            or await AccessGrants.has_access(
                user_id=user.id,
                resource_type='knowledge',
                resource_id=knowledge.id,
                permission='read',
                db=db,
            )
        ):
            return KnowledgeFilesResponse(
                **knowledge.model_dump(),
                write_access=(
                    user.id == knowledge.user_id
                    or (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
                    or await AccessGrants.has_access(
                        user_id=user.id,
                        resource_type='knowledge',
                        resource_id=knowledge.id,
                        permission='write',
                        db=db,
                    )
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateKnowledgeById
############################


@router.post('/{id}/update', response_model=KnowledgeFilesResponse | None)
async def update_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeForm,
    user=Depends(get_verified_user),
):
    # NOTE: We intentionally do NOT use Depends(get_async_session) here.
    # Database operations manage their own short-lived sessions internally.
    # This prevents holding a connection during embed_knowledge_base_metadata()
    # which makes external embedding API calls (1-5+ seconds).
    knowledge = await Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # Is the user the original creator, in a group with write access, or an admin
    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    knowledge = await Knowledges.update_knowledge_by_id(id=id, form_data=form_data)
    if knowledge:
        # Re-embed knowledge base for semantic search
        await embed_knowledge_base_metadata(
            request,
            knowledge.id,
            knowledge.name,
            knowledge.description,
        )
        response = KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id),
        )
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_UPDATED,
            actor=user,
            subject_id=knowledge.id,
            data={'name': knowledge.name},
        )
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# UpdateKnowledgeAccessById
############################


class KnowledgeAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/{id}/access/update', response_model=KnowledgeFilesResponse | None)
async def update_knowledge_access_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    knowledge.access_grants = await AccessGrants.set_access_grants('knowledge', id, form_data.access_grants, db=db)

    response = KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=await Knowledges.get_file_metadatas_by_id(id, db=db),
    )
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_ACCESS_UPDATED,
        actor=user,
        subject_id=knowledge.id,
        data={'name': knowledge.name},
    )
    return response


############################
# GetPendingKnowledgeFiles
############################


@router.get('/{id}/files/pending')
async def get_pending_knowledge_files(
    id: str,
    stream: bool = Query(False),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return files that are being processed for this knowledge base but not yet linked.

    After a file is uploaded with ``knowledge_id`` in its metadata, the backend
    processes it in a background task before linking it to the ``knowledge_file``
    join table.  During this window the file is invisible to the normal file
    list endpoint.  This endpoint exposes those in-flight files so the frontend
    can show them with a processing indicator even after a page reload.

    When ``stream=true``, returns an SSE stream that polls every 3 seconds
    and emits the current pending file list.  Closes when no files remain.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not (
        user.role == 'admin'
        or knowledge.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='read',
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if not stream:
        return await Files.get_pending_files_for_knowledge(id, db=db)

    async def event_stream(knowledge_id: str):
        MAX_POLL_DURATION = 3600  # 1 hour max
        for _ in range(MAX_POLL_DURATION // 3):
            pending = await Files.get_pending_files_for_knowledge(knowledge_id)
            data = [f.model_dump() for f in pending]
            yield f'data: {json.dumps(data)}\n\n'
            if len(pending) == 0:
                break
            await asyncio.sleep(3)

    return StreamingResponse(
        event_stream(id),
        media_type='text/event-stream',
    )


############################
# GetKnowledgeFilesById
############################


@router.get('/{id}/files', response_model=KnowledgeFileListResponse)
async def get_knowledge_files_by_id(
    id: str,
    query: str | None = None,
    include_content: bool = Query(False, description='Include file content in search (expensive).'),
    view_option: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    directory_id: str | None = Query(None, description='Filter by directory ID. Pass empty string for root.'),
    page: int | None = 1,
    limit: int | None = Query(None, description='Page size (admin only). Defaults to 30.'),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not (
        user.role == 'admin'
        or knowledge.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='read',
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    page = max(page, 1)

    # Allow admins to configure page size; non-admins always get the default
    if user.role == 'admin' and limit is not None:
        limit = max(1, limit)
    else:
        limit = PAGE_ITEM_COUNT
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if include_content:
        filter['include_content'] = True
    if view_option:
        filter['view_option'] = view_option
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction
    # directory_id filtering: present in filter = scope to that directory (None = root)
    if directory_id is not None:
        filter['directory_id'] = directory_id if directory_id else None

    return await Knowledges.search_files_by_id(id, user.id, filter=filter, skip=skip, limit=limit, db=db)


############################
# AddFileToKnowledge
############################


class KnowledgeFileIdForm(BaseModel):
    file_id: str
    directory_id: Optional[str] = None


@router.post('/{id}/file/add', response_model=KnowledgeFilesResponse | None)
async def add_file_to_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = await Files.get_file_by_id(form_data.file_id, db=db)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not file.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_PROCESSED,
        )

    # KB write-access alone is not enough — caller must also be able to read the file.
    if file.user_id != user.id and user.role != 'admin':
        if not await has_access_to_file(file.id, 'read', user, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    # Add content to the vector database
    try:
        await process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
            db=db,
        )

        # Add file to knowledge base
        await Knowledges.add_file_to_knowledge_by_id(
            knowledge_id=id,
            file_id=form_data.file_id,
            user_id=user.id,
            directory_id=form_data.directory_id,
            db=db,
        )
    except Exception as e:
        log.debug(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if knowledge:
        response = KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_FILE_ADDED,
            actor=user,
            subject_id=form_data.file_id,
            data={'knowledge_id': knowledge.id, 'directory_id': form_data.directory_id},
        )
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post('/{id}/file/update', response_model=KnowledgeFilesResponse | None)
async def update_file_from_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = await Files.get_file_by_id(form_data.file_id, db=db)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Validate the file actually belongs to this knowledge base
    if not await Knowledges.has_file(knowledge_id=id, file_id=form_data.file_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database
    await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=knowledge.id, filter={'file_id': form_data.file_id})

    # Add content to the vector database
    try:
        await process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if knowledge:
        response = KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_FILE_UPDATED,
            actor=user,
            subject_id=form_data.file_id,
            data={'knowledge_id': knowledge.id},
        )
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# RemoveFileFromKnowledge
############################


@router.post('/{id}/file/remove', response_model=KnowledgeFilesResponse | None)
async def remove_file_from_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    delete_file: bool = Query(True),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = await Files.get_file_by_id(form_data.file_id, db=db)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Validate the file actually belongs to this knowledge base
    if not await Knowledges.has_file(knowledge_id=id, file_id=form_data.file_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    await Knowledges.remove_file_from_knowledge_by_id(knowledge_id=id, file_id=form_data.file_id, db=db)

    # Remove content from the vector database
    try:
        await ASYNC_VECTOR_DB_CLIENT.delete(
            collection_name=knowledge.id, filter={'file_id': form_data.file_id}
        )  # Remove by file_id first

        await ASYNC_VECTOR_DB_CLIENT.delete(
            collection_name=knowledge.id, filter={'hash': file.hash}
        )  # Remove by hash as well in case of duplicates
    except Exception as e:
        log.debug('This was most likely caused by bypassing embedding processing')
        log.debug(e)
        pass

    # Anyone with write permission or higher can delete files
    if delete_file and (file.user_id == user.id or user.role == 'admin'):
        try:
            # Remove the file's collection from vector database
            file_collection = f'file-{form_data.file_id}'
            if await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name=file_collection):
                await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)
        except Exception as e:
            log.debug('This was most likely caused by bypassing embedding processing')
            log.debug(e)
            pass

        # Delete file from database
        await Files.delete_file_by_id(form_data.file_id, db=db)

    if knowledge:
        response = KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_FILE_REMOVED,
            actor=user,
            subject_id=form_data.file_id,
            data={'knowledge_id': knowledge.id, 'delete_file': delete_file},
        )
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# DeleteKnowledgeById
############################


@router.delete('/{id}/delete', response_model=bool)
async def delete_knowledge_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    log.info(f'Deleting knowledge base: {id} (name: {knowledge.name})')

    # Get all models
    models = await Models.get_all_models(db=db)
    log.info(f'Found {len(models)} models to check for knowledge base {id}')

    # Update models that reference this knowledge base
    for model in models:
        if model.meta and hasattr(model.meta, 'knowledge'):
            knowledge_list = model.meta.knowledge or []
            # Filter out the deleted knowledge base
            updated_knowledge = [k for k in knowledge_list if k.get('id') != id]

            # If the knowledge list changed, update the model
            if len(updated_knowledge) != len(knowledge_list):
                log.info(f'Updating model {model.id} to remove knowledge base {id}')
                model.meta.knowledge = updated_knowledge
                model_form = ModelForm(**model.model_dump())
                await Models.update_model_by_id(model.id, model_form, db=db)

    # Clean up vector DB
    if is_external_knowledge(knowledge):
        connection_id = (knowledge.meta or {}).get('external', {}).get('connection_id')
        if connection_id:
            connections = [
                connection for connection in await _get_external_connections() if connection.get('id') != connection_id
            ]
            await _set_external_connections(connections)
    else:
        try:
            await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=id)
        except Exception as e:
            log.debug(e)
            pass

    # Remove knowledge base embedding
    await remove_knowledge_base_metadata_embedding(id)

    result = await Knowledges.delete_knowledge_by_id(id=id, db=db)
    if result:
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_DELETED,
            actor=user,
            subject_id=id,
            data={'name': knowledge.name},
        )
    return result


############################
# ResetKnowledgeById
############################


@router.post('/{id}/reset', response_model=KnowledgeResponse | None)
async def reset_knowledge_by_id(
    request: Request,
    id: str,
    include_directories: bool = Query(True),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=id)
    except Exception as e:
        log.debug(e)
        pass

    knowledge = await Knowledges.reset_knowledge_by_id(id=id, include_directories=include_directories, db=db)
    if knowledge:
        await publish_event(
            request,
            EVENTS.KNOWLEDGE_RESET,
            actor=user,
            subject_id=id,
            data={'include_directories': include_directories},
        )
    return knowledge


############################
# SyncKnowledgeDiff
############################


class FileManifestEntry(BaseModel):
    filename: str  # basename: "readme.md"
    path: str  # relative dir: "docs/api" or "" for root
    checksum: str  # SHA-256 of raw bytes
    size: int


class SyncDiffForm(BaseModel):
    manifest: list[FileManifestEntry]


class SyncDiffResponse(BaseModel):
    added: list[dict]  # [{filename, path}] — new files
    modified: list[dict]  # [{filename, path, stale_file_id}] — changed files
    deleted: list[dict]  # [{file_id, filename}] — files to remove
    mkdir: list[str]  # directory paths to create
    rmdir: list[str]  # directory IDs to remove
    unmodified_count: int
    directory_map: dict[str, str]  # existing path → directory ID


@router.post('/{id}/sync/diff', response_model=SyncDiffResponse)
async def sync_knowledge_diff(
    id: str,
    form_data: SyncDiffForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Compare a local file manifest against the knowledge base to determine
    which files need uploading, removing, and which directories to create/remove.
    """
    await _verify_knowledge_write_access(id, user, db)

    # ── Index existing state ──
    knowledge_files = await Knowledges.get_files_with_directory_ids(id, db=db)
    existing_directories = await Knowledges.get_all_directories(id, db=db)

    # Build directory path lookups
    directory_path_by_id: dict[str, str] = {}
    directory_id_by_path: dict[str, str] = {}
    for directory in existing_directories:
        segments = [directory.name]
        parent_id = directory.parent_id
        while parent_id:
            parent = next((d for d in existing_directories if d.id == parent_id), None)
            if not parent:
                break
            segments.insert(0, parent.name)
            parent_id = parent.parent_id
        full_path = '/'.join(segments)
        directory_path_by_id[directory.id] = full_path
        directory_id_by_path[full_path] = directory.id

    # Index existing files by (path, filename) → {file_id, checksum}
    indexed_files: dict[tuple[str, str], dict] = {}
    for file_model, directory_id in knowledge_files:
        file_path = directory_path_by_id.get(directory_id, '') if directory_id else ''
        stored_checksum = (file_model.meta or {}).get('file_hash')
        indexed_files[(file_path, file_model.filename)] = {
            'file_id': file_model.id,
            'checksum': stored_checksum,
        }

    # ── Diff files ──
    added: list[dict] = []
    modified: list[dict] = []
    deleted: list[dict] = []
    unmodified_count = 0
    manifest_keys: set[tuple[str, str]] = set()

    for entry in form_data.manifest:
        key = (entry.path, entry.filename)
        manifest_keys.add(key)

        if key not in indexed_files:
            added.append({'filename': entry.filename, 'path': entry.path})
        elif indexed_files[key]['checksum'] != entry.checksum:
            modified.append(
                {
                    'filename': entry.filename,
                    'path': entry.path,
                    'stale_file_id': indexed_files[key]['file_id'],
                }
            )
        else:
            unmodified_count += 1

    for key, file_info in indexed_files.items():
        if key not in manifest_keys:
            deleted.append({'file_id': file_info['file_id'], 'filename': key[1]})

    # ── Diff directories ──
    required_directory_paths: set[str] = set()
    for entry in form_data.manifest:
        if entry.path:
            segments = entry.path.split('/')
            for depth in range(len(segments)):
                required_directory_paths.add('/'.join(segments[: depth + 1]))

    mkdir = sorted([p for p in required_directory_paths if p not in directory_id_by_path], key=lambda p: p.count('/'))

    orphaned_directory_paths = set(directory_id_by_path) - required_directory_paths
    rmdir = [directory_id_by_path[p] for p in orphaned_directory_paths]

    return SyncDiffResponse(
        added=added,
        modified=modified,
        deleted=deleted,
        mkdir=mkdir,
        rmdir=rmdir,
        unmodified_count=unmodified_count,
        directory_map=directory_id_by_path,
    )


############################
# SyncKnowledgeCleanup
############################


class SyncCleanupForm(BaseModel):
    file_ids: list[str]  # file IDs to delete
    dir_ids: list[str] = []  # directory IDs to rmdir


@router.post('/{id}/sync/cleanup')
async def sync_knowledge_cleanup(
    id: str,
    form_data: SyncCleanupForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Remove stale files and orphaned directories from a knowledge base
    after an incremental sync.
    """
    await _verify_knowledge_write_access(id, user, db)

    # ── Remove deleted files ──
    for file_id in form_data.file_ids:
        file = await Files.get_file_by_id(file_id, db=db)
        if not file:
            continue

        await Knowledges.remove_file_from_knowledge_by_id(id, file_id, db=db)

        try:
            await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=id, filter={'file_id': file_id})
            await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=id, filter={'hash': file.hash})
        except Exception:
            pass

        try:
            collection_name = f'file-{file_id}'
            if await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name):
                await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name)
        except Exception:
            pass

        if file.user_id == user.id or user.role == 'admin':
            await Files.delete_file_by_id(file_id, db=db)
            try:
                await asyncio.to_thread(Storage.delete_file, file.path)
            except Exception:
                pass

    # ── Remove orphaned directories (children before parents) ──
    for dir_id in reversed(form_data.dir_ids):
        await Knowledges.delete_directory(dir_id, move_files_to_parent=False, db=db)

    return {'status': True}


############################
# AddFilesToKnowledge
############################


@router.post('/{id}/files/batch/add', response_model=KnowledgeFilesResponse | None)
async def add_files_to_knowledge_batch(
    request: Request,
    id: str,
    form_data: list[KnowledgeFileIdForm],
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Add multiple files to a knowledge base
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()

    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Batch-fetch all files to avoid N+1 queries
    log.info(f'files/batch/add - {len(form_data)} files')
    file_ids = [form.file_id for form in form_data]
    files = await Files.get_files_by_ids(file_ids, db=db)

    # Verify all requested files were found
    found_ids = {file.id for file in files}
    missing_ids = [fid for fid in file_ids if fid not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'File {missing_ids[0]} not found',
        )

    # Per-file read-access check — same gate as the single-file endpoint.
    if user.role != 'admin':
        for file in files:
            if file.user_id != user.id and not await has_access_to_file(file.id, 'read', user, db=db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )

    # Filter out files already linked to this knowledge base to prevent
    # duplicate embeddings in the vector DB (issue #10679).
    new_entries = []
    for form in form_data:
        if not await Knowledges.has_file(knowledge_id=id, file_id=form.file_id, db=db):
            new_entries.append(form)

    if not new_entries:
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )

    # Narrow the file list to only new files for processing
    new_file_ids = {form.file_id for form in new_entries}
    files = [f for f in files if f.id in new_file_ids]

    # Process files
    try:
        result = await process_files_batch(
            request=request,
            form_data=BatchProcessFilesForm(files=files, collection_name=id),
            user=user,
            db=db,
        )
    except Exception as e:
        log.error(f'add_files_to_knowledge_batch: Exception occurred: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Only add files that were successfully processed
    successful_file_ids = [r.file_id for r in result.results if r.status == 'completed']
    dir_map = {form.file_id: form.directory_id for form in new_entries}
    for file_id in successful_file_ids:
        await Knowledges.add_file_to_knowledge_by_id(
            knowledge_id=id,
            file_id=file_id,
            user_id=user.id,
            directory_id=dir_map.get(file_id),
            db=db,
        )

    # If there were any errors, include them in the response
    if result.errors:
        error_details = [f'{err.file_id}: {err.error}' for err in result.errors]
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
            warnings={
                'message': 'Some files failed to process',
                'errors': error_details,
            },
        )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
    )


############################
# ExportKnowledgeById
############################


@router.get('/{id}/export')
async def export_knowledge_by_id(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    """
    Export a knowledge base as a zip file containing .txt files.
    Admin only.
    """

    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()

    files = await Knowledges.get_files_by_id(id, db=db)

    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            content = file.data.get('content', '') if file.data else ''
            if content:
                # Use original filename with .txt extension
                filename = file.filename
                if not filename.endswith('.txt'):
                    filename = f'{filename}.txt'
                zf.writestr(filename, content)

    zip_buffer.seek(0)

    # Sanitize knowledge name for filename
    safe_name = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in knowledge.name)
    zip_filename = f'{safe_name}.zip'

    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(zip_filename, safe='')}"},
    )


############################
# Directory endpoints
############################


class KnowledgeDirectoryCreateForm(BaseModel):
    name: str
    parent_id: Optional[str] = None


class KnowledgeDirectoryUpdateForm(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = '__unset__'


class KnowledgeFileMoveForm(BaseModel):
    file_id: str
    directory_id: Optional[str] = None


async def _verify_knowledge_write_access(id: str, user, db: AsyncSession):
    """Verify the user has write access to the knowledge base. Returns the knowledge model."""
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if is_external_knowledge(knowledge):
        external_knowledge_error()
    if (
        knowledge.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='knowledge',
            resource_id=knowledge.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return knowledge


@router.post('/{id}/dirs/create', response_model=KnowledgeDirectoryModel)
async def create_knowledge_directory(
    request: Request,
    id: str,
    form_data: KnowledgeDirectoryCreateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _verify_knowledge_write_access(id, user, db)

    directory = await Knowledges.create_directory(
        knowledge_id=id,
        name=form_data.name,
        user_id=user.id,
        parent_id=form_data.parent_id,
        db=db,
    )
    if not directory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to create directory. A directory with this name may already exist at this level.',
        )
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_DIRECTORY_CREATED,
        actor=user,
        subject_id=directory.id,
        data={'knowledge_id': id, 'name': directory.name, 'parent_id': directory.parent_id},
    )
    return directory


@router.post('/{id}/dirs/{dir_id}/update', response_model=KnowledgeDirectoryModel)
async def update_knowledge_directory(
    request: Request,
    id: str,
    dir_id: str,
    form_data: KnowledgeDirectoryUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _verify_knowledge_write_access(id, user, db)

    # Verify directory belongs to this knowledge base
    directory = await Knowledges.get_directory_by_id(dir_id, db=db)
    if not directory or directory.knowledge_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    result = await Knowledges.update_directory(
        directory_id=dir_id,
        name=form_data.name,
        parent_id=form_data.parent_id,
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to update directory. This may be caused by a naming conflict or circular move.',
        )
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_DIRECTORY_UPDATED,
        actor=user,
        subject_id=result.id,
        data={'knowledge_id': id, 'name': result.name, 'parent_id': result.parent_id},
    )
    return result


@router.delete('/{id}/dirs/{dir_id}/delete')
async def delete_knowledge_directory(
    request: Request,
    id: str,
    dir_id: str,
    move_files: bool = Query(True, description='If true, move contained files to parent. If false, delete them.'),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _verify_knowledge_write_access(id, user, db)

    # Verify directory belongs to this knowledge base
    directory = await Knowledges.get_directory_by_id(dir_id, db=db)
    if not directory or directory.knowledge_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    success = await Knowledges.delete_directory(
        directory_id=dir_id,
        move_files_to_parent=move_files,
        db=db,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to delete directory.',
        )
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_DIRECTORY_DELETED,
        actor=user,
        subject_id=dir_id,
        data={'knowledge_id': id, 'move_files': move_files},
    )
    return {'status': True}


@router.post('/{id}/file/move')
async def move_file_in_knowledge(
    request: Request,
    id: str,
    form_data: KnowledgeFileMoveForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _verify_knowledge_write_access(id, user, db)

    # Verify file belongs to this knowledge base
    if not await Knowledges.has_file(knowledge_id=id, file_id=form_data.file_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # If target directory is set, verify it belongs to this knowledge base
    if form_data.directory_id:
        directory = await Knowledges.get_directory_by_id(form_data.directory_id, db=db)
        if not directory or directory.knowledge_id != id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Target directory not found.',
            )

    success = await Knowledges.move_file_to_directory(
        knowledge_id=id,
        file_id=form_data.file_id,
        directory_id=form_data.directory_id,
        db=db,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to move file.',
        )
    await publish_event(
        request,
        EVENTS.KNOWLEDGE_FILE_MOVED,
        actor=user,
        subject_id=form_data.file_id,
        data={'knowledge_id': id, 'directory_id': form_data.directory_id},
    )
    return {'status': True}

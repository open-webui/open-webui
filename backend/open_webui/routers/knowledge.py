from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse

import logging
import io
import zipfile
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import get_async_session
from open_webui.models.groups import Groups
from open_webui.models.knowledge import (
    KnowledgeFileListResponse,
    Knowledges,
    KnowledgeForm,
    KnowledgeResponse,
    KnowledgeUserResponse,
)
from open_webui.models.files import Files, FileModel, FileMetadataResponse
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.routers.retrieval import (
    process_file,
    ProcessFileForm,
    process_files_batch,
    BatchProcessFilesForm,
    get_namespace_for_collection,
)
from open_webui.storage.provider import Storage

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.utils.access_control import has_permission, filter_allowed_access_grants
from open_webui.utils.access_control.files import has_access_to_file
from open_webui.models.access_grants import AccessGrants


from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.models.models import Models, ModelForm

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
    write_access: Optional[bool] = False


class KnowledgeAccessListResponse(BaseModel):
    items: list[KnowledgeAccessResponse]
    total: int


@router.get('/', response_model=KnowledgeAccessListResponse)
async def get_knowledge_bases(
    page: Optional[int] = 1,
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
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    page: Optional[int] = 1,
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
    query: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    page = max(page, 1)
    limit = PAGE_ITEM_COUNT
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query

    groups = await Groups.get_groups_by_member_id(user.id, db=db)
    if groups:
        filter['group_ids'] = [group.id for group in groups]

    filter['user_id'] = user.id

    return await Knowledges.search_knowledge_files(filter=filter, skip=skip, limit=limit, db=db)


############################
# CreateNewKnowledge
############################


@router.post('/create', response_model=Optional[KnowledgeResponse])
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
        user.id, 'workspace.knowledge', request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        request.app.state.config.USER_PERMISSIONS,
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

    log.info(f'Starting reindexing for {len(knowledge_bases)} knowledge bases')

    for knowledge_base in knowledge_bases:
        try:
            files = await Knowledges.get_files_by_id(knowledge_base.id, db=db)
            try:
                # Delete main collection namespace
                namespace = get_namespace_for_collection(knowledge_base.id)
                if VECTOR_DB_CLIENT.has_collection(collection_name=knowledge_base.id, namespace=namespace):
                    VECTOR_DB_CLIENT.delete_collection(
                        collection_name=knowledge_base.id,
                        namespace=namespace,
                    )

                # Delete individual file namespaces during reindex
                if file_ids:
                    log.info(
                        f'Reindexing: Deleting {len(file_ids)} file namespaces for knowledge base {knowledge_base.id}'
                    )
                    for file_id in file_ids:
                        try:
                            file_collection = f'file-{file_id}'
                            file_namespace = get_namespace_for_collection(
                                file_collection, parent_collection_name=knowledge_base.id
                            )

                            if VECTOR_DB_CLIENT.has_collection(
                                collection_name=file_collection, namespace=file_namespace
                            ):
                                VECTOR_DB_CLIENT.delete_collection(
                                    collection_name=file_collection, namespace=file_namespace
                                )
                                log.debug(f'Deleted file namespace: {file_namespace}')
                        except Exception as file_error:
                            log.error(f'Error deleting file namespace for {file_id}: {file_error}')
            except Exception as e:
                log.error(f'Error deleting collection {knowledge_base.id}: {str(e)}')
                continue  # Skip, don't raise

            failed_files = []
            for file in files:
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
            log.warning(f'Failed to process {len(failed_files)} files in knowledge base {knowledge_base.id}')
            for failed in failed_files:
                log.warning(f'File ID: {failed["file_id"]}, Error: {failed["error"]}')

    log.info(f'Reindexing completed.')
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
# GetKnowledgeById
############################


class KnowledgeFilesResponse(KnowledgeResponse):
    files: Optional[list[FileMetadataResponse]] = None
    write_access: Optional[bool] = False


@router.get('/{id}', response_model=Optional[KnowledgeFilesResponse])
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


@router.post('/{id}/update', response_model=Optional[KnowledgeFilesResponse])
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
        request.app.state.config.USER_PERMISSIONS,
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
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id),
        )
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


@router.post('/{id}/access/update', response_model=Optional[KnowledgeFilesResponse])
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
        request.app.state.config.USER_PERMISSIONS,
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_knowledge',
    )

    knowledge.access_grants = await AccessGrants.set_access_grants('knowledge', id, form_data.access_grants, db=db)

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=await Knowledges.get_file_metadatas_by_id(id, db=db),
    )


############################
# GetKnowledgeFilesById
############################


@router.get('/{id}/files', response_model=KnowledgeFileListResponse)
async def get_knowledge_files_by_id(
    id: str,
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
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

    limit = 30
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if view_option:
        filter['view_option'] = view_option
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    return await Knowledges.search_files_by_id(id, user.id, filter=filter, skip=skip, limit=limit, db=db)


############################
# AddFileToKnowledge
############################


class KnowledgeFileIdForm(BaseModel):
    file_id: str


@router.post('/{id}/file/add', response_model=Optional[KnowledgeFilesResponse])
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
        await Knowledges.add_file_to_knowledge_by_id(knowledge_id=id, file_id=form_data.file_id, user_id=user.id, db=db)
    except Exception as e:
        log.debug(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if knowledge:
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post('/{id}/file/update', response_model=Optional[KnowledgeFilesResponse])
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
    namespace = get_namespace_for_collection(knowledge.id)
    VECTOR_DB_CLIENT.delete(
        collection_name=knowledge.id,
        filter={'file_id': form_data.file_id},
        namespace=namespace,
    )

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
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# RemoveFileFromKnowledge
############################


@router.post('/{id}/file/remove', response_model=Optional[KnowledgeFilesResponse])
async def remove_file_from_knowledge_by_id(
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
        namespace = get_namespace_for_collection(knowledge.id)
        log.info(f'Attempting to delete vectors for file_id: {form_data.file_id} from collection: {knowledge.id}')

        # Delete by file_id with namespace support
        VECTOR_DB_CLIENT.delete(
            collection_name=knowledge.id,
            filter={'file_id': form_data.file_id},
            namespace=namespace,
        )

        # Also delete by hash in case of duplicates
        VECTOR_DB_CLIENT.delete(
            collection_name=knowledge.id,
            filter={'hash': file.hash},
            namespace=namespace,
        )
        log.info(f'Successfully deleted vectors for file_id: {form_data.file_id}')
    except Exception as e:
        log.error(f'Error deleting vectors for file_id {form_data.file_id}: {e}')
        log.debug('This was most likely caused by bypassing embedding processing')
        pass

    # Only the file owner or an admin may permanently delete the underlying
    # file.  Collaborators with KB write access can unlink a file from the
    # knowledge base but must not be able to destroy files they do not own,
    # as the same file may be referenced by other KBs and chats.
    if delete_file and (file.user_id == user.id or user.role == 'admin'):
        try:
            # Remove the file's collection from vector database
            file_collection = f'file-{form_data.file_id}'
            file_namespace = get_namespace_for_collection(file_collection)
            if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection, namespace=file_namespace):
                VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection, namespace=file_namespace)
        except Exception as e:
            log.debug('This was most likely caused by bypassing embedding processing')
            log.debug(e)
            pass

        # Delete file from database
        await Files.delete_file_by_id(form_data.file_id, db=db)

    if knowledge:
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=await Knowledges.get_file_metadatas_by_id(knowledge.id, db=db),
        )
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
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
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
    try:
        # Delete main collection namespace
        namespace = get_namespace_for_collection(id)
        log.info(f'Attempting to delete vector collection: {id}')

        if VECTOR_DB_CLIENT.has_collection(collection_name=id, namespace=namespace):
            VECTOR_DB_CLIENT.delete_collection(collection_name=id, namespace=namespace)
            log.info(f'Successfully deleted vector collection: {id}')
        else:
            log.warning(f'Vector collection {id} does not exist, skipping deletion')

        # Delete individual file namespaces (each file gets its own namespace
        # like "fosd-file-abc123" for standalone access)
        file_ids = knowledge.data.get('file_ids', []) if knowledge.data else []
        if file_ids:
            log.info(f'Deleting {len(file_ids)} individual file namespaces for knowledge base {id}')

            for file_id in file_ids:
                try:
                    file_collection = f'file-{file_id}'
                    file_namespace = get_namespace_for_collection(file_collection, parent_collection_name=id)

                    if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection, namespace=file_namespace):
                        VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection, namespace=file_namespace)
                        log.info(f'Deleted file namespace: {file_namespace}')
                    else:
                        log.debug(f'File namespace {file_namespace} does not exist, skipping')
                except Exception as file_error:
                    log.error(f'Error deleting file namespace for {file_id}: {file_error}')
    except Exception as e:
        log.error(f"Error deleting vector collection {id}: {e}")
        # Don't pass silently - this is important for cleanup
        # But don't fail the entire operation if vector cleanup fails

    # Remove knowledge base embedding
    await remove_knowledge_base_metadata_embedding(id)

    result = await Knowledges.delete_knowledge_by_id(id=id, db=db)
    return result


############################
# ResetKnowledgeById
############################


@router.post('/{id}/reset', response_model=Optional[KnowledgeResponse])
async def reset_knowledge_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
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

    try:
        # Delete main collection namespace
        namespace = get_namespace_for_collection(id)
        log.info(f'Attempting to reset vector collection: {id}')

        if VECTOR_DB_CLIENT.has_collection(collection_name=id, namespace=namespace):
            VECTOR_DB_CLIENT.delete_collection(collection_name=id, namespace=namespace)
            log.info(f'Successfully reset vector collection: {id}')
        else:
            log.warning(f'Vector collection {id} does not exist, skipping reset')

        # Delete individual file namespaces
        file_ids = knowledge.data.get('file_ids', []) if knowledge.data else []
        if file_ids:
            log.info(f'Resetting {len(file_ids)} individual file namespaces for knowledge base {id}')

            for file_id in file_ids:
                try:
                    file_collection = f'file-{file_id}'
                    file_namespace = get_namespace_for_collection(file_collection, parent_collection_name=id)

                    if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection, namespace=file_namespace):
                        VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection, namespace=file_namespace)
                        log.info(f'Deleted file namespace: {file_namespace}')
                    else:
                        log.debug(f'File namespace {file_namespace} does not exist, skipping')
                except Exception as file_error:
                    log.error(f'Error deleting file namespace for {file_id}: {file_error}')
    except Exception as e:
        log.error(f"Error resetting vector collection {id}: {e}")
        # Don't pass silently - this is important for cleanup
        # But don't fail the entire operation if vector cleanup fails

    knowledge = await Knowledges.reset_knowledge_by_id(id=id, db=db)
    return knowledge


############################
# AddFilesToKnowledge
############################


@router.post('/{id}/files/batch/add', response_model=Optional[KnowledgeFilesResponse])
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
    for file_id in successful_file_ids:
        await Knowledges.add_file_to_knowledge_by_id(knowledge_id=id, file_id=file_id, user_id=user.id, db=db)

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
    # ASCII-safe fallback for the basic filename parameter (latin-1 safe)
    safe_name = ''.join(c if c.isascii() and (c.isalnum() or c in ' -_') else '_' for c in knowledge.name)
    zip_filename = f'{safe_name}.zip'

    # Use RFC 5987 filename* for non-ASCII names so the browser gets the real name
    quoted_name = quote(f'{knowledge.name}.zip')
    content_disposition = f'attachment; filename="{zip_filename}"; filename*=UTF-8\'\'{quoted_name}'

    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={'Content-Disposition': content_disposition},
    )


############################
# Google Drive Integration
############################


from open_webui.models.knowledge_drive import (
    KnowledgeDriveSources,
    KnowledgeDriveFiles,
    KnowledgeDriveSourceForm,
    KnowledgeDriveSourceResponse,
    KnowledgeDriveSourceModel,
)


class DriveSourcesResponse(BaseModel):
    """Response containing list of Drive sources for a Knowledge base"""

    sources: List[KnowledgeDriveSourceResponse]


class DriveSyncResponse(BaseModel):
    """Response for Drive sync operation"""

    status: str
    message: str
    source_id: Optional[str] = None


############################
# GetDriveSources
############################


@router.get("/{id}/drive/sources", response_model=DriveSourcesResponse)
async def get_drive_sources(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get all Google Drive sources connected to a Knowledge base.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access
    if (
        knowledge.user_id != user.id
        and not await has_access(user.id, "read", knowledge.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    sources = KnowledgeDriveSources.get_drive_sources_by_knowledge_id(id)

    return DriveSourcesResponse(
        sources=[
            KnowledgeDriveSourceResponse(
                id=s.id,
                knowledge_id=s.knowledge_id,
                drive_folder_id=s.drive_folder_id,
                drive_folder_name=s.drive_folder_name,
                drive_folder_path=s.drive_folder_path,
                shared_drive_id=s.shared_drive_id,
                recursive=s.recursive,
                sync_status=s.sync_status,
                sync_enabled=s.sync_enabled,
                last_sync_timestamp=s.last_sync_timestamp,
                last_sync_file_count=s.last_sync_file_count,
                error_count=s.error_count,
                last_error=s.last_error,
                created_at=s.created_at,
            )
            for s in sources
        ]
    )


############################
# ConnectDriveFolder
############################


@router.post("/{id}/drive/connect", response_model=KnowledgeDriveSourceResponse)
async def connect_drive_folder(
    request: Request,
    id: str,
    form_data: KnowledgeDriveSourceForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Connect a Google Drive folder to a Knowledge base.

    The folder will be synced automatically based on the configured interval.
    Requires user to have Google OAuth with Drive scope.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if (
        knowledge.user_id != user.id
        and not await has_access(user.id, "write", knowledge.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Verify user has Google Drive access
    from open_webui.utils.google_drive_client import create_drive_client_for_user

    drive_client = await create_drive_client_for_user(
        request.app.state.oauth_manager,
        user.id,
    )

    if not drive_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Drive access not available. Please log out and log back in with Google to grant Drive permissions, or check that your admin has enabled Drive scope in OAuth settings.",
        )

    # Verify folder access
    try:
        folder_info = await drive_client.get_folder_info(form_data.drive_folder_id)
        # Update form with folder name if not provided
        if not form_data.drive_folder_name:
            form_data.drive_folder_name = folder_info.name
        # Store Shared Drive ID if present (needed for API calls)
        if folder_info.drive_id:
            form_data.shared_drive_id = folder_info.drive_id
            log.info(f"Folder is in Shared Drive: {folder_info.drive_id}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot access Drive folder: {str(e)}",
        )
    finally:
        await drive_client.close()

    # Check if folder is already connected
    existing_sources = KnowledgeDriveSources.get_drive_sources_by_knowledge_id(id)
    for source in existing_sources:
        if source.drive_folder_id == form_data.drive_folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This folder is already connected to this Knowledge base.",
            )

    # Create drive source
    source = KnowledgeDriveSources.create_drive_source(
        knowledge_id=id,
        user_id=user.id,
        form_data=form_data,
    )

    if not source:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect Drive folder.",
        )

    log.info(
        f"Connected Drive folder {form_data.drive_folder_id} to knowledge {id} "
        f"(source: {source.id}, recursive={source.recursive})"
    )

    return KnowledgeDriveSourceResponse(
        id=source.id,
        knowledge_id=source.knowledge_id,
        drive_folder_id=source.drive_folder_id,
        drive_folder_name=source.drive_folder_name,
        drive_folder_path=source.drive_folder_path,
        shared_drive_id=source.shared_drive_id,
        recursive=source.recursive,
        sync_status=source.sync_status,
        sync_enabled=source.sync_enabled,
        last_sync_timestamp=source.last_sync_timestamp,
        last_sync_file_count=source.last_sync_file_count,
        error_count=source.error_count,
        last_error=source.last_error,
        created_at=source.created_at,
    )


############################
# DisconnectDriveFolder
############################


@router.delete("/{id}/drive/sources/{source_id}", response_model=bool)
async def disconnect_drive_folder(
    id: str,
    source_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Disconnect a Google Drive folder from a Knowledge base.

    This removes the sync connection but does not delete files already synced.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if (
        knowledge.user_id != user.id
        and not await has_access(user.id, "write", knowledge.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Verify source exists and belongs to this knowledge
    source = KnowledgeDriveSources.get_drive_source_by_id(source_id)
    if not source or source.knowledge_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive source not found.",
        )

    # Delete source (also deletes tracked files)
    result = KnowledgeDriveSources.delete_drive_source(source_id)

    log.info(f"Disconnected Drive source {source_id} from knowledge {id}")

    return result


############################
# SyncDriveSource
############################


@router.post("/{id}/drive/sources/{source_id}/sync", response_model=DriveSyncResponse)
async def sync_drive_source(
    request: Request,
    id: str,
    source_id: str,
    force_full: bool = Query(False, description="Force full sync instead of incremental"),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Manually trigger a sync for a Drive source.

    By default, performs incremental sync (only changed files).
    Set force_full=true to resync all files.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if (
        knowledge.user_id != user.id
        and not await has_access(user.id, "write", knowledge.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Verify source exists
    source = KnowledgeDriveSources.get_drive_source_by_id(source_id)
    if not source or source.knowledge_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive source not found.",
        )

    # Check if sync is already running
    if source.sync_status == "active":
        return DriveSyncResponse(
            status="already_running",
            message="Sync is already in progress for this source.",
            source_id=source_id,
        )

    # Trigger sync in background
    from open_webui.utils.knowledge_drive_sync import sync_knowledge_drive_source
    from open_webui.tasks import create_task

    try:
        task_id, _ = await create_task(
            request.app.state.redis,
            sync_knowledge_drive_source(
                source_id,
                request.app.state,
                force_full_sync=force_full,
            ),
            id=f"drive_sync_{source_id}",
        )

        log.info(f"Started Drive sync task {task_id} for source {source_id}")

        return DriveSyncResponse(
            status="started",
            message="Sync started. Check source status for progress.",
            source_id=source_id,
        )

    except Exception as e:
        log.error(f"Failed to start Drive sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync: {str(e)}",
        )


############################
# SyncAllDriveSources
############################


@router.post("/{id}/drive/sync", response_model=DriveSyncResponse)
async def sync_all_drive_sources(
    request: Request,
    id: str,
    force_full: bool = Query(False, description="Force full sync instead of incremental"),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Trigger sync for all Drive sources connected to a Knowledge base.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if (
        knowledge.user_id != user.id
        and not await has_access(user.id, "write", knowledge.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    sources = KnowledgeDriveSources.get_drive_sources_by_knowledge_id(id)

    if not sources:
        return DriveSyncResponse(
            status="no_sources",
            message="No Drive sources connected to this Knowledge base.",
        )

    # Trigger sync for all sources
    from open_webui.utils.knowledge_drive_sync import trigger_drive_sync_for_knowledge
    from open_webui.tasks import create_task

    try:
        task_id, _ = await create_task(
            request.app.state.redis,
            trigger_drive_sync_for_knowledge(
                id,
                request.app.state,
                force_full_sync=force_full,
            ),
            id=f"drive_sync_knowledge_{id}",
        )

        log.info(f"Started Drive sync task {task_id} for knowledge {id}")

        return DriveSyncResponse(
            status="started",
            message=f"Sync started for {len(sources)} source(s).",
        )

    except Exception as e:
        log.error(f"Failed to start Drive sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync: {str(e)}",
        )


############################
# UpdateDriveSource
############################


class DriveSourceUpdateForm(BaseModel):
    sync_enabled: Optional[bool] = None
    recursive: Optional[bool] = None
    auto_sync_interval_hours: Optional[int] = None


@router.post("/{id}/drive/sources/{source_id}/update", response_model=KnowledgeDriveSourceResponse)
async def update_drive_source(
    id: str,
    source_id: str,
    form_data: DriveSourceUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update settings for a Drive source.
    """
    knowledge = await Knowledges.get_knowledge_by_id(id=id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if (
        knowledge.user_id != user.id
        and not await has_access(user.id, "write", knowledge.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Verify source exists
    source = KnowledgeDriveSources.get_drive_source_by_id(source_id)
    if not source or source.knowledge_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive source not found.",
        )

    # Build updates
    updates = {}
    if form_data.sync_enabled is not None:
        updates["sync_enabled"] = form_data.sync_enabled
    if form_data.recursive is not None:
        updates["recursive"] = form_data.recursive
    if form_data.auto_sync_interval_hours is not None:
        updates["auto_sync_interval_hours"] = form_data.auto_sync_interval_hours

    if updates:
        source = KnowledgeDriveSources.update_drive_source(source_id, **updates)

    return KnowledgeDriveSourceResponse(
        id=source.id,
        knowledge_id=source.knowledge_id,
        drive_folder_id=source.drive_folder_id,
        drive_folder_name=source.drive_folder_name,
        drive_folder_path=source.drive_folder_path,
        shared_drive_id=source.shared_drive_id,
        recursive=source.recursive,
        sync_status=source.sync_status,
        sync_enabled=source.sync_enabled,
        last_sync_timestamp=source.last_sync_timestamp,
        last_sync_file_count=source.last_sync_file_count,
        error_count=source.error_count,
        last_error=source.last_error,
        created_at=source.created_at,
    )

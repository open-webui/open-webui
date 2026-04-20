import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.clients.memories import (
    AddMemoryForm,
    MemoryUpdateModel,
    QueryMemoryForm,
)
from open_webui.clients.memories import (
    add_memory as _client_add_memory,
)
from open_webui.clients.memories import (
    query_memory as _client_query_memory,
)
from open_webui.clients.memories import (
    update_memory_by_id as _client_update_memory_by_id,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.memories import Memories, MemoryModel
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


############################
# GetMemories
# Let what is remembered here spare someone the cost
# of learning it twice.
############################


@router.get('/', response_model=list[MemoryModel])
async def get_memories(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[MemoryModel]:
    if not request.app.state.config.ENABLE_MEMORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not await has_permission(user.id, 'features.memories', request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return await Memories.get_memories_by_user_id(user.id, db=db)


############################
# AddMemory
############################


@router.post('/add', response_model=MemoryModel | None)
async def add_memory(
    request: Request,
    form_data: AddMemoryForm,
    user=Depends(get_verified_user),
) -> MemoryModel | None:
    return await _client_add_memory(request, form_data, user)


############################
# QueryMemory
############################


@router.post('/query')
async def query_memory(
    request: Request,
    form_data: QueryMemoryForm,
    user=Depends(get_verified_user),
):
    return await _client_query_memory(request, form_data, user)


############################
# ResetMemoryFromVectorDB
############################
@router.post('/reset', response_model=bool)
async def reset_memory_from_vector_db(
    request: Request,
    user=Depends(get_verified_user),
) -> bool:
    """Reset user's memory vector embeddings.

    CRITICAL: We intentionally do NOT use Depends(get_async_session) here.
    This endpoint generates embeddings for ALL user memories in parallel using
    asyncio.gather(). A user with 100 memories would trigger 100 embedding API
    calls simultaneously. With a session held, this could block a connection
    for MINUTES, completely exhausting the connection pool.
    """
    if not request.app.state.config.ENABLE_MEMORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not await has_permission(user.id, 'features.memories', request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    await ASYNC_VECTOR_DB_CLIENT.delete_collection(f'user-memory-{user.id}')

    memories = await Memories.get_memories_by_user_id(user.id)

    # Generate vectors in parallel
    vectors = await asyncio.gather(
        *[request.app.state.EMBEDDING_FUNCTION(memory.content, user=user) for memory in memories]
    )

    await ASYNC_VECTOR_DB_CLIENT.upsert(
        collection_name=f'user-memory-{user.id}',
        items=[
            {
                'id': memory.id,
                'text': memory.content,
                'vector': vectors[idx],
                'metadata': {
                    'created_at': memory.created_at,
                    'updated_at': memory.updated_at,
                },
            }
            for idx, memory in enumerate(memories)
        ],
    )

    return True


############################
# DeleteMemoriesByUserId
############################


@router.delete('/delete/user', response_model=bool)
async def delete_memory_by_user_id(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
) -> bool:
    if not request.app.state.config.ENABLE_MEMORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not await has_permission(user.id, 'features.memories', request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = await Memories.delete_memories_by_user_id(user.id, db=db)

    if result:
        try:
            await ASYNC_VECTOR_DB_CLIENT.delete_collection(f'user-memory-{user.id}')
        except Exception as e:
            log.error(e)
        return True

    return False


############################
# UpdateMemoryById
############################


@router.post('/{memory_id}/update', response_model=MemoryModel | None)
async def update_memory_by_id(
    memory_id: str,
    request: Request,
    form_data: MemoryUpdateModel,
    user=Depends(get_verified_user),
) -> MemoryModel | None:
    return await _client_update_memory_by_id(memory_id, request, form_data, user)


############################
# DeleteMemoryById
############################


@router.delete('/{memory_id}', response_model=bool)
async def delete_memory_by_id(
    memory_id: str,
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
) -> bool:
    if not request.app.state.config.ENABLE_MEMORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not await has_permission(user.id, 'features.memories', request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = await Memories.delete_memory_by_id_and_user_id(memory_id, user.id, db=db)

    if result:
        await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=f'user-memory-{user.id}', ids=[memory_id])
        return True

    return False

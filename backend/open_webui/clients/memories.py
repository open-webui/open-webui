import logging
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.models.memories import Memories, MemoryModel
from open_webui.models.users import UserModel
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.utils.access_control import has_permission

log = logging.getLogger(__name__)


class AddMemoryForm(BaseModel):
    content: str


class MemoryUpdateModel(BaseModel):
    content: str | None = None


class QueryMemoryForm(BaseModel):
    content: str
    k: int | None = 1


def _ensure_memories_enabled_for(request: Request, user: UserModel) -> None:
    if not request.app.state.config.ENABLE_MEMORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


async def _ensure_user_can_use_memories(request: Request, user: UserModel) -> None:
    _ensure_memories_enabled_for(request, user)
    if not await has_permission(user.id, 'features.memories', request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


async def add_memory(
    request: Request,
    form_data: AddMemoryForm,
    user: UserModel,
) -> MemoryModel | None:
    """Insert a user memory and upsert its embedding.

    NOTE: This intentionally does NOT take a `Depends(get_async_session)` session.
    `insert_new_memory` manages its own short-lived session so we don't hold a
    DB connection while awaiting `EMBEDDING_FUNCTION` (external API call,
    1-5+ seconds).
    """
    await _ensure_user_can_use_memories(request, user)

    memory = await Memories.insert_new_memory(user.id, form_data.content)
    vector = await request.app.state.EMBEDDING_FUNCTION(memory.content, user=user)

    await ASYNC_VECTOR_DB_CLIENT.upsert(
        collection_name=f'user-memory-{user.id}',
        items=[
            {
                'id': memory.id,
                'text': memory.content,
                'vector': vector,
                'metadata': {'created_at': memory.created_at},
            }
        ],
    )
    return memory


async def query_memory(
    request: Request,
    form_data: QueryMemoryForm,
    user: UserModel,
) -> Any:
    """Semantic-search a user's memories.

    NOTE: This intentionally does NOT take a `Depends(get_async_session)` session.
    `get_memories_by_user_id` manages its own short-lived session so we don't
    hold a DB connection while awaiting `EMBEDDING_FUNCTION` (external API call,
    1-5+ seconds).
    """
    await _ensure_user_can_use_memories(request, user)

    memories = await Memories.get_memories_by_user_id(user.id)
    if not memories:
        raise HTTPException(status_code=404, detail='No memories found for user')

    vector = await request.app.state.EMBEDDING_FUNCTION(form_data.content, user=user)

    results = await ASYNC_VECTOR_DB_CLIENT.search(
        collection_name=f'user-memory-{user.id}',
        vectors=[vector],
        limit=form_data.k,
    )

    relevance_threshold = getattr(request.app.state.config, 'RELEVANCE_THRESHOLD', 0.0)
    if results and relevance_threshold > 0.0 and results.distances and results.distances[0]:
        results = _filter_by_relevance(results, relevance_threshold)

    return results


def _filter_by_relevance(results: Any, threshold: float) -> Any:
    from open_webui.retrieval.vector.main import SearchResult

    filtered_ids: list[str] = []
    filtered_docs: list[str] = []
    filtered_metas: list[dict[str, Any]] = []
    filtered_dists: list[float] = []

    for idx, score in enumerate(results.distances[0]):
        if score < threshold:
            continue
        if results.ids and results.ids[0]:
            filtered_ids.append(results.ids[0][idx])
        if results.documents and results.documents[0]:
            filtered_docs.append(results.documents[0][idx])
        if results.metadatas and results.metadatas[0]:
            filtered_metas.append(results.metadatas[0][idx])
        filtered_dists.append(score)

    return SearchResult(
        ids=[filtered_ids] if filtered_ids else [[]],
        documents=[filtered_docs] if filtered_docs else [[]],
        metadatas=[filtered_metas] if filtered_metas else [[]],
        distances=[filtered_dists] if filtered_dists else [[]],
    )


async def update_memory_by_id(
    memory_id: str,
    request: Request,
    form_data: MemoryUpdateModel,
    user: UserModel,
) -> MemoryModel | None:
    """Update a memory and re-embed if content changed.

    NOTE: This intentionally does NOT take a `Depends(get_async_session)` session.
    `update_memory_by_id_and_user_id` manages its own short-lived session so we
    don't hold a DB connection while awaiting `EMBEDDING_FUNCTION` (external API
    call, 1-5+ seconds).
    """
    await _ensure_user_can_use_memories(request, user)

    memory = await Memories.update_memory_by_id_and_user_id(memory_id, user.id, form_data.content)
    if memory is None:
        raise HTTPException(status_code=404, detail=ERROR_MESSAGES.NOT_FOUND)

    if form_data.content is not None:
        vector = await request.app.state.EMBEDDING_FUNCTION(memory.content, user=user)
        await ASYNC_VECTOR_DB_CLIENT.upsert(
            collection_name=f'user-memory-{user.id}',
            items=[
                {
                    'id': memory.id,
                    'text': memory.content,
                    'vector': vector,
                    'metadata': {
                        'created_at': memory.created_at,
                        'updated_at': memory.updated_at,
                    },
                }
            ],
        )

    return memory

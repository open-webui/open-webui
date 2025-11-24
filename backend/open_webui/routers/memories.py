from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import logging
import asyncio
from typing import Optional

from open_webui.models.memories import Memories, MemoryModel
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


@router.get("/ef")
async def get_embeddings(request: Request):
    return {"result": await request.app.state.EMBEDDING_FUNCTION("hello world")}


############################
# GetMemories
############################


@router.get("/", response_model=list[MemoryModel])
async def get_memories(user=Depends(get_verified_user)):
    return Memories.get_memories_by_user_id(user.id)


############################
# AddMemory
############################


class AddMemoryForm(BaseModel):
    content: str


class MemoryUpdateModel(BaseModel):
    content: Optional[str] = None


@router.post("/add", response_model=Optional[MemoryModel])
async def add_memory(
    request: Request,
    form_data: AddMemoryForm,
    user=Depends(get_verified_user),
):
    memory = Memories.insert_new_memory(user.id, form_data.content)

    vector = await request.app.state.EMBEDDING_FUNCTION(memory.content, user=user)

    VECTOR_DB_CLIENT.upsert(
        collection_name=f"user-memory-{user.id}",
        items=[
            {
                "id": memory.id,
                "text": memory.content,
                "vector": vector,
                "metadata": {"created_at": memory.created_at},
            }
        ],
    )

    return memory


############################
# QueryMemory
############################


class QueryMemoryForm(BaseModel):
    content: str
    k: Optional[int] = 1


@router.post("/query")
async def query_memory(
    request: Request, form_data: QueryMemoryForm, user=Depends(get_verified_user)
):
    memories = Memories.get_memories_by_user_id(user.id)
    if not memories:
        raise HTTPException(status_code=404, detail="No memories found for user")

    vector = await request.app.state.EMBEDDING_FUNCTION(form_data.content, user=user)

    results = VECTOR_DB_CLIENT.search(
        collection_name=f"user-memory-{user.id}",
        vectors=[vector],
        limit=form_data.k,
    )

    return results


############################
# ResetMemoryFromVectorDB
############################
@router.post("/reset", response_model=bool)
async def reset_memory_from_vector_db(
    request: Request, user=Depends(get_verified_user)
):
    VECTOR_DB_CLIENT.delete_collection(f"user-memory-{user.id}")

    memories = Memories.get_memories_by_user_id(user.id)

    # Generate vectors in parallel
    vectors = await asyncio.gather(
        *[
            request.app.state.EMBEDDING_FUNCTION(memory.content, user=user)
            for memory in memories
        ]
    )

    VECTOR_DB_CLIENT.upsert(
        collection_name=f"user-memory-{user.id}",
        items=[
            {
                "id": memory.id,
                "text": memory.content,
                "vector": vectors[idx],
                "metadata": {
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at,
                },
            }
            for idx, memory in enumerate(memories)
        ],
    )

    return True


############################
# DeleteMemoriesByUserId
############################


@router.delete("/delete/user", response_model=bool)
async def delete_memory_by_user_id(user=Depends(get_verified_user)):
    result = Memories.delete_memories_by_user_id(user.id)

    if result:
        try:
            VECTOR_DB_CLIENT.delete_collection(f"user-memory-{user.id}")
        except Exception as e:
            log.error(e)
        return True

    return False


############################
# UpdateMemoryById
############################


@router.post("/{memory_id}/update", response_model=Optional[MemoryModel])
async def update_memory_by_id(
    memory_id: str,
    request: Request,
    form_data: MemoryUpdateModel,
    user=Depends(get_verified_user),
):
    memory = Memories.update_memory_by_id_and_user_id(
        memory_id, user.id, form_data.content
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if form_data.content is not None:
        vector = await request.app.state.EMBEDDING_FUNCTION(memory.content, user=user)

        VECTOR_DB_CLIENT.upsert(
            collection_name=f"user-memory-{user.id}",
            items=[
                {
                    "id": memory.id,
                    "text": memory.content,
                    "vector": vector,
                    "metadata": {
                        "created_at": memory.created_at,
                        "updated_at": memory.updated_at,
                    },
                }
            ],
        )

    return memory


############################
# DeleteMemoryById
############################


@router.delete("/{memory_id}", response_model=bool)
async def delete_memory_by_id(memory_id: str, user=Depends(get_verified_user)):
    result = Memories.delete_memory_by_id_and_user_id(memory_id, user.id)

    if result:
        VECTOR_DB_CLIENT.delete(
            collection_name=f"user-memory-{user.id}", ids=[memory_id]
        )
        return True

    return False

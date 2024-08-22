import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.documents import Document
from open_webui.apps.rag.vector_store import VECTOR_STORE_CONNECTOR
from open_webui.apps.webui.models.memories import Memories, MemoryModel
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.utils import get_verified_user
from pydantic import BaseModel

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


@router.get("/ef")
async def get_embeddings(request: Request):
    return {"result": request.app.state.EMBEDDING_FUNCTION("hello world")}


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
    # Create documents to ingest to VectorStore
    memory_document = Document(
        page_content=memory.content, metadata={"created_at": memory.created_at}
    )
    VECTOR_STORE_CONNECTOR.vs_class.from_documents(
        documents=[memory_document],
        collection_name=f"user-memory-{user.id}",
        embedding=request.app.state.EMBEDDING_FUNCTION,
        ids=[memory.id],
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
    vector_store = VECTOR_STORE_CONNECTOR.get_vs_collection(
        collection_name=f"user-memory-{user.id}",
        embedding_function=request.app.state.EMBEDDING_FUNCTION,
    )

    list_docs_with_scores = vector_store.similarity_search_with_score(
        query=form_data.content,
        k=form_data.k,
    )
    results = {
        "distances": [[doc_with_score[1] for doc_with_score in list_docs_with_scores]],
        "documents": [
            [doc_with_score[0].page_content for doc_with_score in list_docs_with_scores]
        ],
        "metadatas": [
            [doc_with_score[0].metadata for doc_with_score in list_docs_with_scores]
        ],
    }

    return results


############################
# ResetMemoryFromVectorDB
############################
@router.post("/reset", response_model=bool)
async def reset_memory_from_vector_db(
    request: Request, user=Depends(get_verified_user)
):
    vector_store = VECTOR_STORE_CONNECTOR.get_vs_collection(
        collection_name=f"user-memory-{user.id}",
        embedding_function=request.app.state.EMBEDDING_FUNCTION,
    )
    vector_store.delete_collection()
    memories = Memories.get_memories_by_user_id(user.id)
    # Create documents to ingest to VectorStore
    list_docs = [
        Document(
            page_content=memory.content,
        )
        for memory in memories
    ]
    list_ids = [memory.id for memory in memories]
    if list_docs:
        VECTOR_STORE_CONNECTOR.vs_class.from_documents(
            documents=list_docs,
            collection_name=f"user-memory-{user.id}",
            embedding=request.app.state.EMBEDDING_FUNCTION,
            ids=list_ids,
        )
    return True


############################
# DeleteMemoriesByUserId
############################


@router.delete("/delete/user", response_model=bool)
async def delete_memory_by_user_id(request: Request, user=Depends(get_verified_user)):
    result = Memories.delete_memories_by_user_id(user.id)

    if result:
        try:
            vector_store = VECTOR_STORE_CONNECTOR.get_vs_collection(
                collection_name=f"user-memory-{user.id}",
                embedding_function=request.app.state.EMBEDDING_FUNCTION,
            )
            vector_store.delete_collection()
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
    memory = Memories.update_memory_by_id(memory_id, form_data.content)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if form_data.content is not None:
        memory_document = Document(
            page_content=form_data.content,
            metadata={"created_at": memory.created_at, "updated_at": memory.updated_at},
        )
        VECTOR_STORE_CONNECTOR.vs_class.from_documents(
            documents=[memory_document],
            collection_name=f"user-memory-{user.id}",
            embedding=request.app.state.EMBEDDING_FUNCTION,
            ids=[memory.id],
        )

    return memory


############################
# DeleteMemoryById
############################


@router.delete("/{memory_id}", response_model=bool)
async def delete_memory_by_id(
    request: Request, memory_id: str, user=Depends(get_verified_user)
):
    result = Memories.delete_memory_by_id_and_user_id(memory_id, user.id)

    if result:
        vector_store = VECTOR_STORE_CONNECTOR.get_vs_collection(
            collection_name=f"user-memory-{user.id}",
            embedding_function=request.app.state.EMBEDDING_FUNCTION,
        )
        vector_store.delete(ids=[memory_id])
        return True

    return False

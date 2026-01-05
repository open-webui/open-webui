"""
Built-in tools for Open WebUI.

These tools are automatically available when native function calling is enabled.
"""

import json
import logging
import time
from typing import Optional

from fastapi import Request

from open_webui.models.users import UserModel
from open_webui.routers.retrieval import search_web
from open_webui.retrieval.utils import get_content_from_url
from open_webui.routers.images import image_generations, image_edits, CreateImageForm, EditImageForm
from open_webui.routers.memories import query_memory, add_memory, QueryMemoryForm, AddMemoryForm

log = logging.getLogger(__name__)


async def web_search(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the web for information on a given topic.

    Use this tool when:
    - Information is NOT available in configured knowledge bases (check query_knowledge first!)
    - Looking for current events, real-time information, or recent updates
    - Need information from external/public sources not in local knowledge bases

    :param query: The search query to look up
    :param count: Number of results to return (default: 5)
    :return: JSON with search results containing title, link, and snippet for each result
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        engine = __request__.app.state.config.WEB_SEARCH_ENGINE
        user = UserModel(**__user__) if __user__ else None

        results = search_web(__request__, engine, query, user)

        # Limit results
        results = results[:count] if results else []

        return json.dumps(
            [{"title": r.title, "link": r.link, "snippet": r.snippet} for r in results],
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"web_search error: {e}")
        return json.dumps({"error": str(e)})


async def fetch_url(
    url: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Fetch and extract the main text content from a web page URL.

    :param url: The URL to fetch content from
    :return: The extracted text content from the page
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        content, _ = get_content_from_url(__request__, url)
        
        # Truncate if too long (avoid overwhelming context)
        max_length = 50000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n[Content truncated...]"
        
        return content
    except Exception as e:
        log.exception(f"fetch_url error: {e}")
        return json.dumps({"error": str(e)})


async def generate_image(
    prompt: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Generate an image based on a text prompt.

    :param prompt: A detailed description of the image to generate
    :return: Confirmation that the image was generated, or an error message
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_generations(
            request=__request__,
            form_data=CreateImageForm(prompt=prompt),
            user=user,
        )

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and images:
            await __event_emitter__(
                {
                    "type": "files",
                    "data": {
                        "files": [
                            {"type": "image", "url": img["url"]}
                            for img in images
                        ]
                    },
                }
            )

        return json.dumps({"status": "success", "images": images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f"generate_image error: {e}")
        return json.dumps({"error": str(e)})


async def edit_image(
    prompt: str,
    image_url: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Edit an existing image based on a text prompt.

    :param prompt: A description of the changes to make to the image
    :param image_url: The URL of the image to edit
    :return: Confirmation that the image was edited, or an error message
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_edits(
            request=__request__,
            form_data=EditImageForm(prompt=prompt, image=image_url),
            user=user,
        )

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and images:
            await __event_emitter__(
                {
                    "type": "files",
                    "data": {
                        "files": [
                            {"type": "image", "url": img["url"]}
                            for img in images
                        ]
                    },
                }
            )

        return json.dumps({"status": "success", "images": images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f"edit_image error: {e}")
        return json.dumps({"error": str(e)})


async def memory_query(
    query: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's stored memories for relevant information.

    :param query: The search query to find relevant memories
    :return: JSON with matching memories and their dates
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        results = await query_memory(
            __request__,
            QueryMemoryForm(content=query, k=5),
            user,
        )

        if results and hasattr(results, "documents") and results.documents:
            memories = []
            for doc_idx, doc in enumerate(results.documents[0]):
                created_at = "Unknown"
                if results.metadatas and results.metadatas[0][doc_idx].get("created_at"):
                    created_at = time.strftime(
                        "%Y-%m-%d", time.localtime(results.metadatas[0][doc_idx]["created_at"])
                    )
                memories.append({"date": created_at, "content": doc})
            return json.dumps(memories, ensure_ascii=False)
        else:
            return json.dumps([])
    except Exception as e:
        log.exception(f"memory_query error: {e}")
        return json.dumps({"error": str(e)})


async def memory_add(
    content: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Store a new memory for the user.

    :param content: The memory content to store
    :return: Confirmation that the memory was stored
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await add_memory(
            __request__,
            AddMemoryForm(content=content),
            user,
        )

        return json.dumps({"status": "success", "id": memory.id}, ensure_ascii=False)
    except Exception as e:
        log.exception(f"memory_add error: {e}")
        return json.dumps({"error": str(e)})


async def query_knowledge(
    query: str,
    k: int = 5,
    __request__: Request = None,
    __user__: dict = None,
    __model__: dict = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Search the model's configured knowledge bases for relevant information.

    IMPORTANT: Always check knowledge bases FIRST before using web_search. Knowledge bases contain
    curated, verified information that should be prioritized over web searches.

    :param query: The search query to find relevant documents
    :param k: Maximum number of results to return (default: 5)
    :return: JSON with matching documents, their metadata, and relevance scores
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if __model__ is None:
        return json.dumps({"error": "Model context not available"})

    try:
        # Extract knowledge configuration from model metadata
        model_knowledge = __model__.get("info", {}).get("meta", {}).get("knowledge", [])

        if not model_knowledge:
            return json.dumps({"error": "No knowledge bases configured for this model"})

        # Emit status event
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "knowledge_search",
                        "query": query,
                        "done": False,
                    },
                }
            )

        # Extract collection names from knowledge configuration
        collection_names = []
        for item in model_knowledge:
            if item.get("collection_name"):
                collection_names.append(item.get("collection_name"))
            elif item.get("collection_names"):
                collection_names.extend(item.get("collection_names"))
            elif item.get("id"):  # Direct ID reference
                collection_names.append(item.get("id"))

        if not collection_names:
            return json.dumps(
                {"error": "No valid collection names found in knowledge configuration"}
            )

        user = UserModel(**__user__) if __user__ else None

        # Import here to avoid circular dependency
        from open_webui.retrieval.utils import (
            query_collection,
            query_collection_with_hybrid_search,
        )

        # Use hybrid search if enabled
        if __request__.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            result = await query_collection_with_hybrid_search(
                collection_names=collection_names,
                queries=[query],
                embedding_function=lambda q, prefix: __request__.app.state.EMBEDDING_FUNCTION(
                    q, prefix=prefix, user=user
                ),
                k=k,
                reranking_function=(
                    (
                        lambda q, documents: __request__.app.state.RERANKING_FUNCTION(
                            q, documents, user=user
                        )
                    )
                    if __request__.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=__request__.app.state.config.TOP_K_RERANKER,
                r=__request__.app.state.config.RELEVANCE_THRESHOLD,
                hybrid_bm25_weight=__request__.app.state.config.HYBRID_BM25_WEIGHT,
                enable_enriched_texts=__request__.app.state.config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS,
            )
        else:
            result = await query_collection(
                collection_names=collection_names,
                queries=[query],
                embedding_function=lambda q, prefix: __request__.app.state.EMBEDDING_FUNCTION(
                    q, prefix=prefix, user=user
                ),
                k=k,
            )

        # Emit completion status
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "knowledge_search",
                        "query": query,
                        "done": True,
                    },
                }
            )

        # Format results with only essential metadata
        if result and "documents" in result and result["documents"]:
            documents = []
            for doc_idx, doc in enumerate(result["documents"][0]):
                full_metadata = {}
                if "metadatas" in result and result["metadatas"] and result["metadatas"][0]:
                    full_metadata = (
                        result["metadatas"][0][doc_idx]
                        if doc_idx < len(result["metadatas"][0])
                        else {}
                    )

                # Filter metadata to only essential fields
                filtered_metadata = {}
                if "name" in full_metadata:
                    filtered_metadata["name"] = full_metadata["name"]
                if "page" in full_metadata:
                    filtered_metadata["page"] = full_metadata["page"]
                if "total_pages" in full_metadata:
                    filtered_metadata["total_pages"] = full_metadata["total_pages"]
                if "creationdate" in full_metadata:
                    filtered_metadata["creationdate"] = full_metadata["creationdate"]

                doc_entry = {
                    "content": doc,
                    "metadata": filtered_metadata,
                }

                # Include relevance score if available
                if "distances" in result and result["distances"] and result["distances"][0]:
                    if doc_idx < len(result["distances"][0]):
                        doc_entry["score"] = result["distances"][0][doc_idx]

                documents.append(doc_entry)

            return json.dumps({"documents": documents}, ensure_ascii=False)
        else:
            return json.dumps({"documents": []})

    except Exception as e:
        log.exception(f"query_knowledge error: {e}")
        return json.dumps({"error": str(e)})

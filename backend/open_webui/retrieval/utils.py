import logging
import os
import hashlib
from typing import Any, List, Optional, Sequence, Union
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import requests
from huggingface_hub import snapshot_download
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun, Callbacks
from langchain_core.retrievers import BaseRetriever

from open_webui.config import (
    VECTOR_DB,
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
)
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.models.users import UserModel
from open_webui.models.files import Files
from open_webui.retrieval.vector.main import GetResult
from open_webui.env import (
    SRC_LOG_LEVELS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)

# Configure logging
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", logging.INFO))


class VectorSearchRetriever(BaseRetriever):
    """Retriever that uses vector search to find relevant documents."""
    
    def __init__(self, collection_name: str, embedding_function: Any, top_k: int):
        """Initialize the retriever with collection name, embedding function, and top_k."""
        super().__init__()
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.top_k = top_k

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        """Get documents relevant to the query."""
        result = VECTOR_DB_CLIENT.search(
            collection_name=self.collection_name,
            vectors=[self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)],
            limit=self.top_k,
        )

        return [
            Document(metadata=metadata, page_content=document)
            for metadata, document in zip(result.metadatas[0], result.documents[0])
        ]


class RerankCompressor(BaseDocumentCompressor):
    """Compressor that reranks documents based on relevance to query."""
    
    def __init__(self, embedding_function: Any, top_n: int, reranking_function: Any = None, r_score: float = 0.0):
        """Initialize the compressor with embedding function, top_n, reranking function, and threshold score."""
        super().__init__()
        self.embedding_function = embedding_function
        self.top_n = top_n
        self.reranking_function = reranking_function
        self.r_score = r_score

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """Compress documents by reranking them based on relevance to query."""
        if not documents:
            return []
            
        if self.reranking_function:
            scores = self.reranking_function.predict(
                [(query, doc.page_content) for doc in documents]
            )
        else:
            from sentence_transformers import util
            query_embedding = self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)
            document_embedding = self.embedding_function(
                [doc.page_content for doc in documents], RAG_EMBEDDING_CONTENT_PREFIX
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        # Filter by threshold score if specified
        docs_with_scores = [
            (doc, score) 
            for doc, score in zip(documents, scores.tolist()) 
            if score >= self.r_score
        ]

        # Sort by score and take top_n
        docs_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Create new documents with score in metadata
        return [
            Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "score": score}
            )
            for doc, score in docs_with_scores[:self.top_n]
        ]


@lru_cache(maxsize=32)
def get_model_path(model: str, update_model: bool = False) -> str:
    """Get local path for a model, optionally updating it from HuggingFace."""
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME")
    local_files_only = not update_model or OFFLINE_MODE

    # Check if path exists or is a full path
    if (os.path.exists(model) or ("\\" in model or model.count("/") > 1)) and local_files_only:
        return model
        
    # Set repo ID for model short-name
    repo_id = f"sentence-transformers/{model}" if "/" not in model else model

    # Get snapshot path
    try:
        model_repo_path = snapshot_download(
            repo_id=repo_id,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )
        log.debug(f"Model repo path: {model_repo_path}")
        return model_repo_path
    except Exception as e:
        log.exception(f"Cannot determine model snapshot path: {e}")
        return model


def generate_embeddings(
    engine: str,
    model: str,
    text: Union[str, List[str]],
    prefix: Optional[str] = None,
    **kwargs,
) -> Union[List[float], List[List[float]]]:
    """Generate embeddings for text using specified engine."""
    url = kwargs.get("url", "")
    key = kwargs.get("key", "")
    user = kwargs.get("user")

    # Handle prefix if RAG_EMBEDDING_PREFIX_FIELD_NAME is not set
    if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
        if isinstance(text, list):
            text = [f"{prefix}{t}" for t in text]
        else:
            text = f"{prefix}{text}"

    # Create header with user info if enabled
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    
    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers.update({
            "X-OpenWebUI-User-Name": user.name,
            "X-OpenWebUI-User-Id": user.id,
            "X-OpenWebUI-User-Email": user.email,
            "X-OpenWebUI-User-Role": user.role,
        })

    # Convert single text to list for consistent handling
    is_single = isinstance(text, str)
    texts = [text] if is_single else text

    try:
        if engine == "ollama":
            json_data = {"model": model, "input": texts}
            if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and prefix:
                json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix
                
            response = requests.post(f"{url}/api/embed", headers=headers, json=json_data)
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings")
            
        elif engine == "openai":
            json_data = {"model": model, "input": texts}
            if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and prefix:
                json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix
                
            response = requests.post(f"{url}/embeddings", headers=headers, json=json_data)
            response.raise_for_status()
            data = response.json()
            embeddings = [elem["embedding"] for elem in data.get("data", [])]
        else:
            raise ValueError(f"Unsupported embedding engine: {engine}")
            
        return embeddings[0] if is_single else embeddings
    except Exception as e:
        log.exception(f"Error generating {engine} embeddings: {e}")
        raise


def query_doc(
    collection_name: str, 
    query_embedding: List[float], 
    k: int, 
    user: Optional[UserModel] = None
):
    """Query a document collection with vector search."""
    try:
        log.debug(f"Querying collection: {collection_name}")
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )
        
        if result and log.isEnabledFor(logging.INFO):
            log.info(f"Query results: {result.ids} {result.metadatas}")
            
        return result
    except Exception as e:
        log.exception(f"Error querying collection {collection_name} with limit {k}: {e}")
        raise


def get_doc(collection_name: str, user: Optional[UserModel] = None):
    """Get all documents from a collection."""
    try:
        log.debug(f"Getting collection: {collection_name}")
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)
        
        if result and log.isEnabledFor(logging.INFO):
            log.info(f"Get results: {result.ids} {result.metadatas}")
            
        return result
    except Exception as e:
        log.exception(f"Error getting collection {collection_name}: {e}")
        raise


def query_doc_with_hybrid_search(
    collection_name: str,
    collection_result: GetResult,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
) -> dict:
    """Query a document collection using hybrid search (BM25 + vector search)."""
    try:
        log.debug(f"Hybrid search on collection: {collection_name}")
        
        # Create BM25 retriever
        bm25_retriever = BM25Retriever.from_texts(
            texts=collection_result.documents[0],
            metadatas=collection_result.metadatas[0],
        )
        bm25_retriever.k = k
        
        # Create vector search retriever
        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )
        
        # Create ensemble retriever
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_search_retriever], 
            weights=[0.5, 0.5]
        )
        
        # Create compressor
        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k_reranker,
            reranking_function=reranking_function,
            r_score=r,
        )
        
        # Create compression retriever
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, 
            base_retriever=ensemble_retriever
        )
        
        # Get results
        result_docs = compression_retriever.invoke(query)
        
        # Extract data
        distances = [doc.metadata.get("score", 0) for doc in result_docs]
        documents = [doc.page_content for doc in result_docs]
        metadatas = [doc.metadata for doc in result_docs]
        
        # Limit results to k
        if k < k_reranker:
            # Sort by distance (score)
            sorted_items = sorted(zip(distances, metadatas, documents), key=lambda x: x[0], reverse=True)
            sorted_items = sorted_items[:k]
            distances, metadatas, documents = zip(*sorted_items) if sorted_items else ([], [], [])
            distances, metadatas, documents = list(distances), list(metadatas), list(documents)
            
        # Format result
        result = {
            "distances": [distances],
            "documents": [documents],
            "metadatas": [metadatas],
        }
        
        if log.isEnabledFor(logging.INFO):
            log.info(f"Hybrid search results: {result['metadatas']} {result['distances']}")
            
        return result
    except Exception as e:
        log.exception(f"Error with hybrid search on collection {collection_name}: {e}")
        raise


def merge_get_results(get_results: List[dict]) -> dict:
    """Merge multiple retrieval results into one."""
    combined_documents = []
    combined_metadatas = []
    combined_ids = []

    for data in get_results:
        if data and "documents" in data and "metadatas" in data and "ids" in data:
            combined_documents.extend(data["documents"][0])
            combined_metadatas.extend(data["metadatas"][0])
            combined_ids.extend(data["ids"][0])

    return {
        "documents": [combined_documents],
        "metadatas": [combined_metadatas],
        "ids": [combined_ids],
    }


def merge_and_sort_query_results(query_results: List[dict], k: int) -> dict:
    """Merge and sort multiple query results, removing duplicates."""
    # Dictionary to store unique documents by hash
    combined = {}

    for data in query_results:
        if not data or "distances" not in data or "documents" not in data or "metadatas" not in data:
            continue
            
        for distance, document, metadata in zip(
            data["distances"][0], data["documents"][0], data["metadatas"][0]
        ):
            if isinstance(document, str):
                # Compute document hash for deduplication
                doc_hash = hashlib.md5(document.encode()).hexdigest()
                
                # Add document if new or update if better score
                if doc_hash not in combined or distance > combined[doc_hash][0]:
                    combined[doc_hash] = (distance, document, metadata)

    # Sort by distance and take top k
    sorted_results = sorted(combined.values(), key=lambda x: x[0], reverse=True)[:k]
    
    # Unzip results
    if sorted_results:
        sorted_distances, sorted_documents, sorted_metadatas = zip(*sorted_results)
        return {
            "distances": [list(sorted_distances)],
            "documents": [list(sorted_documents)],
            "metadatas": [list(sorted_metadatas)],
        }
    else:
        return {"distances": [[]], "documents": [[]], "metadatas": [[]]}


def get_all_items_from_collections(collection_names: List[str]) -> dict:
    """Get all items from multiple collections."""
    results = []

    with ThreadPoolExecutor() as executor:
        future_to_collection = {
            executor.submit(get_doc, collection_name): collection_name 
            for collection_name in collection_names if collection_name
        }
        
        for future in future_to_collection:
            collection_name = future_to_collection[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f"Error getting collection {collection_name}: {e}")

    return merge_get_results(results)


def query_collection(
    collection_names: List[str],
    queries: List[str],
    embedding_function,
    k: int,
) -> dict:
    """Query multiple collections with multiple queries."""
    results = []
    
    # Generate query embeddings first (avoiding repeated encoding)
    query_embeddings = {
        query: embedding_function(query, prefix=RAG_EMBEDDING_QUERY_PREFIX)
        for query in queries
    }
    
    # Create tasks for parallel execution
    tasks = []
    with ThreadPoolExecutor() as executor:
        for query, query_embedding in query_embeddings.items():
            for collection_name in collection_names:
                if collection_name:
                    tasks.append(
                        executor.submit(
                            query_doc,
                            collection_name=collection_name,
                            k=k,
                            query_embedding=query_embedding,
                        )
                    )
        
        # Process results
        for future in tasks:
            try:
                result = future.result()
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f"Error querying collection: {e}")

    return merge_and_sort_query_results(results, k=k)


def query_collection_with_hybrid_search(
    collection_names: List[str],
    queries: List[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
) -> dict:
    """Query multiple collections with hybrid search."""
    results = []
    error = False
    
    # Fetch collection data once per collection
    collection_results = {}
    for collection_name in collection_names:
        if not collection_name:
            continue
            
        try:
            log.debug(f"Fetching collection data: {collection_name}")
            collection_results[collection_name] = VECTOR_DB_CLIENT.get(
                collection_name=collection_name
            )
        except Exception as e:
            log.exception(f"Failed to fetch collection {collection_name}: {e}")
            collection_results[collection_name] = None

    # Prepare tasks for parallel processing
    tasks = [
        (cn, q)
        for cn in collection_names
        if collection_results.get(cn) is not None
        for q in queries
    ]
    
    log.info(f"Starting hybrid search for {len(queries)} queries across {len(collection_names)} collections")

    # Process tasks in parallel
    with ThreadPoolExecutor() as executor:
        future_to_task = {
            executor.submit(
                query_doc_with_hybrid_search,
                collection_name=cn,
                collection_result=collection_results[cn],
                query=q,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                k_reranker=k_reranker,
                r=r,
            ): (cn, q)
            for cn, q in tasks
        }
        
        for future in future_to_task:
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                log.exception(f"Error with hybrid search: {e}")
                error = True

    if error and not results:
        log.warning("Hybrid search failed for all collections. Using non-hybrid search as fallback.")
        return query_collection(collection_names, queries, embedding_function, k)

    return merge_and_sort_query_results(results, k=k)


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
):
    """Get an embedding function based on configuration."""
    if not embedding_engine:
        # Use provided embedding_function
        return lambda query, prefix=None, user=None: embedding_function.encode(
            query, **({"prompt": prefix} if prefix else {})
        ).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        # Create a function that handles batching
        def batched_embedding_function(query, prefix=None, user=None):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    batch = query[i:i + embedding_batch_size]
                    embeddings.extend(
                        generate_embeddings(
                            engine=embedding_engine,
                            model=embedding_model,
                            text=batch,
                            prefix=prefix,
                            url=url,
                            key=key,
                            user=user,
                        )
                    )
                return embeddings
            else:
                return generate_embeddings(
                    engine=embedding_engine,
                    model=embedding_model,
                    text=query,
                    prefix=prefix,
                    url=url,
                    key=key,
                    user=user,
                )
                
        return batched_embedding_function
    else:
        raise ValueError(f"Unsupported embedding engine: {embedding_engine}")


def get_sources_from_files(
    request,
    files,
    queries,
    embedding_function,
    k,
    reranking_function,
    k_reranker,
    r,
    hybrid_search,
    full_context=False,
):
    """Get relevant sources from files based on queries."""
    log.debug(f"Processing files: {files}")

    extracted_collections = set()
    relevant_contexts = []

    for file in files:
        context = None
        
        # Handle different types of file inputs
        if file.get("docs"):
            # BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
            context = {
                "documents": [[doc.get("content") for doc in file.get("docs")]],
                "metadatas": [[doc.get("metadata") for doc in file.get("docs")]],
            }
        elif file.get("context") == "full":
            # Manual Full Mode Toggle
            context = {
                "documents": [[file.get("file").get("data", {}).get("content")]],
                "metadatas": [[{"file_id": file.get("id"), "name": file.get("name")}]],
            }
        elif (
            file.get("type") != "web_search"
            and request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
        ):
            # BYPASS_EMBEDDING_AND_RETRIEVAL
            if file.get("type") == "collection":
                file_ids = file.get("data", {}).get("file_ids", [])
                documents = []
                metadatas = []
                
                # Get content for each file in collection
                for file_id in file_ids:
                    file_object = Files.get_file_by_id(file_id)
                    if file_object:
                        documents.append(file_object.data.get("content", ""))
                        metadatas.append({
                            "file_id": file_id,
                            "name": file_object.filename,
                            "source": file_object.filename,
                        })

                context = {
                    "documents": [documents],
                    "metadatas": [metadatas],
                }
            elif file.get("id"):
                # Get content for single file
                file_object = Files.get_file_by_id(file.get("id"))
                if file_object:
                    context = {
                        "documents": [[file_object.data.get("content", "")]],
                        "metadatas": [[{
                            "file_id": file.get("id"),
                            "name": file_object.filename,
                            "source": file_object.filename,
                        }]],
                    }
            elif file.get("file", {}).get("data"):
                # Use provided file data
                context = {
                    "documents": [[file.get("file").get("data", {}).get("content")]],
                    "metadatas": [[file.get("file").get("data", {}).get("metadata", {})]],
                }
        else:
            # Use vector search for retrieval
            collection_names = []
            if file.get("type") == "collection":
                if file.get("legacy"):
                    collection_names = file.get("collection_names", [])
                else:
                    collection_names.append(file["id"])
            elif file.get("collection_name"):
                collection_names.append(file["collection_name"])
            elif file.get("id"):
                prefix = "" if file.get("legacy") else "file-"
                collection_names.append(f"{prefix}{file['id']}")

            # Filter out already processed collections
            collection_names = set(collection_names) - extracted_collections
            if not collection_names:
                log.debug(f"Skipping already processed file: {file.get('id')}")
                continue

            # Process collections
            if full_context:
                try:
                    context = get_all_items_from_collections(list(collection_names))
                except Exception as e:
                    log.exception(f"Error getting all items: {e}")
            else:
                try:
                    if file.get("type") == "text":
                        context = file["content"]
                    else:
                        # Try hybrid search first, fall back to regular search if needed
                        if hybrid_search:
                            try:
                                context = query_collection_with_hybrid_search(
                                    collection_names=list(collection_names),
                                    queries=queries,
                                    embedding_function=embedding_function,
                                    k=k,
                                    reranking_function=reranking_function,
                                    k_reranker=k_reranker,
                                    r=r,
                                )
                            except Exception as e:
                                log.warning(f"Hybrid search failed, using fallback: {e}")
                                context = None

                        if (not hybrid_search) or (context is None):
                            context = query_collection(
                                collection_names=list(collection_names),
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                            )
                except Exception as e:
                    log.exception(f"Error retrieving from collections: {e}")

            # Mark collections as processed
            extracted_collections.update(collection_names)

        # Add context to results if found
        if context:
            # Remove data field to reduce memory usage
            if "data" in file:
                del file["data"]
                
            relevant_contexts.append({**context, "file": file})

    # Format sources from contexts
    sources = []
    for context in relevant_contexts:
        try:
            if "documents" in context and "metadatas" in context:
                source = {
                    "source": context["file"],
                    "document": context["documents"][0],
                    "metadata": context["metadatas"][0],
                }
                if "distances" in context and context["distances"]:
                    source["distances"] = context["distances"][0]
                    
                sources.append(source)
        except Exception as e:
            log.exception(f"Error formatting source: {e}")

    return sources

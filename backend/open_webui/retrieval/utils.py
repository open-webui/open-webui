import logging
import os
import time
from typing import Optional, Union

import requests
import hashlib
from concurrent.futures import ThreadPoolExecutor

from huggingface_hub import snapshot_download
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from open_webui.config import VECTOR_DB
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

from open_webui.models.users import UserModel
from open_webui.models.files import Files

from open_webui.retrieval.vector.main import GetResult


from open_webui.env import (
    SRC_LOG_LEVELS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from open_webui.config import (
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever


# Circuit breaker for vector database operations
class VectorDBCircuitBreaker:
    """Simple circuit breaker to prevent cascading failures in vector DB operations."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, operation_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.operation_timeout = operation_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self):
        """Check if operation can be executed based on circuit breaker state."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                log.info("Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False
    
    def record_success(self):
        """Record successful operation."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            log.info("Circuit breaker reset to CLOSED state")
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            log.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
    
    def execute_with_timeout(self, operation, *args, **kwargs):
        """Execute operation with timeout and circuit breaker protection."""
        if not self.can_execute():
            raise Exception("Circuit breaker is OPEN - operation blocked")
        
        try:
            # Simple timeout implementation
            start_time = time.time()
            result = operation(*args, **kwargs)
            
            # Check if operation took too long (basic timeout check)
            if time.time() - start_time > self.operation_timeout:
                raise TimeoutError(f"Operation exceeded {self.operation_timeout}s timeout")
            
            self.record_success()
            return result
            
        except Exception as e:
            self.record_failure()
            log.error(f"Vector DB operation failed: {e}")
            raise


# Global circuit breaker instance
vector_db_circuit_breaker = VectorDBCircuitBreaker()


class VectorSearchRetriever(BaseRetriever):
    collection_name: Any
    embedding_function: Any
    top_k: int

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        result = VECTOR_DB_CLIENT.search(
            collection_name=self.collection_name,
            vectors=[self.embedding_function(query, RAG_EMBEDDING_QUERY_PREFIX)],
            limit=self.top_k,
        )

        ids = result.ids[0]
        metadatas = result.metadatas[0]
        documents = result.documents[0]

        results = []
        for idx in range(len(ids)):
            results.append(
                Document(
                    metadata=metadatas[idx],
                    page_content=documents[idx],
                )
            )
        return results


def query_doc(
    collection_name: str, query_embedding: list[float], k: int, user: UserModel = None
):
    try:
        log.debug(f"query_doc:doc {collection_name}")
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        log.exception(f"Error querying doc {collection_name} with limit {k}: {e}")
        raise e


def get_doc(collection_name: str, user: UserModel = None):
    try:
        log.debug(f"get_doc:doc {collection_name}")
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        log.exception(f"Error getting doc {collection_name}: {e}")
        raise e


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
    try:
        log.debug(f"query_doc_with_hybrid_search:doc {collection_name}")
        bm25_retriever = BM25Retriever.from_texts(
            texts=collection_result.documents[0],
            metadatas=collection_result.metadatas[0],
        )
        bm25_retriever.k = k

        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_search_retriever], weights=[0.5, 0.5]
        )
        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k_reranker,
            reranking_function=reranking_function,
            r_score=r,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = compression_retriever.invoke(query)

        distances = [d.metadata.get("score") for d in result]
        documents = [d.page_content for d in result]
        metadatas = [d.metadata for d in result]

        # retrieve only min(k, k_reranker) items, sort and cut by distance if k < k_reranker
        if k < k_reranker:
            sorted_items = sorted(
                zip(distances, metadatas, documents), key=lambda x: x[0], reverse=True
            )
            sorted_items = sorted_items[:k]
            distances, documents, metadatas = map(list, zip(*sorted_items))

        result = {
            "distances": [distances],
            "documents": [documents],
            "metadatas": [metadatas],
        }

        log.info(
            "query_doc_with_hybrid_search:result "
            + f'{result["metadatas"]} {result["distances"]}'
        )
        return result
    except Exception as e:
        log.exception(f"Error querying doc {collection_name} with hybrid search: {e}")
        raise e


def merge_get_results(get_results: list[dict]) -> dict:
    # Initialize lists to store combined data
    combined_documents = []
    combined_metadatas = []
    combined_ids = []

    for data in get_results:
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])
        combined_ids.extend(data["ids"][0])

    # Create the output dictionary
    result = {
        "documents": [combined_documents],
        "metadatas": [combined_metadatas],
        "ids": [combined_ids],
    }

    return result


def merge_and_sort_query_results(query_results: list[dict], k: int) -> dict:
    # Initialize lists to store combined data
    combined = dict()  # To store documents with unique document hashes

    for data in query_results:
        distances = data["distances"][0]
        documents = data["documents"][0]
        metadatas = data["metadatas"][0]

        for distance, document, metadata in zip(distances, documents, metadatas):
            if isinstance(document, str):
                doc_hash = hashlib.sha256(
                    document.encode()
                ).hexdigest()  # Compute a hash for uniqueness

                if doc_hash not in combined.keys():
                    combined[doc_hash] = (distance, document, metadata)
                    continue  # if doc is new, no further comparison is needed

                # if doc is alredy in, but new distance is better, update
                if distance > combined[doc_hash][0]:
                    combined[doc_hash] = (distance, document, metadata)

    combined = list(combined.values())
    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=True)

    # Slice to keep only the top k elements
    sorted_distances, sorted_documents, sorted_metadatas = (
        zip(*combined[:k]) if combined else ([], [], [])
    )

    # Create and return the output dictionary
    return {
        "distances": [list(sorted_distances)],
        "documents": [list(sorted_documents)],
        "metadatas": [list(sorted_metadatas)],
    }


def get_all_items_from_collections(collection_names: list[str], limit: Optional[int] = None) -> dict:
    results = []

    for collection_name in collection_names:
        if collection_name:
            try:
                # Use circuit breaker for vector DB operations
                def vector_operation():
                    if limit:
                        return VECTOR_DB_CLIENT.query(
                            collection_name=collection_name,
                            filter={},
                            limit=limit
                        )
                    else:
                        return get_doc(collection_name=collection_name)
                
                result = vector_db_circuit_breaker.execute_with_timeout(vector_operation)
                    
                if result is not None:
                    # Convert GetResult object to dictionary format expected by merge_get_results
                    if hasattr(result, 'model_dump'):
                        results.append(result.model_dump())
                    else:
                        # Fallback: manually convert GetResult to dict format
                        result_dict = {
                            "documents": [result.documents[0]] if result.documents else [[]],
                            "metadatas": [result.metadatas[0]] if result.metadatas else [[]],
                            "ids": [result.ids[0]] if result.ids else [[]]
                        }
                        results.append(result_dict)
            except Exception as e:
                log.exception(f"Error when getting all items from collection {collection_name}: {e}")
                # Continue with other collections even if one fails

    return merge_get_results(results)


def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    results = []
    error = False
    
    # Memory safety limits
    MAX_COLLECTIONS_QUERY = 20  # Maximum collections for regular query
    MAX_QUERIES = 10  # Maximum queries to process
    
    # Limit collections and queries to prevent resource exhaustion
    if len(collection_names) > MAX_COLLECTIONS_QUERY:
        log.warning(f"Too many collections ({len(collection_names)}), limiting to {MAX_COLLECTIONS_QUERY}")
        collection_names = collection_names[:MAX_COLLECTIONS_QUERY]
    
    if len(queries) > MAX_QUERIES:
        log.warning(f"Too many queries ({len(queries)}), limiting to {MAX_QUERIES}")
        queries = queries[:MAX_QUERIES]

    def process_query_collection(collection_name, query_embedding):
        try:
            if collection_name:
                # Use circuit breaker for vector DB operations
                def query_operation():
                    return query_doc(
                        collection_name=collection_name,
                        k=k,
                        query_embedding=query_embedding,
                    )
                
                result = vector_db_circuit_breaker.execute_with_timeout(query_operation)
                if result is not None:
                    return result.model_dump(), None
            return None, None
        except Exception as e:
            log.exception(f"Error when querying the collection {collection_name}: {e}")
            return None, e

    # Generate all query embeddings (in one call) - this is already optimized
    query_embeddings = embedding_function(queries, prefix=RAG_EMBEDDING_QUERY_PREFIX)
    log.debug(
        f"query_collection: processing {len(queries)} queries across {len(collection_names)} collections"
    )

    # Optimize: Use smaller thread pool to prevent overwhelming the vector DB
    max_workers = min(4, len(collection_names) * len(query_embeddings), 8)  # Hard cap at 8 workers
    
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="vector_query") as executor:
        future_results = []
        for query_embedding in query_embeddings:
            for collection_name in collection_names:
                result = executor.submit(
                    process_query_collection, collection_name, query_embedding
                )
                future_results.append(result)
        task_results = [future.result() for future in future_results]

    for result, err in task_results:
        if err is not None:
            error = True
        elif result is not None:
            results.append(result)

    if error and not results:
        log.warning("All collection queries failed. No results returned.")

    return merge_and_sort_query_results(results, k=k)


def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
) -> dict:
    results = []
    error = False
    
    # Memory-safe limits for hybrid search operations
    HYBRID_SEARCH_COLLECTION_LIMIT = 1000  # Reduced from 2000 for memory safety
    MAX_TOTAL_DOCUMENTS = 5000  # Maximum total documents across all collections
    MAX_COLLECTIONS = 10  # Maximum number of collections to process
    
    # Limit number of collections to prevent memory exhaustion
    if len(collection_names) > MAX_COLLECTIONS:
        log.warning(f"Too many collections ({len(collection_names)}), limiting to {MAX_COLLECTIONS}")
        collection_names = collection_names[:MAX_COLLECTIONS]
    
    # Fetch collection data once per collection sequentially with memory monitoring
    # Avoid fetching the same data multiple times later
    collection_results = {}
    total_documents_loaded = 0
    
    for collection_name in collection_names:
        try:
            log.debug(
                f"query_collection_with_hybrid_search:VECTOR_DB_CLIENT.get:collection {collection_name}"
            )
            
            # Check if we've already loaded too many documents
            if total_documents_loaded >= MAX_TOTAL_DOCUMENTS:
                log.warning(f"Reached maximum document limit ({MAX_TOTAL_DOCUMENTS}), skipping remaining collections")
                break
            
            # Calculate remaining document budget
            remaining_budget = min(HYBRID_SEARCH_COLLECTION_LIMIT, MAX_TOTAL_DOCUMENTS - total_documents_loaded)
            
            # Use circuit breaker for vector DB operations
            def fetch_collection():
                return VECTOR_DB_CLIENT.query(
                    collection_name=collection_name,
                    filter={},
                    limit=remaining_budget
                )
            
            collection_results[collection_name] = vector_db_circuit_breaker.execute_with_timeout(fetch_collection)
            
            if collection_results[collection_name]:
                doc_count = len(collection_results[collection_name].documents[0])
                total_documents_loaded += doc_count
                log.debug(f"Loaded {doc_count} documents from {collection_name} for hybrid search (total: {total_documents_loaded}/{MAX_TOTAL_DOCUMENTS})")
            else:
                collection_results[collection_name] = None
                
        except Exception as e:
            log.exception(f"Failed to fetch collection {collection_name}: {e}")
            collection_results[collection_name] = None

    log.info(
        f"Starting hybrid search for {len(queries)} queries in {len(collection_names)} collections..."
    )

    def process_query(collection_name, query):
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                collection_result=collection_results[collection_name],
                query=query,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                k_reranker=k_reranker,
                r=r,
            )
            return result, None
        except Exception as e:
            log.exception(f"Error when querying the collection with hybrid_search: {e}")
            return None, e

    # Prepare tasks for all collections and queries
    # Avoid running any tasks for collections that failed to fetch data (have assigned None)
    tasks = [
        (cn, q)
        for cn in collection_names
        if collection_results[cn] is not None
        for q in queries
    ]

    # Use limited thread pool for hybrid search to prevent resource exhaustion
    max_workers = min(4, len(tasks), 6)  # Hard cap at 6 workers for hybrid search
    
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="hybrid_search") as executor:
        future_results = [executor.submit(process_query, cn, q) for cn, q in tasks]
        task_results = [future.result() for future in future_results]

    for result, err in task_results:
        if err is not None:
            error = True
        elif result is not None:
            results.append(result)

    if error and not results:
        raise Exception(
            "Hybrid search failed for all collections. Using Non-hybrid search as fallback."
        )

    return merge_and_sort_query_results(results, k=k)


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
):
    if embedding_engine == "":
        return lambda query, prefix=None, user=None: embedding_function.encode(
            query, **({"prompt": prefix} if prefix else {})
        ).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        func = lambda query, prefix=None, user=None: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            prefix=prefix,
            url=url,
            key=key,
            user=user,
        )

        def generate_multiple(query, prefix, user, func):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    embeddings.extend(
                        func(
                            query[i : i + embedding_batch_size],
                            prefix=prefix,
                            user=user,
                        )
                    )
                return embeddings
            else:
                return func(query, prefix, user)

        return lambda query, prefix=None, user=None: generate_multiple(
            query, prefix, user, func
        )
    else:
        raise ValueError(f"Unknown embedding engine: {embedding_engine}")


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
    sources = []

    for file in files:
        try:
            if file["type"] == "collection":
                collection_names = file["collection_names"]

                # DEBUG: Log the path taken based on full_context
                if full_context:
                    log.info(f"DEBUG: Using FULL CONTEXT mode for collections: {collection_names}")
                    try:
                        # SIMPLE FIX: Add a reasonable limit to prevent performance issues
                        # This is the minimal change to fix your timeout issue
                        context = get_all_items_from_collections(collection_names, limit=500)
                        # DEBUG: Log what get_all_items_from_collections returned
                        if context:
                            doc_count = len(context.get("documents", [[]])[0]) if context.get("documents") else 0
                            log.info(f"DEBUG: get_all_items_from_collections returned {doc_count} documents (limited to 500)")
                        else:
                            log.warning(f"DEBUG: get_all_items_from_collections returned None/empty for {collection_names}")
                    except Exception as e:
                        log.exception(f"DEBUG: Error in get_all_items_from_collections: {e}")
                        context = None

                    if context:
                        sources.append(
                            {
                                "source": {"name": file["name"]},
                                "document": context["documents"][0],
                                "metadata": context["metadatas"][0],
                            }
                        )
                else:
                    # DEBUG: Log the path taken based on full_context
                    log.info(f"DEBUG: Using QUERY mode for collections: {collection_names}")

                    if hybrid_search:
                        try:
                            context = query_collection_with_hybrid_search(
                                collection_names=collection_names,
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                                reranking_function=reranking_function,
                                k_reranker=k_reranker,
                                r=r,
                            )
                        except Exception as e:
                            log.exception(f"Error when querying the collection: {e}")
                            context = None
                    else:
                        try:
                            context = query_collection(
                                collection_names=collection_names,
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                            )
                        except Exception as e:
                            log.exception(f"Error when querying the collection: {e}")
                            context = None

                    if context:
                        sources.append(
                            {
                                "source": {"name": file["name"]},
                                "document": context["documents"][0],
                                "metadata": context["metadatas"][0],
                            }
                        )
            elif file["type"] == "web_search":
                if "docs" in file:
                    sources.append(
                        {
                            "source": {"name": file["name"]},
                            "document": [doc["content"] for doc in file["docs"]],
                            "metadata": [
                                {
                                    "source": doc["url"],
                                    "title": doc.get("title", doc["url"]),
                                }
                                for doc in file["docs"]
                            ],
                        }
                    )
                else:
                    collection_name = file["collection_name"]

                    if full_context:
                        try:
                            # SIMPLE FIX: Add limit here too
                            context = get_all_items_from_collections([collection_name], limit=500)
                        except Exception as e:
                            log.exception(f"Error when getting all items from collection: {e}")
                            context = None
                    else:
                        if hybrid_search:
                            try:
                                context = query_collection_with_hybrid_search(
                                    collection_names=[collection_name],
                                    queries=queries,
                                    embedding_function=embedding_function,
                                    k=k,
                                    reranking_function=reranking_function,
                                    k_reranker=k_reranker,
                                    r=r,
                                )
                            except Exception as e:
                                log.exception(f"Error when querying the collection: {e}")
                                context = None
                        else:
                            try:
                                context = query_collection(
                                    collection_names=[collection_name],
                                    queries=queries,
                                    embedding_function=embedding_function,
                                    k=k,
                                )
                            except Exception as e:
                                log.exception(f"Error when querying the collection: {e}")
                                context = None

                    if context:
                        sources.append(
                            {
                                "source": {"name": file["name"]},
                                "document": context["documents"][0],
                                "metadata": context["metadatas"][0],
                            }
                        )
            else:
                collection_name = file.get("collection_name") or file.get("id")

                if full_context:
                    try:
                        # SIMPLE FIX: Add limit here too
                        context = get_all_items_from_collections([collection_name], limit=500)
                    except Exception as e:
                        log.exception(f"Error when getting all items from collection: {e}")
                        context = None
                else:
                    if hybrid_search:
                        try:
                            context = query_collection_with_hybrid_search(
                                collection_names=[collection_name],
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                                reranking_function=reranking_function,
                                k_reranker=k_reranker,
                                r=r,
                            )
                        except Exception as e:
                            log.exception(f"Error when querying the collection: {e}")
                            context = None
                    else:
                        try:
                            context = query_collection(
                                collection_names=[collection_name],
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                            )
                        except Exception as e:
                            log.exception(f"Error when querying the collection: {e}")
                            context = None

                if context:
                    sources.append(
                        {
                            "source": {"name": file["name"]},
                            "document": context["documents"][0],
                            "metadata": context["metadatas"][0],
                        }
                    )
        except Exception as e:
            log.exception(f"Error when processing file: {e}")

    return sources


def get_model_path(model: str, update_model: bool = False):
    # Construct huggingface_hub kwargs with local_files_only to return the snapshot path
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME")

    local_files_only = not update_model

    if OFFLINE_MODE:
        local_files_only = True

    snapshot_kwargs = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
    }

    log.debug(f"model: {model}")
    log.debug(f"snapshot_kwargs: {snapshot_kwargs}")

    # Inspiration from upstream sentence_transformers
    if (
        os.path.exists(model)
        or ("\\" in model or model.count("/") > 1)
        and local_files_only
    ):
        # If fully qualified path exists, return input, else set repo_id
        return model
    elif "/" not in model:
        # Set valid repo_id for model short-name
        model = "sentence-transformers" + "/" + model

    snapshot_kwargs["repo_id"] = model

    # Attempt to query the huggingface_hub library to determine the local path and/or to update
    try:
        model_repo_path = snapshot_download(**snapshot_kwargs)
        log.debug(f"model_repo_path: {model_repo_path}")
        return model_repo_path
    except Exception as e:
        log.exception(f"Cannot determine model snapshot path: {e}")
        return model


def generate_openai_batch_embeddings(
    model: str,
    texts: list[str],
    url: str = "https://api.openai.com/v1",
    key: str = "",
    prefix: str = None,
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    try:
        log.debug(
            f"generate_openai_batch_embeddings:model {model} batch size: {len(texts)}"
        )
        json_data = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user
                    else {}
                ),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return [elem["embedding"] for elem in data["data"]]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        log.exception(f"Error generating openai batch embeddings: {e}")
        return None


def generate_ollama_batch_embeddings(
    model: str,
    texts: list[str],
    url: str,
    key: str = "",
    prefix: str = None,
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    try:
        log.debug(
            f"generate_ollama_batch_embeddings:model {model} batch size: {len(texts)}"
        )
        json_data = {"input": texts, "model": model}
        if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
            json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix

        r = requests.post(
            f"{url}/api/embed",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            },
            json=json_data,
        )
        r.raise_for_status()
        data = r.json()

        if "embeddings" in data:
            return data["embeddings"]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        log.exception(f"Error generating ollama batch embeddings: {e}")
        return None


def generate_embeddings(
    engine: str,
    model: str,
    text: Union[str, list[str]],
    prefix: Union[str, None] = None,
    **kwargs,
):
    url = kwargs.get("url", "")
    key = kwargs.get("key", "")
    user = kwargs.get("user")

    if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
        if isinstance(text, list):
            text = [f"{prefix}{text_element}" for text_element in text]
        else:
            text = f"{prefix}{text}"

    if engine == "ollama":
        if isinstance(text, list):
            embeddings = generate_ollama_batch_embeddings(
                **{
                    "model": model,
                    "texts": text,
                    "url": url,
                    "key": key,
                    "prefix": prefix,
                    "user": user,
                }
            )
        else:
            embeddings = generate_ollama_batch_embeddings(
                **{
                    "model": model,
                    "texts": [text],
                    "url": url,
                    "key": key,
                    "prefix": prefix,
                    "user": user,
                }
            )
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "openai":
        if isinstance(text, list):
            embeddings = generate_openai_batch_embeddings(
                model, text, url, key, prefix, user
            )
        else:
            embeddings = generate_openai_batch_embeddings(
                model, [text], url, key, prefix, user
            )
        return embeddings[0] if isinstance(text, str) else embeddings


import operator
from typing import Optional, Sequence

from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document


class RerankCompressor(BaseDocumentCompressor):
    embedding_function: Any
    top_n: int
    reranking_function: Any
    r_score: float

    class Config:
        extra = "forbid"
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        reranking = self.reranking_function is not None

        if reranking:
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

        docs_with_scores = list(
            zip(documents, scores.tolist() if not isinstance(scores, list) else scores)
        )
        if self.r_score:
            docs_with_scores = [
                (d, s) for d, s in docs_with_scores if s >= self.r_score
            ]

        result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
        final_results = []
        for doc, doc_score in result[: self.top_n]:
            metadata = doc.metadata
            metadata["score"] = doc_score
            doc = Document(
                page_content=doc.page_content,
                metadata=metadata,
            )
            final_results.append(doc)
        return final_results
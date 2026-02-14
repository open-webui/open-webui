import logging
import os
import uuid
from typing import Optional, Union, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import asyncio
import requests
import hashlib

from huggingface_hub import snapshot_download
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

try:
    from portkey_ai import Portkey
    PORTKEY_SDK_AVAILABLE = True
except ImportError:
    PORTKEY_SDK_AVAILABLE = False

log = logging.getLogger(__name__)


from open_webui.config import VECTOR_DB, RAG_EMBEDDING_MODEL
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.utils.misc import get_last_user_message, calculate_sha256_string

from open_webui.models.users import UserModel
from open_webui.models.files import Files

from open_webui.env import (
    SRC_LOG_LEVELS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)

log.setLevel(SRC_LOG_LEVELS["RAG"])

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever


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
            vectors=[self.embedding_function(query)],
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
    log.info(f"[VECTOR_SEARCH] query_doc START | collection={collection_name} | k={k} | embedding_len={len(query_embedding) if query_embedding else 0}")
    try:
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        if result:
            num_results = len(result.ids[0]) if result.ids and result.ids[0] else 0
            log.info(f"[VECTOR_SEARCH] query_doc SUCCESS | collection={collection_name} | results_count={num_results} | ids={result.ids} | metadatas={result.metadatas}")
        else:
            log.info(f"[VECTOR_SEARCH] query_doc EMPTY | collection={collection_name} | no results")

        return result
    except Exception as e:
        log.exception(f"[VECTOR_SEARCH] query_doc ERROR | collection={collection_name} | k={k} | error={e}")
        raise e


def get_doc(collection_name: str, user: UserModel = None):
    log.info(f"[VECTOR_GET] get_doc START | collection={collection_name}")
    try:
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        if result:
            num_docs = len(result.ids[0]) if result.ids and result.ids[0] else 0
            log.info(f"[VECTOR_GET] get_doc SUCCESS | collection={collection_name} | docs_count={num_docs} | ids={result.ids} | metadatas={result.metadatas}")
        else:
            log.info(f"[VECTOR_GET] get_doc EMPTY | collection={collection_name} | no documents")

        return result
    except Exception as e:
        log.exception(f"[VECTOR_GET] get_doc ERROR | collection={collection_name} | error={e}")
        raise e


def query_doc_with_hybrid_search(
    collection_name: str,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
) -> dict:
    try:
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        bm25_retriever = BM25Retriever.from_texts(
            texts=result.documents[0],
            metadatas=result.metadatas[0],
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
            top_n=k,
            reranking_function=reranking_function,
            r_score=r,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = compression_retriever.invoke(query)
        result = {
            "distances": [[d.metadata.get("score") for d in result]],
            "documents": [[d.page_content for d in result]],
            "metadatas": [[d.metadata for d in result]],
        }

        log.info(
            "query_doc_with_hybrid_search:result "
            + f'{result["metadatas"]} {result["distances"]}'
        )
        return result
    except Exception as e:
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


def merge_and_sort_query_results(
    query_results: list[dict], k: int, reverse: bool = False
) -> dict:
    # Initialize lists to store combined data
    combined = []
    seen_hashes = set()  # To store unique document hashes

    for data in query_results:
        distances = data["distances"][0]
        documents = data["documents"][0]
        metadatas = data["metadatas"][0]

        for distance, document, metadata in zip(distances, documents, metadatas):
            if isinstance(document, str):
                doc_hash = hashlib.md5(
                    document.encode()
                ).hexdigest()  # Compute a hash for uniqueness

                if doc_hash not in seen_hashes:
                    seen_hashes.add(doc_hash)
                    combined.append((distance, document, metadata))

    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=reverse)

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


def get_all_items_from_collections(collection_names: list[str]) -> dict:
    results = []

    for collection_name in collection_names:
        if collection_name:
            try:
                result = get_doc(collection_name=collection_name)
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f"Error when querying the collection: {e}")
        else:
            pass

    return merge_get_results(results)


def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    log.info(f"[QUERY_COLLECTION] START | collections={list(collection_names)} | queries_count={len(queries) if queries else 0} | k={k} | queries={queries[:3] if queries else []}{'...' if queries and len(queries) > 3 else ''}")
    results = []
    
    # Handle edge cases
    if not queries or len(queries) == 0:
        log.warning("[QUERY_COLLECTION] EMPTY | called with empty queries list")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    if not collection_names or len(collection_names) == 0:
        log.warning("query_collection called with empty collection_names list")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # Filter out empty queries
    queries = [q for q in queries if q and q.strip()]
    if not queries:
        log.warning("All queries were empty after filtering")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # Batch embedding generation for multiple queries (faster than individual calls)
    # The embedding_function supports both single strings and lists of strings
    query_embedding_map = {}
    try:
        if len(queries) > 1:
            # Batch embed all queries at once - significantly faster for multiple queries
            log.debug(f"Batching {len(queries)} queries for embedding generation")
            query_embeddings = embedding_function(queries)
            
            # Handle different return formats:
            # - List of embeddings: [[emb1], [emb2], ...] or [emb1, emb2, ...]
            # - Single embedding: [emb1] or just emb1 (shouldn't happen for batch)
            if isinstance(query_embeddings, list):
                if len(query_embeddings) == len(queries):
                    # Check if embeddings are nested lists or flat lists
                    if len(query_embeddings) > 0 and isinstance(query_embeddings[0], list):
                        # Already in correct format: [[emb1], [emb2], ...]
                        # Validate embeddings are not empty
                        for i, emb in enumerate(query_embeddings):
                            if isinstance(emb, list) and len(emb) > 0:
                                query_embedding_map[queries[i]] = emb
                            else:
                                log.warning(f"Empty or invalid embedding for query {i}: {queries[i]}")
                    else:
                        # Flat list: might be single embedding or needs wrapping
                        # If length matches, assume each element is an embedding vector
                        for i, emb in enumerate(query_embeddings):
                            if isinstance(emb, list) and len(emb) > 0:
                                query_embedding_map[queries[i]] = emb
                            else:
                                log.warning(f"Empty or invalid embedding for query {i}: {queries[i]}")
                else:
                    # Mismatch - fallback to individual calls
                    log.warning(f"Batch embedding returned {len(query_embeddings)} results for {len(queries)} queries, falling back to individual calls")
                    raise ValueError("Batch embedding result length mismatch")
            else:
                # Unexpected return type - fallback
                log.warning(f"Batch embedding returned unexpected type: {type(query_embeddings)}, falling back to individual calls")
                raise ValueError("Unexpected batch embedding return type")
        elif len(queries) == 1:
            # Single query - embed normally
            embedding = embedding_function(queries[0])
            # Ensure it's a list (embedding functions should return list[float])
            if isinstance(embedding, list) and len(embedding) > 0:
                query_embedding_map[queries[0]] = embedding
            else:
                # Invalid embedding - log and skip
                log.warning(f"Empty or invalid embedding for single query: {queries[0]}")
                if not isinstance(embedding, list):
                    # Try wrapping as fallback
                    query_embedding_map[queries[0]] = [embedding] if embedding else None
    except Exception as e:
        log.exception(f"Error generating batch embeddings: {e}")
        # Fallback to individual embedding generation
        log.debug("Falling back to individual embedding generation")
        for query in queries:
            try:
                embedding = embedding_function(query)
                if isinstance(embedding, list) and len(embedding) > 0:
                    query_embedding_map[query] = embedding
                elif isinstance(embedding, list) and len(embedding) == 0:
                    log.warning(f"Empty embedding returned for query: {query}")
                else:
                    # Wrap non-list embeddings
                    query_embedding_map[query] = [embedding] if embedding else None
            except Exception as embed_error:
                log.exception(f"Error embedding query '{query}': {embed_error}")
                continue
    
    # Validate we have at least some embeddings
    if not query_embedding_map:
        log.error("Failed to generate embeddings for any queries")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # Parallelize query processing for faster RAG retrieval
    # Note: Thread-safety depends on the vector DB implementation:
    # - Postgres (pgvector): Uses scoped_session - thread-safe
    # - SQLite-based DBs: May have issues with concurrent access
    # - Chroma/Qdrant/Milvus: Generally thread-safe if using separate clients per thread
    def process_query_collection_pair(query: str, collection_name: str, query_embedding: list[float]):
        """Process a single query against a single collection using pre-computed embedding"""
        try:
            if collection_name:
                result = query_doc(
                    collection_name=collection_name,
                    k=k,
                    query_embedding=query_embedding,
                )
                if result is not None:
                    return result.model_dump()
        except Exception as e:
            log.exception(f"Error when querying collection {collection_name} with query: {e}")
        return None
    
    # Create all query-collection pairs with pre-computed embeddings
    # Filter out None embeddings and ensure embeddings are valid lists
    query_collection_pairs = []
    for query in queries:
        if query not in query_embedding_map:
            continue
        embedding = query_embedding_map[query]
        if embedding is None or not isinstance(embedding, list) or len(embedding) == 0:
            continue
        for collection_name in collection_names:
            query_collection_pairs.append((query, collection_name, embedding))
    
    if not query_collection_pairs:
        log.warning("No valid query-collection pairs after filtering invalid embeddings")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # For single query-collection pair, process sequentially to avoid overhead
    # For multiple queries/collections, use parallel processing
    if len(query_collection_pairs) == 1:
        # Sequential processing for single query-collection pair
        query, collection_name, query_embedding = query_collection_pairs[0]
        if query_embedding and isinstance(query_embedding, list) and len(query_embedding) > 0:
            result = process_query_collection_pair(query, collection_name, query_embedding)
            if result is not None:
                results.append(result)
    elif len(query_collection_pairs) > 1:
        # Process in parallel using ThreadPoolExecutor
        # Limit workers to prevent resource exhaustion and potential SQLite lock issues
        max_workers = min(len(query_collection_pairs), 10)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pair = {
                executor.submit(process_query_collection_pair, query, collection_name, query_embedding): (query, collection_name)
                for query, collection_name, query_embedding in query_collection_pairs
                if query_embedding is not None and isinstance(query_embedding, list) and len(query_embedding) > 0
            }
            
            if not future_to_pair:
                log.warning("No valid futures created for parallel query processing")
            else:
                for future in as_completed(future_to_pair):
                    try:
                        result = future.result()
                        if result is not None:
                            results.append(result)
                    except Exception as e:
                        log.exception(f"Error in parallel query processing: {e}")

    if VECTOR_DB == "chroma":
        # Chroma uses unconventional cosine similarity, so we don't need to reverse the results
        # https://docs.trychroma.com/docs/collections/configure#configuring-chroma-collections
        merged = merge_and_sort_query_results(results, k=k, reverse=False)
    else:
        merged = merge_and_sort_query_results(results, k=k, reverse=True)
    
    merged_count = len(merged.get("documents", [[]])[0]) if merged and merged.get("documents") else 0
    log.info(f"[QUERY_COLLECTION] DONE | collections={list(collection_names)} | results_merged={merged_count} | k={k}")
    return merged


def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    r: float,
) -> dict:
    log.info(f"[HYBRID_SEARCH] START | collections={list(collection_names)} | queries_count={len(queries) if queries else 0} | k={k} | r={r}")
    results = []
    errors = []
    
    # Handle edge cases
    if not queries or len(queries) == 0:
        log.warning("query_collection_with_hybrid_search called with empty queries list")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    if not collection_names or len(collection_names) == 0:
        log.warning("query_collection_with_hybrid_search called with empty collection_names list")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # Filter out empty queries
    queries = [q for q in queries if q and q.strip()]
    if not queries:
        log.warning("All queries were empty after filtering in hybrid search")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # Parallelize query processing for faster RAG retrieval with hybrid search
    # Note: Thread-safety depends on the vector DB implementation
    def process_hybrid_search(query: str, collection_name: str):
        """Process a single query against a single collection with hybrid search"""
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                query=query,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                r=r,
            )
            return {"result": result, "error": None, "collection": collection_name}
        except Exception as e:
            log.exception(
                f"Error when querying collection {collection_name} with hybrid_search: {e}"
            )
            return {"result": None, "error": str(e), "collection": collection_name}
    
    # Create all query-collection pairs
    query_collection_pairs = [
        (query, collection_name)
        for collection_name in collection_names
        for query in queries
    ]
    
    if not query_collection_pairs:
        log.warning("No valid query-collection pairs for hybrid search")
        return merge_and_sort_query_results(results, k=k, reverse=True) if VECTOR_DB != "chroma" else merge_and_sort_query_results(results, k=k, reverse=False)
    
    # For single query-collection pair, process sequentially to avoid overhead
    # For multiple queries/collections, use parallel processing
    if len(query_collection_pairs) == 1:
        # Sequential processing for single query-collection pair
        pair_result = process_hybrid_search(query_collection_pairs[0][0], query_collection_pairs[0][1])
        if pair_result["result"] is not None:
            results.append(pair_result["result"])
        elif pair_result["error"]:
            errors.append(pair_result)
    else:
        # Process in parallel using ThreadPoolExecutor
        # Limit workers to prevent resource exhaustion and potential SQLite lock issues
        max_workers = min(len(query_collection_pairs), 10)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pair = {
                executor.submit(process_hybrid_search, query, collection_name): (query, collection_name)
                for query, collection_name in query_collection_pairs
            }
            
            for future in as_completed(future_to_pair):
                try:
                    pair_result = future.result()
                    if pair_result["result"] is not None:
                        results.append(pair_result["result"])
                    elif pair_result["error"]:
                        errors.append(pair_result)
                except Exception as e:
                    log.exception(f"Error in parallel hybrid search processing: {e}")
                    errors.append({"result": None, "error": str(e), "collection": "unknown"})

    # Only raise error if ALL searches failed
    if len(errors) == len(query_collection_pairs):
        log.error(f"[HYBRID_SEARCH] ALL_FAILED | collections={list(collection_names)} | errors_count={len(errors)}")
        raise Exception(
            "Hybrid search failed for all collections. Using Non hybrid search as fallback."
        )

    if VECTOR_DB == "chroma":
        # Chroma uses unconventional cosine similarity, so we don't need to reverse the results
        # https://docs.trychroma.com/docs/collections/configure#configuring-chroma-collections
        merged = merge_and_sort_query_results(results, k=k, reverse=False)
    else:
        merged = merge_and_sort_query_results(results, k=k, reverse=True)
    
    merged_count = len(merged.get("documents", [[]])[0]) if merged and merged.get("documents") else 0
    log.info(f"[HYBRID_SEARCH] DONE | collections={list(collection_names)} | results_merged={merged_count} | errors_count={len(errors)} | k={k}")
    return merged


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
    backoff=True,
):
    if embedding_engine == "":
        return lambda query, user=None: embedding_function.encode(query).tolist()
    elif embedding_engine in ["ollama", "openai", "portkey"]:
        func = lambda query, user=None: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            url=url,
            key=key,
            user=user,
            backoff=backoff,
        )

        def generate_multiple(query, user, func):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    embeddings.extend(
                        func(query[i : i + embedding_batch_size], user=user)
                    )
                return embeddings
            else:
                return func(query, user)

        return lambda query, user=None: generate_multiple(query, user, func)
    else:
        raise ValueError(f"Unknown embedding engine: {embedding_engine}")


# Modified get_embedding_function to send all texts in one batch
def get_single_batch_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
    backoff=True,
):
    if embedding_engine == "":
        return lambda query, user=None: embedding_function.encode(query).tolist()
    elif embedding_engine in ["ollama", "openai", "portkey"]:
        engine = embedding_engine
        model = embedding_model
        url = url
        key = key

        # Return a function that processes everything in one go
        return lambda query, user=None: generate_embeddings(
            engine=engine,
            model=model,
            text=query,
            url=url,
            key=key,
            user=user,
            backoff=backoff,
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
    r,
    hybrid_search,
    full_context=False,
):
    log.debug(
        f"files: {files} {queries} {embedding_function} {reranking_function} {full_context}"
    )

    extracted_collections = []
    relevant_contexts = []

    for file in files:
        queried_collections_this_file = []

        context = None
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
                for file_id in file_ids:
                    file_object = Files.get_file_by_id(file_id)

                    if file_object:
                        documents.append(file_object.data.get("content", ""))
                        metadatas.append(
                            {
                                "file_id": file_id,
                                "name": file_object.filename,
                                "source": file_object.filename,
                            }
                        )

                context = {
                    "documents": [documents],
                    "metadatas": [metadatas],
                }

            elif file.get("id"):
                file_object = Files.get_file_by_id(file.get("id"))
                if file_object:
                    context = {
                        "documents": [[file_object.data.get("content", "")]],
                        "metadatas": [
                            [
                                {
                                    "file_id": file.get("id"),
                                    "name": file_object.filename,
                                    "source": file_object.filename,
                                }
                            ]
                        ],
                    }
        else:
            collection_names = []
            if file.get("type") == "collection":
                if file.get("legacy"):
                    collection_names = file.get("collection_names", [])
                else:
                    collection_names.append(file["id"])
            elif file.get("collection_name"):
                collection_names.append(file["collection_name"])
            elif file.get("id"):
                if file.get("legacy"):
                    collection_names.append(f"{file['id']}")
                else:
                    collection_names.append(f"file-{file['id']}")

            collection_names = set(collection_names).difference(extracted_collections)
            if not collection_names:
                log.debug(f"skipping {file} as it has already been extracted")
                continue

            queried_collections_this_file = list(collection_names)

            # Log collection names being queried for debugging RAG issues
            log.info(f"[RAG Query] file_id={file.get('id')} | collection_names={queried_collections_this_file} | queries_count={len(queries)}")
            
            # Check if collections actually exist and have documents
            for coll_name in collection_names:
                try:
                    has_coll = VECTOR_DB_CLIENT.has_collection(collection_name=coll_name)
                    if not has_coll:
                        log.warning(
                            f"[RAG Query WARNING] Collection '{coll_name}' does not exist! "
                            f"File may not have been processed. Check file processing status."
                        )
                except Exception as check_err:
                    log.debug(f"Could not check collection existence: {check_err}")

            if full_context:
                try:
                    context = get_all_items_from_collections(collection_names)
                except Exception as e:
                    log.exception(e)

            else:
                try:
                    context = None
                    if file.get("type") == "text":
                        context = file["content"]
                    else:
                        if hybrid_search:
                            try:
                                context = query_collection_with_hybrid_search(
                                    collection_names=collection_names,
                                    queries=queries,
                                    embedding_function=embedding_function,
                                    k=k,
                                    reranking_function=reranking_function,
                                    r=r,
                                )
                            except Exception as e:
                                log.debug(
                                    "Error when using hybrid search, using"
                                    " non hybrid search as fallback."
                                )

                        if (not hybrid_search) or (context is None):
                            context = query_collection(
                                collection_names=collection_names,
                                queries=queries,
                                embedding_function=embedding_function,
                                k=k,
                            )
                            
                            # Log if no results were found for debugging
                            if context is None or not context.get("documents") or not context["documents"][0]:
                                log.warning(
                                    f"[RAG Query WARNING] No documents found for file_id={file.get('id')} | "
                                    f"collections={list(collection_names)} | "
                                    f"Possible causes: "
                                    f"1) File not processed yet (check processing_status), "
                                    f"2) Content extraction failed (empty PDF/scanned image), "
                                    f"3) Embedding failed during upload"
                                )
                except Exception as e:
                    log.exception(e)

            extracted_collections.extend(collection_names)

        if context:
            if "data" in file:
                del file["data"]

            # RAG debug: per-file retrieval result (which file, how many chunks retrieved)
            num_chunks = 0
            if context.get("documents") and context["documents"]:
                num_chunks = len(context["documents"][0])
            file_id = file.get("id", "")
            file_name = file.get("name") or file.get("filename")
            if not file_name:
                _file = file.get("file")
                if isinstance(_file, dict):
                    _data = _file.get("data")
                    if isinstance(_data, dict):
                        file_name = _data.get("name")
            if not file_name:
                file_name = f"collection:{file_id}" if file.get("type") == "collection" else str(file_id)
            file_name = str(file_name) if file_name else str(file_id)
            log.info(
                f"[RAG Retrieval] file_id={file_id} | file_name={file_name} | chunks_retrieved={num_chunks} | collections_queried={queried_collections_this_file}"
            )
            relevant_contexts.append({**context, "file": file})

    sources = []
    for context in relevant_contexts:
        try:
            if "documents" in context:
                if "metadatas" in context:
                    source = {
                        "source": context["file"],
                        "document": context["documents"][0],
                        "metadata": context["metadatas"][0],
                    }
                    if "distances" in context and context["distances"]:
                        source["distances"] = context["distances"][0]

                    sources.append(source)
        except Exception as e:
            log.exception(e)

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
    user: UserModel = None,
) -> Optional[list[list[float]]]:
    try:
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
            json={"input": texts, "model": model},
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


from typing import Optional, List, Union


def generate_portkey_embeddings_sdk(
    model: str,
    texts: Union[str, List[str]],
    base_url: str,
    api_key: str,
    encoding_format: str = "float",
) -> Union[List[float], List[List[float]]]:
    """
    Generate embeddings using Portkey Python SDK.
    
    This function uses the official Portkey SDK to generate embeddings for either
    a single string or a batch of strings. The SDK handles retries, error handling,
    and HTTP management automatically.
    
    Args:
        model: Portkey model identifier (e.g., "@openai-embedding/text-embedding-3-small")
        texts: Single string or list of strings to embed
        base_url: Portkey API base URL (e.g., "https://ai-gateway.apps.cloud.rt.nyu.edu/v1")
        api_key: Portkey API key
        encoding_format: "float" for uncompressed embeddings (default)
        
    Returns:
        list[float] if texts is a single string
        list[list[float]] if texts is a list of strings
        
    Raises:
        ImportError: If portkey_ai SDK is not installed
        Exception: For any Portkey API errors (handled by SDK)
    """
    if not PORTKEY_SDK_AVAILABLE:
        raise ImportError(
            "Portkey SDK (portkey_ai) is not installed. "
            "Install it with: pip install portkey-ai"
        )
    
    # Log API key status for debugging (masked for security)
    key_status = "EMPTY" if not api_key else f"set ({len(api_key)} chars, ends with ...{api_key[-4:] if len(api_key) >= 4 else '***'})"
    log.info(
        f"Portkey SDK init: base_url={base_url}, api_key={key_status}"
    )
    
    if not api_key:
        log.error(
            "Portkey API key is empty! This will result in 401 Unauthorized. "
            "Ensure the admin has configured an embedding API key in Settings > Documents."
        )
    
    # Initialize Portkey client (simple - no deprecated virtual_key)
    portkey = Portkey(
        base_url=base_url,
        api_key=api_key
    )
    
    # Generate embeddings using SDK
    # The SDK handles retries, rate limiting, and error handling automatically
    # CRITICAL: Azure OpenAI (via Portkey) has a limit of 2048 items per request
    # We need to batch large requests into chunks of max 2048 items
    MAX_BATCH_SIZE = 2048
    
    try:
        # Convert single string to list for uniform processing
        is_single_string = isinstance(texts, str)
        if is_single_string:
            texts_list = [texts]
        elif isinstance(texts, list):
            texts_list = texts
        else:
            raise ValueError(f"Invalid input type: {type(texts)}. Expected str or list[str]")
        
        texts_count = len(texts_list)
        
        # CRITICAL: Validate input format and log detailed diagnostics
        log.info(
            f"Portkey embedding input validation: "
            f"input_type={type(texts)}, "
            f"texts_count={texts_count}, "
            f"is_list={isinstance(texts_list, list)}"
        )
        
        # Sample first few items to diagnose format issues
        sample_items = []
        non_string_count = 0
        empty_count = 0
        very_short_count = 0  # Items with length <= 1
        
        for i, text in enumerate(texts_list[:10]):  # Check first 10 items
            if not isinstance(text, str):
                non_string_count += 1
                sample_items.append(f"idx{i}:{type(text).__name__}={text!r}")
            elif len(text.strip()) == 0:
                empty_count += 1
                sample_items.append(f"idx{i}:EMPTY")
            elif len(text) <= 1:
                very_short_count += 1
                sample_items.append(f"idx{i}:LEN{len(text)}={text!r}")
            else:
                preview = text[:50].replace("\n", " ") + ("..." if len(text) > 50 else "")
                sample_items.append(f"idx{i}:LEN{len(text)}={preview!r}")
        
        # Check beyond first 10 for patterns
        for i in range(10, min(100, texts_count)):
            text = texts_list[i]
            if not isinstance(text, str):
                non_string_count += 1
            elif len(text.strip()) == 0:
                empty_count += 1
            elif len(text) <= 1:
                very_short_count += 1
        
        log.warning(
            f"Portkey input diagnostics: "
            f"non_string_items={non_string_count}, "
            f"empty_items={empty_count}, "
            f"very_short_items(<=1char)={very_short_count}, "
            f"sample_items={sample_items[:5]}"
        )
        
        # Validate all items are strings
        for i, text in enumerate(texts_list):
            if not isinstance(text, str):
                raise ValueError(
                    f"Item at index {i} is not a string: {type(text)}={text!r}. "
                    f"This suggests incorrect chunking or document processing."
                )
            if not text.strip():
                log.warning(f"Empty string at index {i} - may cause API errors")
        
        # Warn if most items are very short (suggests character-level chunking bug)
        if texts_count > 100 and very_short_count > texts_count * 0.9:
            error_msg = (
                f"CRITICAL: {very_short_count}/{texts_count} items are <=1 character. "
                f"This suggests chunk_size=0 or character-level splitting bug. "
                f"Check chunk_size configuration (should be >0, typically 500-2000)."
            )
            log.error(error_msg)
            raise ValueError(error_msg)
        
        # Log a concise view of the request payload
        if texts_list:
            first_str = texts_list[0][:80].replace("\n", " ") + ("..." if len(texts_list[0]) > 80 else "")
            avg_len = sum(len(t) for t in texts_list[:100]) / min(100, texts_count)
        else:
            first_str = "<empty>"
            avg_len = 0
        
        log.info(
            f"Generating Portkey embeddings via SDK: "
            f"model={model}, "
            f"texts_count={texts_count}, "
            f"avg_text_length={avg_len:.1f}, "
            f"encoding_format={encoding_format}, "
            f"sample_preview={first_str!r}, "
            f"will_batch={texts_count > MAX_BATCH_SIZE}"
        )
        
        # Batch processing for large requests
        if texts_count <= MAX_BATCH_SIZE:
            # Single batch - process all at once
            # Log complete request payload details
            sample_texts = [t[:50].replace("\n", " ") + ("..." if len(t) > 50 else "") for t in texts_list[:5]]
            log.info(
                f"[Portkey Request Payload]\n"
                f"  Settings:\n"
                f"    model: {model}\n"
                f"    base_url: {base_url}\n"
                f"    api_key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'} (len={len(api_key)})\n"
                f"    encoding_format: {encoding_format}\n"
                f"  Payload:\n"
                f"    input_type: {type(texts_list).__name__}\n"
                f"    input_length: {texts_count}\n"
                f"    input_shape: [{texts_count}]\n"
                f"    avg_text_len: {sum(len(t) for t in texts_list) / texts_count:.1f}\n"
                f"    min_text_len: {min(len(t) for t in texts_list)}\n"
                f"    max_text_len: {max(len(t) for t in texts_list)}\n"
                f"    sample_texts (first 5): {sample_texts}"
            )
            response = portkey.embeddings.create(
                model=model,
                input=texts_list,
                encoding_format=encoding_format
            )
            
            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]
        else:
            # Multiple batches needed - process in chunks
            log.info(f"Batching {texts_count} texts into chunks of {MAX_BATCH_SIZE} for Azure OpenAI limit")
            all_embeddings = []
            
            for i in range(0, texts_count, MAX_BATCH_SIZE):
                batch = texts_list[i:i + MAX_BATCH_SIZE]
                batch_num = (i // MAX_BATCH_SIZE) + 1
                total_batches = (texts_count + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
                sample_batch = [t[:50].replace("\n", " ") + ("..." if len(t) > 50 else "") for t in batch[:3]]
                log.info(
                    f"[Portkey Batch {batch_num}/{total_batches}]\n"
                    f"  Settings: model={model}, base_url={base_url}, api_key={api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}, encoding={encoding_format}\n"
                    f"  Payload: input_length={len(batch)}, shape=[{len(batch)}], avg_len={sum(len(t) for t in batch) / len(batch):.1f}\n"
                    f"  Sample (first 3): {sample_batch}"
                )
                response = portkey.embeddings.create(
                    model=model,
                    input=batch,
                    encoding_format=encoding_format
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            embeddings = all_embeddings
        
        # Validate embeddings were generated
        if not embeddings:
            raise ValueError("No embeddings returned from Portkey SDK")
        
        if len(embeddings) != texts_count:
            raise ValueError(
                f"Embedding count mismatch: expected {texts_count}, got {len(embeddings)}"
            )
        
        # Return single embedding for single string, list for batch
        if is_single_string:
            if len(embeddings) == 0:
                raise ValueError("Expected at least one embedding for single text input")
            return embeddings[0]
        return embeddings
        
    except Exception as e:
        log.exception(f"Error generating Portkey embeddings via SDK: {e}")
        raise


def generate_ollama_batch_embeddings(
    model: str, texts: list[str], url: str, key: str = "", user: UserModel = None
) -> Optional[list[list[float]]]:
    try:
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
            json={"input": texts, "model": model},
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
    engine: str, model: str, text: Union[str, list[str]], backoff: bool, **kwargs
):
    """
    Generate embeddings using the specified engine.
    
    This function routes embedding requests to the appropriate engine implementation.
    For Portkey, it uses the official Python SDK for clean, maintainable code.
    
    Args:
        engine: Embedding engine ("ollama", "openai", "portkey", or "" for local)
        model: Model identifier (e.g., "@openai-embedding/text-embedding-3-small")
        text: Single string or list of strings to embed
        backoff: Whether to use exponential backoff (for legacy compatibility)
        **kwargs: Additional engine-specific parameters:
            - url: API base URL
            - key: API key
            - user: UserModel instance
            
    Returns:
        list[float] if text is a single string
        list[list[float]] if text is a list of strings
    """
    url = kwargs.get("url", "")
    key = kwargs.get("key", "")
    user = kwargs.get("user")
    user_email = user.email if user and hasattr(user, 'email') else "(no user)"
    text_count = len(text) if isinstance(text, list) else 1
    log.info(f"[GENERATE_EMBEDDINGS] START | engine={engine} | model={model} | texts_count={text_count} | url={url} | key={key} | user={user_email}")
    
    # CRITICAL FIX: For portkey/openai engines, dynamically retrieve the user's API key
    # The `key` passed in may be the startup default (empty), but users configure their own keys
    # This ensures per-user API key scoping works correctly for RAG queries
    if engine in ["openai", "portkey"] and user and hasattr(user, 'email') and user.email:
        try:
            from open_webui.config import RAG_OPENAI_API_KEY
            user_key = RAG_OPENAI_API_KEY.get(user.email)
            if user_key:
                log.debug(f"Using per-user API key for {user.email} (key length: {len(user_key)})")
                key = user_key
            else:
                log.warning(f"No embedding API key found for user {user.email} - using default (may be empty)")
        except Exception as e:
            log.warning(f"Failed to retrieve per-user API key: {e}")

    if engine == "ollama":
        if isinstance(text, list):
            embeddings = generate_ollama_batch_embeddings(
                **{"model": model, "texts": text, "url": url, "key": key, "user": user}
            )
        else:
            embeddings = generate_ollama_batch_embeddings(
                **{
                    "model": model,
                    "texts": [text],
                    "url": url,
                    "key": key,
                    "user": user,
                }
            )
        emb_count = len(embeddings) if isinstance(embeddings, list) else 1
        log.info(f"[GENERATE_EMBEDDINGS] SUCCESS | engine=ollama | model={model} | embeddings_count={emb_count} | user={user_email}")
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "openai":
        if isinstance(text, list):
            embeddings = generate_openai_batch_embeddings(model, text, url, key, user)
        else:
            embeddings = generate_openai_batch_embeddings(model, [text], url, key, user)

        emb_count = len(embeddings) if isinstance(embeddings, list) else 1
        log.info(f"[GENERATE_EMBEDDINGS] SUCCESS | engine=openai | model={model} | embeddings_count={emb_count} | user={user_email}")
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "portkey":
        # Use SDK-based implementation
        embeddings = generate_portkey_embeddings_sdk(
            model=model,
            texts=text,
            base_url=url,
            api_key=key,
            encoding_format="float"
        )
        emb_count = len(embeddings) if isinstance(embeddings, list) else 1
        log.info(f"[GENERATE_EMBEDDINGS] SUCCESS | engine={engine} | model={model} | embeddings_count={emb_count} | user={user_email}")
        return embeddings
    else:
        log.error(f"[GENERATE_EMBEDDINGS] ERROR | unknown engine={engine}")
        raise ValueError(f"Unknown embedding engine: {engine}")


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

            query_embedding = self.embedding_function(query)
            document_embedding = self.embedding_function(
                [doc.page_content for doc in documents]
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        docs_with_scores = list(zip(documents, scores.tolist()))
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
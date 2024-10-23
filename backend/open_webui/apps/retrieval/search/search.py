import logging

from langchain.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_community.retrievers import BM25Retriever

from open_webui.apps.retrieval.search.rerank import RerankCompressor
from open_webui.apps.retrieval.search.retriever import VectorSearchRetriever
from open_webui.apps.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.apps.retrieval.web.brave import search_brave
from open_webui.apps.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.apps.retrieval.web.google_pse import search_google_pse
from open_webui.apps.retrieval.web.jina_search import search_jina
from open_webui.apps.retrieval.web.main import SearchResult
from open_webui.apps.retrieval.web.searchapi import search_searchapi
from open_webui.apps.retrieval.web.searxng import search_searxng
from open_webui.apps.retrieval.web.serper import search_serper
from open_webui.apps.retrieval.web.serply import search_serply
from open_webui.apps.retrieval.web.serpstack import search_serpstack
from open_webui.apps.retrieval.web.tavily import search_tavily
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.misc import get_last_user_message

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def _merge_and_sort_query_results(
    query_results: list[dict], k: int, reverse: bool = False
) -> list[dict]:
    # Initialize lists to store combined data
    combined_distances = []
    combined_documents = []
    combined_metadatas = []

    for data in query_results:
        combined_distances.extend(data["distances"][0])
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])

    # Create a list of tuples (distance, document, metadata)
    combined = list(zip(combined_distances, combined_documents, combined_metadatas))

    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=reverse)

    # We don't have anything :-(
    if not combined:
        sorted_distances = []
        sorted_documents = []
        sorted_metadatas = []
    else:
        # Unzip the sorted list
        sorted_distances, sorted_documents, sorted_metadatas = zip(*combined)

        # Slicing the lists to include only k elements
        sorted_distances = list(sorted_distances)[:k]
        sorted_documents = list(sorted_documents)[:k]
        sorted_metadatas = list(sorted_metadatas)[:k]

    # Create the output dictionary
    result = {
        "distances": [sorted_distances],
        "documents": [sorted_documents],
        "metadatas": [sorted_metadatas],
    }

    return result


def query_collection(
    collection_names: list[str],
    query: str,
    embedding_function,
    k: int,
) -> dict:
    results = []
    query_embedding = embedding_function(query)

    for collection_name in collection_names:
        if collection_name:
            try:
                result = query_doc(
                    collection_name=collection_name,
                    k=k,
                    query_embedding=query_embedding,
                )
                if result is not None:
                    results.append(result.model_dump())
            except Exception as e:
                log.exception(f"Error when querying the collection: {e}")
        else:
            pass

    return _merge_and_sort_query_results(results, k=k)


def query_collection_with_hybrid_search(
    collection_names: list[str],
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
) -> dict:
    results = []
    error = False
    for collection_name in collection_names:
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                query=query,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                r=r,
            )
            results.append(result)
        except Exception as e:
            log.exception(
                "Error when querying the collection with " f"hybrid_search: {e}"
            )
            error = True

    if error:
        raise Exception(
            "Hybrid search failed for all collections. Using Non hybrid search as fallback."
        )

    return _merge_and_sort_query_results(results, k=k, reverse=True)


def query_doc(
    collection_name: str,
    query_embedding: list[float],
    k: int,
):
    try:
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        log.info(f"query_doc:result {result}")
        return result
    except Exception as e:
        print(e)
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

        log.info(f"query_doc_with_hybrid_search:result {result}")
        return result
    except Exception as e:
        raise e


def get_rag_context(
    files,
    messages,
    embedding_function,
    k,
    reranking_function,
    r,
    hybrid_search,
):
    log.debug(f"files: {files} {messages} {embedding_function} {reranking_function}")
    query = get_last_user_message(messages)

    extracted_collections = []
    relevant_contexts = []

    for file in files:
        if file.get("context") == "full":
            context = {
                "documents": [[file.get("file").get("data", {}).get("content")]],
                "metadatas": [[{"file_id": file.get("id"), "name": file.get("name")}]],
            }
        else:
            context = None

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

            try:
                context = None
                if file.get("type") == "text":
                    context = file["content"]
                else:
                    if hybrid_search:
                        try:
                            context = query_collection_with_hybrid_search(
                                collection_names=collection_names,
                                query=query,
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
                            query=query,
                            embedding_function=embedding_function,
                            k=k,
                        )
            except Exception as e:
                log.exception(e)

            extracted_collections.extend(collection_names)

        if context:
            if "data" in file:
                del file["data"]
            relevant_contexts.append({**context, "file": file})

    contexts = []
    citations = []
    for context in relevant_contexts:
        try:
            if "documents" in context:
                file_names = list(
                    set(
                        [
                            metadata["name"]
                            for metadata in context["metadatas"][0]
                            if metadata is not None and "name" in metadata
                        ]
                    )
                )
                contexts.append(
                    ((", ".join(file_names) + ":\n\n") if file_names else "")
                    + "\n\n".join(
                        [text for text in context["documents"][0] if text is not None]
                    )
                )

                if "metadatas" in context:
                    citation = {
                        "source": context["file"],
                        "document": context["documents"][0],
                        "metadata": context["metadatas"][0],
                    }
                    if "distances" in context and context["distances"]:
                        citation["distances"] = context["distances"][0]
                    citations.append(citation)
        except Exception as e:
            log.exception(e)

    print("contexts", contexts)
    print("citations", citations)

    return contexts, citations


def search_web(state, query: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default `google`)
    Args:
        query (str): The query to search for
    """

    engine = state.config.RAG_WEB_SEARCH_ENGINE

    # TODO: add playwright to search the web
    if engine == "searxng":
        if state.config.SEARXNG_QUERY_URL:
            return search_searxng(
                state.config.SEARXNG_QUERY_URL,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARXNG_QUERY_URL found in environment variables")
    elif engine == "google_pse":
        if state.config.GOOGLE_PSE_API_KEY and state.config.GOOGLE_PSE_ENGINE_ID:
            return search_google_pse(
                state.config.GOOGLE_PSE_API_KEY,
                state.config.GOOGLE_PSE_ENGINE_ID,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
            )
    elif engine == "brave":
        if state.config.BRAVE_SEARCH_API_KEY:
            return search_brave(
                state.config.BRAVE_SEARCH_API_KEY,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
    elif engine == "serpstack":
        if state.config.SERPSTACK_API_KEY:
            return search_serpstack(
                state.config.SERPSTACK_API_KEY,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=state.config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception("No SERPSTACK_API_KEY found in environment variables")
    elif engine == "serper":
        if state.config.SERPER_API_KEY:
            return search_serper(
                state.config.SERPER_API_KEY,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPER_API_KEY found in environment variables")
    elif engine == "serply":
        if state.config.SERPLY_API_KEY:
            return search_serply(
                state.config.SERPLY_API_KEY,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPLY_API_KEY found in environment variables")
    elif engine == "duckduckgo":
        return search_duckduckgo(
            query,
            state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "tavily":
        if state.config.TAVILY_API_KEY:
            return search_tavily(
                state.config.TAVILY_API_KEY,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            )
        else:
            raise Exception("No TAVILY_API_KEY found in environment variables")
    elif engine == "searchapi":
        if state.config.SEARCHAPI_API_KEY:
            return search_searchapi(
                state.config.SEARCHAPI_API_KEY,
                state.config.SEARCHAPI_ENGINE,
                query,
                state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARCHAPI_API_KEY found in environment variables")
    elif engine == "jina":
        return search_jina(query, state.config.RAG_WEB_SEARCH_RESULT_COUNT)
    else:
        raise Exception("No search engine API key found in environment variables")

import logging
import os
import operator
from typing import Optional, Union, Sequence, Any

import asyncio
import requests
import concurrent.futures

from huggingface_hub import snapshot_download
from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document

from open_webui.config import VECTOR_DB
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.retrieval.models.jina_remote import JinaRemoteReranker
from open_webui.utils.misc import measure_time

from open_webui.models.users import UserModel

from open_webui.env import (
    SRC_LOG_LEVELS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)

from open_webui.models.documents import DocumentDBs

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class VectorSearchRetriever(BaseRetriever):
    collection_name: Any
    embedding_function: Any
    top_k: int
    enable_hybrid_search: bool = False

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        result = VECTOR_DB_CLIENT.search(
            collection_name=self.collection_name,
            vectors=[self.embedding_function(query)],
            queries=[query],
            limit=self.top_k,
            enable_hybrid_search=self.enable_hybrid_search,
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
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[query_embedding],
            limit=k,
        )

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        print(e)
        raise e


def get_doc(collection_name: str, user: UserModel = None):
    try:
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        if result:
            log.info(f"query_doc:result {result.ids} {result.metadatas}")

        return result
    except Exception as e:
        print(e)
        raise e


@measure_time
def query_doc_with_hybrid_search(
    collection_name: str,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
) -> dict:
    try:    
        # Vector search retriever will use hybrid search to retrieve the top k documents
        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
            enable_hybrid_search=True,
        )

        # Reranking compressor will rerank the documents based on the reranking function 
        # and return the top n documents
        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k,
            reranking_function=reranking_function,
            r_score=r,
        )

        # Contextual compression retriever will:
        ## 1. Use the vector search retriever to retrieve the top k documents
        ## 2. Use the reranking compressor to rerank the documents
        ## 3. Return the top n documents
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=vector_search_retriever
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
    results = []
    
    # Create work items
    work_items = []
    for query in queries:
        # TODO: Improve this by running batch embedding instead. Not have time for now ^^
        query_embedding = embedding_function(query)
        for collection_name in collection_names:
            if collection_name:
                work_items.append((collection_name, query_embedding))

    # Use thread pool to execute queries in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(work_items), 10)) as executor:
        futures = [
            executor.submit(query_doc, name, emb, k)
            for name, emb in work_items
        ]
        
        # Gather results as they complete
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result.model_dump())

    if VECTOR_DB == "chroma":
        # Chroma uses unconventional cosine similarity, so we don't need to reverse the results
        # https://docs.trychroma.com/docs/collections/configure#configuring-chroma-collections
        return merge_and_sort_query_results(results, k=k, reverse=False)
    else:
        return merge_and_sort_query_results(results, k=k, reverse=True)


@measure_time
def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    r: float,
) -> dict:
    results = []
    error = False
    
    log.info(f"query_collection_with_hybrid_search:collection_names {collection_names}")
    log.info(f"query_collection_with_hybrid_search:queries {queries}") 
    
    # Create work items
    work_items = []
    for collection_name in collection_names:
        for query in queries:
            work_items.append((collection_name, query))
    
    # Use thread pool to execute queries in parallel
    ## Note: Because most of our work is IO bound, we can use a thread pool to execute the queries in parallel
    ## If you have a CPU bound work, you should use a process pool instead
    num_workers = min(len(work_items), 10)
    log.info(f"query_collection_with_hybrid_search:num_workers {num_workers}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                query_doc_with_hybrid_search,
                collection_name,
                query,
                embedding_function,
                k,
                reranking_function,
                r
            )
            for collection_name, query in work_items
        ]
        
        # Gather results as they complete
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
                
    log.info(f"query_collection_with_hybrid_search:total search result {len(results)}")

    if error:
        raise Exception(
            "Hybrid search failed for all collections. Using Non hybrid search as fallback."
        )

    if VECTOR_DB == "chroma":
        # Chroma uses unconventional cosine similarity, so we don't need to reverse the results
        # https://docs.trychroma.com/docs/collections/configure#configuring-chroma-collections
        return merge_and_sort_query_results(results, k=k, reverse=False)
    else:
        return merge_and_sort_query_results(results, k=k, reverse=True)


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
):
    if embedding_engine == "":
        return lambda query, user=None: embedding_function.encode(query).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        func = lambda query, user=None: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            url=url,
            key=key,
            user=user,
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

@measure_time
def get_sources_from_files(
    files,
    queries,
    embedding_function,
    k,
    reranking_function,
    r,
    hybrid_search,
    enable_parent_retriever,
    full_context=False,
):
    log.debug(
        f"files: {files} {queries} {embedding_function} {reranking_function} {full_context}"
    )

    extracted_collections = []
    relevant_contexts = []

    for file in files:
        if file.get("docs"):
            context = {
                "documents": [[doc.get("content") for doc in file.get("docs")]],
                "metadatas": [[doc.get("metadata") for doc in file.get("docs")]],
            }
        elif file.get("context") == "full":
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
                except Exception as e:
                    log.exception(e)

            extracted_collections.extend(collection_names)

        if context:
            if "data" in file:
                del file["data"]
            relevant_contexts.append({**context, "file": file})

    sources = []
    for context in relevant_contexts:
        try:
            if "documents" in context:
                if "metadatas" in context:
                    metadatas = context["metadatas"][0]
                    document = context["documents"][0]
                    distances = (
                        context["distances"][0]
                        if "distances" in context and context["distances"]
                        else None
                    )

                    parent_ids = [item.get("parent_id") for item in metadatas]
                    if enable_parent_retriever:
                        new_metadatas = []
                        new_document = []
                        new_distances = [] if distances else None

                        processed_parent_ids = []

                        for idx, parent_id in enumerate(parent_ids):
                            if parent_id and parent_id in processed_parent_ids:
                                continue
                            processed_parent_ids.append(parent_id)
                            new_metadatas.append(metadatas[idx])

                            if distances:
                                new_distances.append(distances[idx])

                            parent_doc = (
                                DocumentDBs.get_document_by_id(parent_id)
                                if parent_id
                                else None
                            )
                            
                            new_document.append(
                                parent_doc.page_content if parent_doc else document[idx]
                            )
                            print(f'parent_id {parent_id}, len of child chunk {len(document[idx])}, len of parent {len(parent_doc.page_content) if parent_doc else 0}')

                        document = new_document
                        metadatas = new_metadatas
                        distances = new_distances

                    source = {
                        "source": context["file"],
                        "document": document,
                        "metadata": metadatas,
                        "distances": distances,
                    }

                    sources.append(source)
        except Exception as e:
            log.exception(e)

    print("sourcessources221", sources)
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
        print(e)
        return None


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
        print(e)
        return None


def generate_embeddings(engine: str, model: str, text: Union[str, list[str]], **kwargs):
    url = kwargs.get("url", "")
    key = kwargs.get("key", "")
    user = kwargs.get("user")

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
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "openai":
        if isinstance(text, list):
            embeddings = generate_openai_batch_embeddings(model, text, url, key, user)
        else:
            embeddings = generate_openai_batch_embeddings(model, [text], url, key, user)

        return embeddings[0] if isinstance(text, str) else embeddings
    
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
        # We need to separate the jina remote reranker
        # because Jina api call already sort the documents and get the top n results 
        if isinstance(self.reranking_function, JinaRemoteReranker):
            # Get the index and score of the documents
            index_with_scores = self.reranking_function.predict(
                query=query,
                documents=[doc.page_content for doc in documents],
                top_n=self.top_n,
            )
            
            # Filter the documents with the score greater than the r_score
            if self.r_score:
                index_with_scores = [
                    (idx, s) for idx, s in index_with_scores if s >= self.r_score
                ]
                
            # Create the final results
            final_results = []
            for doc_idx, doc_score in index_with_scores:
                metadata = documents[doc_idx].metadata
                metadata["score"] = doc_score
                doc = Document(
                    page_content=documents[doc_idx].page_content,
                    metadata=metadata,
                )
                final_results.append(doc)
                
            return final_results
            
        else:    
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

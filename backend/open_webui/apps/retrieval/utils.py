import logging
import os
import uuid
from typing import Optional, Union

import asyncio
import requests

from huggingface_hub import snapshot_download
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from open_webui.apps.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.utils.misc import get_last_user_message

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
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

        log.info(f"query_doc:result {result.ids} {result.metadatas}")
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

        log.info(
            "query_doc_with_hybrid_search:result "
            + f'{result["metadatas"]} {result["distances"]}'
        )
        return result
    except Exception as e:
        raise e


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


def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    results = []
    for query in queries:
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

    return merge_and_sort_query_results(results, k=k)


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
    for collection_name in collection_names:
        try:
            for query in queries:
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
        return lambda query: embedding_function.encode(query).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        func = lambda query: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            url=url,
            key=key,
        )

        def generate_multiple(query, func):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    embeddings.extend(func(query[i : i + embedding_batch_size]))
                return embeddings
            else:
                return func(query)

        return lambda query: generate_multiple(query, func)


def get_sources_from_files(
    files,
    queries,
    embedding_function,
    k,
    reranking_function,
    r,
    hybrid_search,
):
    log.debug(f"files: {files} {queries} {embedding_function} {reranking_function}")

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
    model: str, texts: list[str], url: str = "https://api.openai.com/v1", key: str = ""
) -> Optional[list[list[float]]]:
    try:
        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
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
    model: str, texts: list[str], url: str, key: str = ""
) -> Optional[list[list[float]]]:
    try:
        r = requests.post(
            f"{url}/api/embed",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
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

    if engine == "ollama":
        if isinstance(text, list):
            embeddings = generate_ollama_batch_embeddings(
                **{"model": model, "texts": text, "url": url, "key": key}
            )
        else:
            embeddings = generate_ollama_batch_embeddings(
                **{"model": model, "texts": [text], "url": url, "key": key}
            )
        return embeddings[0] if isinstance(text, str) else embeddings
    elif engine == "openai":
        if isinstance(text, list):
            embeddings = generate_openai_batch_embeddings(model, text, url, key)
        else:
            embeddings = generate_openai_batch_embeddings(model, [text], url, key)

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

import os
import logging
import requests

from typing import List

from apps.ollama.main import (
    generate_ollama_embeddings,
    GenerateEmbeddingsForm,
)

from huggingface_hub import snapshot_download

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)

from typing import Optional
from config import SRC_LOG_LEVELS, CHROMA_CLIENT


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def query_doc(
    collection_name: str,
    query: str,
    embedding_function,
    k: int,
):
    try:
        collection = CHROMA_CLIENT.get_collection(name=collection_name)
        query_embeddings = embedding_function(query)

        result = collection.query(
            query_embeddings=[query_embeddings],
            n_results=k,
        )

        log.info(f"query_doc:result {result}")
        return result
    except Exception as e:
        raise e


def query_doc_with_hybrid_search(
    collection_name: str,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
):
    try:
        collection = CHROMA_CLIENT.get_collection(name=collection_name)
        documents = collection.get()  # get all documents

        bm25_retriever = BM25Retriever.from_texts(
            texts=documents.get("documents"),
            metadatas=documents.get("metadatas"),
        )
        bm25_retriever.k = k

        chroma_retriever = ChromaRetriever(
            collection=collection,
            embedding_function=embedding_function,
            top_n=k,
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, chroma_retriever], weights=[0.5, 0.5]
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


def merge_and_sort_query_results(query_results, k, reverse=False):
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
    collection_names: List[str],
    query: str,
    embedding_function,
    k: int,
):
    results = []
    for collection_name in collection_names:
        try:
            result = query_doc(
                collection_name=collection_name,
                query=query,
                k=k,
                embedding_function=embedding_function,
            )
            results.append(result)
        except:
            pass
    return merge_and_sort_query_results(results, k=k)


def query_collection_with_hybrid_search(
    collection_names: List[str],
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
):
    results = []
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
        except:
            pass
    return merge_and_sort_query_results(results, k=k, reverse=True)


def rag_template(template: str, context: str, query: str):
    template = template.replace("[context]", context)
    template = template.replace("[query]", query)
    return template


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    openai_key,
    openai_url,
):
    if embedding_engine == "":
        return lambda query: embedding_function.encode(query).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        if embedding_engine == "ollama":
            func = lambda query: generate_ollama_embeddings(
                GenerateEmbeddingsForm(
                    **{
                        "model": embedding_model,
                        "prompt": query,
                    }
                )
            )
        elif embedding_engine == "openai":
            func = lambda query: generate_openai_embeddings(
                model=embedding_model,
                text=query,
                key=openai_key,
                url=openai_url,
            )

        def generate_multiple(query, f):
            if isinstance(query, list):
                return [f(q) for q in query]
            else:
                return f(query)

        return lambda query: generate_multiple(query, func)


def rag_messages(
    docs,
    messages,
    template,
    embedding_function,
    k,
    reranking_function,
    r,
    hybrid_search,
):
    log.debug(f"docs: {docs} {messages} {embedding_function} {reranking_function}")

    last_user_message_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            last_user_message_idx = i
            break

    user_message = messages[last_user_message_idx]

    if isinstance(user_message["content"], list):
        # Handle list content input
        content_type = "list"
        query = ""
        for content_item in user_message["content"]:
            if content_item["type"] == "text":
                query = content_item["text"]
                break
    elif isinstance(user_message["content"], str):
        # Handle text content input
        content_type = "text"
        query = user_message["content"]
    else:
        # Fallback in case the input does not match expected types
        content_type = None
        query = ""

    extracted_collections = []
    relevant_contexts = []

    for doc in docs:
        context = None

        collection_names = (
            doc["collection_names"]
            if doc["type"] == "collection"
            else [doc["collection_name"]]
        )

        collection_names = set(collection_names).difference(extracted_collections)
        if not collection_names:
            log.debug(f"skipping {doc} as it has already been extracted")
            continue

        try:
            if doc["type"] == "text":
                context = doc["content"]
            else:
                if hybrid_search:
                    context = query_collection_with_hybrid_search(
                        collection_names=collection_names,
                        query=query,
                        embedding_function=embedding_function,
                        k=k,
                        reranking_function=reranking_function,
                        r=r,
                    )
                else:
                    context = query_collection(
                        collection_names=collection_names,
                        query=query,
                        embedding_function=embedding_function,
                        k=k,
                    )
        except Exception as e:
            log.exception(e)
            context = None

        if context:
            relevant_contexts.append({**context, "source": doc})

        extracted_collections.extend(collection_names)

    context_string = ""

    citations = []
    for context in relevant_contexts:
        try:
            if "documents" in context:
                context_string += "\n\n".join(
                    [text for text in context["documents"][0] if text is not None]
                )

                if "metadatas" in context:
                    citations.append(
                        {
                            "source": context["source"],
                            "document": context["documents"][0],
                            "metadata": context["metadatas"][0],
                        }
                    )
        except Exception as e:
            log.exception(e)

    context_string = context_string.strip()

    ra_content = rag_template(
        template=template,
        context=context_string,
        query=query,
    )

    log.debug(f"ra_content: {ra_content}")

    if content_type == "list":
        new_content = []
        for content_item in user_message["content"]:
            if content_item["type"] == "text":
                # Update the text item's content with ra_content
                new_content.append({"type": "text", "text": ra_content})
            else:
                # Keep other types of content as they are
                new_content.append(content_item)
        new_user_message = {**user_message, "content": new_content}
    else:
        new_user_message = {
            **user_message,
            "content": ra_content,
        }

    messages[last_user_message_idx] = new_user_message

    return messages, citations


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


def generate_openai_embeddings(
    model: str, text: str, key: str, url: str = "https://api.openai.com/v1"
):
    try:
        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json={"input": text, "model": model},
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return data["data"][0]["embedding"]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        print(e)
        return None


from typing import Any

from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun


class ChromaRetriever(BaseRetriever):
    collection: Any
    embedding_function: Any
    top_n: int

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        query_embeddings = self.embedding_function(query)

        results = self.collection.query(
            query_embeddings=[query_embeddings],
            n_results=self.top_n,
        )

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]

        results = []
        for idx in range(len(ids)):
            results.append(
                Document(
                    metadata=metadatas[idx],
                    page_content=documents[idx],
                )
            )
        return results


import operator

from typing import Optional, Sequence

from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.callbacks import Callbacks
from langchain_core.pydantic_v1 import Extra

from sentence_transformers import util


class RerankCompressor(BaseDocumentCompressor):
    embedding_function: Any
    top_n: int
    reranking_function: Any
    r_score: float

    class Config:
        extra = Extra.forbid
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

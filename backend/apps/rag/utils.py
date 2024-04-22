import logging
import requests
import operator

import sentence_transformers

from typing import List

from apps.ollama.main import (
    generate_ollama_embeddings,
    GenerateEmbeddingsForm,
)

from langchain.retrievers import (
    BM25Retriever,
    EnsembleRetriever,
)

from config import SRC_LOG_LEVELS, CHROMA_CLIENT


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def query_embeddings_doc(
    collection_name: str,
    query: str,
    k: int,
    embeddings_function,
    reranking_function,
):
    try:
        # if you use docker use the model from the environment variable
        collection = CHROMA_CLIENT.get_collection(name=collection_name)

        # keyword search
        documents = collection.get() # get all documents
        bm25_retriever = BM25Retriever.from_texts(
            texts=documents.get("documents"),
            metadatas=documents.get("metadatas"),
        )
        bm25_retriever.k = k

        # semantic search (vector)
        chroma_retriever = ChromaRetriever(
            collection=collection,
            k=k,
            embeddings_function=embeddings_function,
        )

        # hybrid search (ensemble)
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, chroma_retriever],
            weights=[0.6, 0.4]
        )

        documents = ensemble_retriever.invoke(query)
        result = query_results_rank(
            query=query,
            documents=documents,
            k=k,
            reranking_function=reranking_function,
        )
        result = {
            "distances": [[d[1].item() for d in result]],
            "documents": [[d[0].page_content for d in result]],
            "metadatas": [[d[0].metadata for d in result]],
        }

        return result
    except Exception as e:
        raise e


def query_results_rank(query: str, documents, k: int, reranking_function):
    scores = reranking_function.predict([(query, doc.page_content) for doc in documents])
    docs_with_scores = list(zip(documents, scores))
    result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
    return result[: k]


def merge_and_sort_query_results(query_results, k):
    # Initialize lists to store combined data
    combined_distances = []
    combined_documents = []
    combined_metadatas = []

    # Combine data from each dictionary
    for data in query_results:
        combined_distances.extend(data["distances"][0])
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])

    # Create a list of tuples (distance, document, metadata)
    combined = list(
        zip(combined_distances, combined_documents, combined_metadatas)
    )

    # Sort the list based on distances
    combined.sort(key=lambda x: x[0])

    # Unzip the sorted list
    sorted_distances, sorted_documents, sorted_metadatas = zip(*combined)

    # Slicing the lists to include only k elements
    sorted_distances = list(sorted_distances)[:k]
    sorted_documents = list(sorted_documents)[:k]
    sorted_metadatas = list(sorted_metadatas)[:k]

    # Create the output dictionary
    merged_query_results = {
        "distances": [sorted_distances],
        "documents": [sorted_documents],
        "metadatas": [sorted_metadatas],
        "embeddings": None,
        "uris": None,
        "data": None,
    }

    return merged_query_results


def query_embeddings_collection(
    collection_names: List[str],
    query: str,
    k: int,
    embeddings_function,
    reranking_function,
):

    results = []

    for collection_name in collection_names:
        try:
            result = query_embeddings_doc(
                collection_name=collection_name,
                query=query,
                k=k,
                embeddings_function=embeddings_function,
                reranking_function=reranking_function,
            )
            results.append(result)
        except:
            pass

    return merge_and_sort_query_results(results, k)


def rag_template(template: str, context: str, query: str):
    template = template.replace("[context]", context)
    template = template.replace("[query]", query)
    return template


def query_embeddings_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    openai_key,
    openai_url,
):
    if embedding_engine == "":
        return lambda query: embedding_function.encode(query).tolist()
    elif embedding_engine == "ollama":
        return lambda query: generate_ollama_embeddings(
            GenerateEmbeddingsForm(
                **{
                    "model": embedding_model,
                    "prompt": query,
                }
            )
        )
    elif embedding_engine == "openai":
        return lambda query: generate_openai_embeddings(
            model=embedding_model,
            text=query,
            key=openai_key,
            url=openai_url,
        )


def rag_messages(
    docs,
    messages,
    template,
    k,
    embedding_engine,
    embedding_model,
    embedding_function,
    reranking_function,
    openai_key,
    openai_url,
):
    log.debug(
        f"docs: {docs} {messages} {embedding_engine} {embedding_model} {embedding_function} {reranking_function} {openai_key} {openai_url}"
    )

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

    relevant_contexts = []

    for doc in docs:
        context = None

        try:

            if doc["type"] == "text":
                context = doc["content"]
            else:
                embeddings_function = query_embeddings_function(
                    embedding_engine,
                    embedding_model,
                    embedding_function,
                    openai_key,
                    openai_url,
                )

                if doc["type"] == "collection":
                    context = query_embeddings_collection(
                        collection_names=doc["collection_names"],
                        query=query,
                        k=k,
                        embeddings_function=embeddings_function,
                        reranking_function=reranking_function,
                    )
                else:
                    context = query_embeddings_doc(
                        collection_name=doc["collection_name"],
                        query=query,
                        k=k,
                        embeddings_function=embeddings_function,
                        reranking_function=reranking_function,
                    )

        except Exception as e:
            log.exception(e)
            context = None

        relevant_contexts.append(context)

    log.debug(f"relevant_contexts: {relevant_contexts}")

    context_string = ""
    for context in relevant_contexts:
        if context:
            context_string += " ".join(context["documents"][0]) + "\n"

    ra_content = rag_template(
        template=template,
        context=context_string,
        query=query,
    )

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

    return messages


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

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class ChromaRetriever(BaseRetriever):
    collection: Any
    k: int
    embeddings_function: Any

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        query_embeddings = self.embeddings_function(query)

        results = self.collection.query(
            query_embeddings=[query_embeddings],
            n_results=self.k,
        )

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]

        return [
            Document(
                metadata=metadatas[idx],
                page_content=documents[idx],
            )
            for idx in range(len(ids))
        ]

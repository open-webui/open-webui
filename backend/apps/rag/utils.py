import os
import re
import logging
from typing import List
import requests


from huggingface_hub import snapshot_download
from apps.ollama.main import generate_ollama_embeddings, GenerateEmbeddingsForm


from config import SRC_LOG_LEVELS, CHROMA_CLIENT


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def query_doc(collection_name: str, query: str, k: int, embedding_function):
    try:
        # if you use docker use the model from the environment variable
        collection = CHROMA_CLIENT.get_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )
        result = collection.query(
            query_texts=[query],
            n_results=k,
        )
        return result
    except Exception as e:
        raise e


def query_embeddings_doc(collection_name: str, query_embeddings, k: int):
    try:
        # if you use docker use the model from the environment variable
        log.info(f"query_embeddings_doc {query_embeddings}")
        collection = CHROMA_CLIENT.get_collection(
            name=collection_name,
        )
        result = collection.query(
            query_embeddings=[query_embeddings],
            n_results=k,
        )

        log.info(f"query_embeddings_doc:result {result}")
        return result
    except Exception as e:
        raise e


def merge_and_sort_query_results(query_results, k):
    # Initialize lists to store combined data
    combined_ids = []
    combined_distances = []
    combined_metadatas = []
    combined_documents = []

    # Combine data from each dictionary
    for data in query_results:
        combined_ids.extend(data["ids"][0])
        combined_distances.extend(data["distances"][0])
        combined_metadatas.extend(data["metadatas"][0])
        combined_documents.extend(data["documents"][0])

    # Create a list of tuples (distance, id, metadata, document)
    combined = list(
        zip(combined_distances, combined_ids, combined_metadatas, combined_documents)
    )

    # Sort the list based on distances
    combined.sort(key=lambda x: x[0])

    # Unzip the sorted list
    sorted_distances, sorted_ids, sorted_metadatas, sorted_documents = zip(*combined)

    # Slicing the lists to include only k elements
    sorted_distances = list(sorted_distances)[:k]
    sorted_ids = list(sorted_ids)[:k]
    sorted_metadatas = list(sorted_metadatas)[:k]
    sorted_documents = list(sorted_documents)[:k]

    # Create the output dictionary
    merged_query_results = {
        "ids": [sorted_ids],
        "distances": [sorted_distances],
        "metadatas": [sorted_metadatas],
        "documents": [sorted_documents],
        "embeddings": None,
        "uris": None,
        "data": None,
    }

    return merged_query_results


def query_collection(
    collection_names: List[str], query: str, k: int, embedding_function
):

    results = []

    for collection_name in collection_names:
        try:
            # if you use docker use the model from the environment variable
            collection = CHROMA_CLIENT.get_collection(
                name=collection_name,
                embedding_function=embedding_function,
            )

            result = collection.query(
                query_texts=[query],
                n_results=k,
            )
            results.append(result)
        except:
            pass

    return merge_and_sort_query_results(results, k)


def query_embeddings_collection(collection_names: List[str], query_embeddings, k: int):

    results = []
    log.info(f"query_embeddings_collection {query_embeddings}")

    for collection_name in collection_names:
        try:
            collection = CHROMA_CLIENT.get_collection(name=collection_name)

            result = collection.query(
                query_embeddings=[query_embeddings],
                n_results=k,
            )
            results.append(result)
        except:
            pass

    return merge_and_sort_query_results(results, k)


def rag_template(template: str, context: str, query: str):
    template = template.replace("[context]", context)
    template = template.replace("[query]", query)
    return template


def rag_messages(
    docs,
    messages,
    template,
    k,
    embedding_engine,
    embedding_model,
    embedding_function,
    openai_key,
    openai_url,
):
    log.debug(
        f"docs: {docs} {messages} {embedding_engine} {embedding_model} {embedding_function} {openai_key} {openai_url}"
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
                if embedding_engine == "":
                    if doc["type"] == "collection":
                        context = query_collection(
                            collection_names=doc["collection_names"],
                            query=query,
                            k=k,
                            embedding_function=embedding_function,
                        )
                    else:
                        context = query_doc(
                            collection_name=doc["collection_name"],
                            query=query,
                            k=k,
                            embedding_function=embedding_function,
                        )

                else:
                    if embedding_engine == "ollama":
                        query_embeddings = generate_ollama_embeddings(
                            GenerateEmbeddingsForm(
                                **{
                                    "model": embedding_model,
                                    "prompt": query,
                                }
                            )
                        )
                    elif embedding_engine == "openai":
                        query_embeddings = generate_openai_embeddings(
                            model=embedding_model,
                            text=query,
                            key=openai_key,
                            url=openai_url,
                        )

                    if doc["type"] == "collection":
                        context = query_embeddings_collection(
                            collection_names=doc["collection_names"],
                            query_embeddings=query_embeddings,
                            k=k,
                        )
                    else:
                        context = query_embeddings_doc(
                            collection_name=doc["collection_name"],
                            query_embeddings=query_embeddings,
                            k=k,
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


def get_embedding_model_path(
    embedding_model: str, update_embedding_model: bool = False
):
    # Construct huggingface_hub kwargs with local_files_only to return the snapshot path
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME")

    local_files_only = not update_embedding_model

    snapshot_kwargs = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
    }

    log.debug(f"embedding_model: {embedding_model}")
    log.debug(f"snapshot_kwargs: {snapshot_kwargs}")

    # Inspiration from upstream sentence_transformers
    if (
        os.path.exists(embedding_model)
        or ("\\" in embedding_model or embedding_model.count("/") > 1)
        and local_files_only
    ):
        # If fully qualified path exists, return input, else set repo_id
        return embedding_model
    elif "/" not in embedding_model:
        # Set valid repo_id for model short-name
        embedding_model = "sentence-transformers" + "/" + embedding_model

    snapshot_kwargs["repo_id"] = embedding_model

    # Attempt to query the huggingface_hub library to determine the local path and/or to update
    try:
        embedding_model_repo_path = snapshot_download(**snapshot_kwargs)
        log.debug(f"embedding_model_repo_path: {embedding_model_repo_path}")
        return embedding_model_repo_path
    except Exception as e:
        log.exception(f"Cannot determine embedding model snapshot path: {e}")
        return embedding_model


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

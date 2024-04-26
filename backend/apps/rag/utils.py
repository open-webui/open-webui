import logging
import requests

from typing import List

from apps.ollama.main import (
    generate_ollama_embeddings,
    GenerateEmbeddingsForm,
)

from config import SRC_LOG_LEVELS, CHROMA_CLIENT


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def query_embeddings_doc(collection_name: str, query: str, query_embeddings, k: int):
    try:
        # if you use docker use the model from the environment variable
        log.info(f"query_embeddings_doc {query_embeddings}")
        collection = CHROMA_CLIENT.get_collection(name=collection_name)

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


def query_embeddings_collection(
    collection_names: List[str], query: str, query_embeddings, k: int
):

    results = []
    log.info(f"query_embeddings_collection {query_embeddings}")

    for collection_name in collection_names:
        try:
            result = query_embeddings_doc(
                collection_name=collection_name,
                query=query,
                query_embeddings=query_embeddings,
                k=k,
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
                    query_embeddings = embedding_function.encode(query).tolist()
                elif embedding_engine == "ollama":
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
                        query=query,
                        query_embeddings=query_embeddings,
                        k=k,
                    )
                else:
                    context = query_embeddings_doc(
                        collection_name=doc["collection_name"],
                        query=query,
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

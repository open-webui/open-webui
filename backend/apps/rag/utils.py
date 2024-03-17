import re
from typing import List

from config import CHROMA_CLIENT


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


def rag_template(template: str, context: str, query: str):
    template = template.replace("[context]", context)
    template = template.replace("[query]", query)
    return template


def rag_messages(docs, messages, template, k, embedding_function):
    print(docs)

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
        except Exception as e:
            print(e)
            context = None

        relevant_contexts.append(context)

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

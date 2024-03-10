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
    template = re.sub(r"\[context\]", context, template)
    template = re.sub(r"\[query\]", query, template)

    return template

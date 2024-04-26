import logging
import requests

from typing import List
import psycopg2

from apps.ollama.main import (
    generate_ollama_embeddings,
    GenerateEmbeddingsForm,
)

from config import SRC_LOG_LEVELS, POSTGRES_CONNECTION_STRING

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

def query_embeddings_doc(collection_name: str, query: str, k: int, embedding_function):
    try:
        conn = psycopg2.connect(**POSTGRES_CONNECTION_STRING)
        cursor = conn.cursor()

        # Execute SQL query to retrieve embeddings for the given collection_name
        cursor.execute("""
            SELECT embedding
            FROM documents
            WHERE collection_name = %s
        """, (collection_name,))
        
        # Fetch results
        vectors = cursor.fetchall()
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        # Perform similarity search using PGVector functions in Postgres
        # Add your implementation here
        query_result = None  # Placeholder for the query result
        
        return query_result  # Return the query result
    except Exception as e:
        log.exception(f"Error querying document in collection {collection_name}: {e}")
        raise e

def merge_and_sort_query_results(query_results, k):
    # Sort and merge query results as needed
    # Add your implementation here
    pass

def query_embeddings_collection(
    collection_names: List[str], query: str, k: int, embedding_function
):
    results = []
    log.info(f"query_embeddings_collection {embedding_function}")

    for collection_name in collection_names:
        try:
            # Connect to Postgres database and execute SQL query to retrieve vectors
            conn = psycopg2.connect(**POSTGRES_CONNECTION_STRING)
            cursor = conn.cursor()

            # Execute SQL query to get vectors for the given collection_name
            cursor.execute("""
                SELECT embedding
                FROM documents
                WHERE collection_name = %s
            """, (collection_name,))
            
            # Fetch results
            vectors = cursor.fetchall()
            
            # Close cursor and connection
            cursor.close()
            conn.close()

            # Perform similarity search using PGVector functions in Postgres
            # Example SQL query:
            # SELECT * FROM collection_table WHERE similarity(vector, query_vector) > threshold LIMIT k
            # Add your implementation here
            query_result = None  # Placeholder for the query result
            
            results.append(query_result)
        except Exception as e:
            log.exception(f"Error querying collection {collection_name}: {e}")

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

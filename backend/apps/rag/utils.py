import logging
from typing import List
import psycopg2

from config import SRC_LOG_LEVELS, POSTGRES_CONNECTION_STRING

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

def query_doc(collection_name: str, query: str, k: int, embedding_function):
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

def query_collection(
    collection_names: List[str], query: str, k: int, embedding_function
):
    results = []

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

import chromadb
from chromadb.utils import embedding_functions
from typing import Optional, List, Dict

# Global client cache
_chroma_client = None

def initialize_chroma_client(path: str = "./chroma_data") -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        try:
            # Using PersistentClient to save data to disk
            _chroma_client = chromadb.PersistentClient(path=path)
            print(f"ChromaDB client initialized. Data will be stored in: {path}")
        except Exception as e:
            print(f"Error initializing ChromaDB client at path {path}: {e}")
            # Fallback to in-memory client if persistent client fails (optional, based on requirements)
            # _chroma_client = chromadb.Client()
            # print(f"Initialized in-memory ChromaDB client due to error with persistent storage.")
            raise  # Re-raise the exception if persistence is critical
    return _chroma_client

def get_or_create_collection(
    client: chromadb.ClientAPI,
    collection_name: str,
    embedding_model_name: Optional[str] = "all-MiniLM-L6-v2" # Default if using Chroma's EF
) -> chromadb.Collection:
    try:
        # If we provide our own embeddings, we don't strictly need Chroma's embedding function.
        # However, some Chroma versions might require one, or it can be useful for default behavior.
        # For consistency with our EmbeddingService, we can specify a default sentence transformer.
        # ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embedding_model_name)

        # If providing embeddings directly during add, embedding_function can be None or default.
        # Let's assume we pass embeddings directly, so an EF isn't strictly needed for collection creation here.
        collection = client.get_or_create_collection(
            name=collection_name
            # embedding_function=ef # Optional: if you want Chroma to manage embeddings
        )
        print(f"Collection '{collection_name}' retrieved or created.")
        return collection
    except Exception as e:
        print(f"Error getting or creating collection {collection_name}: {e}")
        raise

def add_documents_to_collection(
    collection: chromadb.Collection,
    ids: List[str],
    documents: List[str],
    embeddings: Optional[List[List[float]]] = None,
    metadatas: Optional[List[Dict]] = None,
):
    try:
        if embeddings:
            collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        else:
            # If embeddings are not provided, Chroma will try to generate them if an EF is set on the collection
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"Added {len(ids)} documents to collection '{collection.name}'.")
    except Exception as e:
        print(f"Error adding documents to collection {collection.name}: {e}")
        # Consider how to handle partial adds or failures
        raise

def query_collection(
    collection: chromadb.Collection,
    query_embeddings: List[List[float]],
    n_results: int = 5,
    where_filter: Optional[Dict] = None,
    include: Optional[List[str]] = ["metadatas", "documents", "distances"]
) -> Dict:
    try:
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where_filter,
            include=include
        )
        print(f"Query returned {len(results.get('ids', [[]])[0])} results from collection '{collection.name}'.")
        return results
    except Exception as e:
        print(f"Error querying collection {collection.name}: {e}")
        raise

def delete_collection(client: chromadb.ClientAPI, collection_name: str):
    try:
        client.delete_collection(name=collection_name)
        print(f"Collection '{collection_name}' deleted.")
    except Exception as e:
        print(f"Error deleting collection {collection_name}: {e}")
        # Handle cases where collection might not exist or other errors
        raise

def count_documents_in_collection(collection: chromadb.Collection) -> int:
    try:
        return collection.count()
    except Exception as e:
        print(f"Error counting documents in collection {collection.name}: {e}")
        raise

# Example Usage (can be removed or kept for testing):
# if __name__ == '__main__':
#     # Initialize client (specify a path for persistence)
#     client = initialize_chroma_client(path="../chroma_db_data") # Example path
#
#     # Get or create a collection
#     collection_name = "my_test_collection"
#     collection = get_or_create_collection(client, collection_name)
#
#     # Prepare dummy data (replace with actual data)
#     # Assuming we have an embedding service like the one defined previously
#     from embedding_service import get_embeddings as get_custom_embeddings
#
#     sample_docs = ["This is document 1 about apples.", "Document 2 discusses bananas.", "The third one is about oranges."]
#     sample_ids = ["doc1", "doc2", "doc3"]
#     sample_metadatas = [{"source": "doc1"}, {"source": "doc2"}, {"source": "doc3"}]
#
#     # Generate embeddings using our service
#     # sample_embeddings = get_custom_embeddings(sample_docs) # This would require embedding_service.py to be in PYTHONPATH
#
#     # For standalone testing, let's mock embeddings or use Chroma's default (if EF was set)
#     # If using Chroma's default EF, you wouldn't pass `embeddings` to add_documents_to_collection
#     # For this example, let's assume we are passing pre-computed embeddings (even if they are zeros for simplicity here)
#     sample_embeddings = [[0.1]*384, [0.2]*384, [0.3]*384] # Replace with actual 384-dim embeddings
#
#     # Add documents
#     if count_documents_in_collection(collection) == 0: # Avoid re-adding
#          add_documents_to_collection(collection, ids=sample_ids, documents=sample_docs, embeddings=sample_embeddings, metadatas=sample_metadatas)
#     print(f"Number of documents in collection: {count_documents_in_collection(collection)}")
#
#     # Query documents
#     # query_text = "Tell me about fruits"
#     # query_embedding = get_custom_embeddings([query_text])[0] # Embedding for the query
#     query_embedding = [0.15]*384 # Mock query embedding
#
#     query_results = query_collection(collection, query_embeddings=[query_embedding], n_results=2)
#     print("Query Results:")
#     print(f"  IDs: {query_results.get('ids')}")
#     print(f"  Documents: {query_results.get('documents')}")
#     print(f"  Distances: {query_results.get('distances')}")
#     print(f"  Metadatas: {query_results.get('metadatas')}")
#
#     # Delete collection (optional cleanup)
#     # delete_collection(client, collection_name)

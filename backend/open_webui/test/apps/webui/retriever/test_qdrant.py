from fastembed import SparseTextEmbedding
import os
import uuid
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.retrieval.utils import get_embedding_function

def test_sparse_text_embedding():
    documents = [
        "You should stay, study and sprint.",
        "History can only prepare us to be surprised yet again.",
    ]

    # The bm25 only calculate the term frequency
    model = SparseTextEmbedding(model_name="Qdrant/bm25")
    embeddings = list(model.embed(documents))

    print(embeddings)
    
def test_insert_items_with_hybrid_vectors(): 
    documents = [
        "You should stay, study and sprint.",
        "History can only prepare us to be surprised yet again.",
        "Karamay Urban Credit, also known as Karamay City Commercial Bank Co Ltd, is more recently known as Bank of Kunlun Co Ltd. This institution has undergone name changes over time but it is essentially the same entity.",
        "The Bank of Karamay Urban Credit is currently subject to restrictions imposed by the Office of Foreign Assets Control (OFAC) of the United States"
    ]
    
    embedding_function = get_embedding_function(
        embedding_engine="openai",
        embedding_model="jina-embeddings-v3",
        embedding_function=None,
        url="https://api.jina.ai/v1",
        key=os.getenv("JINA_API_KEY"),
        embedding_batch_size=10,
    )
    
    embeddings = embedding_function(query=documents, user="test")
    print(len(embeddings))
    
    # Create a collection with hybrid search
    VECTOR_DB_CLIENT._create_collection_if_not_exists(
        collection_name="test",
        dimension=len(embeddings[0]),
        enable_hybrid_search=True,
    )
    
    items = []
    for i, document in enumerate(documents):
        items.append({
            "id": str(uuid.uuid4()),
            "text": document,
            "vector": embeddings[i],
            "metadata": {
                "source": "test"
            }
        })
    
    print(f"Inserting items: {items}")
    VECTOR_DB_CLIENT.insert(
        collection_name="test",
        items=items,
        enable_hybrid_search=True,
    )
    print("Items inserted")
    
def get_points_from_collection(collection_name: str):
    # points = VECTOR_DB_CLIENT.get_raw_data(collection_name=collection_name)
    # print(points[0].payload["text"])
    # print(points[0].vector["bm25"])
    
    import pdb; pdb.set_trace()
    points = VECTOR_DB_CLIENT.client.retrieve(collection_name=collection_name, 
                                              ids=["02c6449c-0cec-4e06-bdfd-aa869bad52fe"],
                                              with_vectors=True)
    print(points[0].payload["text"])
    print(points[0].vector["bm25"])
    
    
def test_query_sparse_vector():
    queries = [
        "Hello how you doing bro",
        "History can only prepare us to be surprised yet again.",
        "Karamay Urban Credit, also known as Karamay City Commercial Bank Co Ltd, is more recently known as Bank of Kunlun Co Ltd. This institution has undergone name changes over time but it is essentially the same entity.",
        "The Bank of Karamay Urban Credit is currently subject to restrictions imposed by the Office of Foreign Assets Control (OFAC) of the United States"
    ]
    
    # The bm25 only calculate the term frequency
    model = SparseTextEmbedding(model_name="Qdrant/bm25")
    embedding = model.query_embed(queries[0])
    print(next(embedding))
    
    results = VECTOR_DB_CLIENT.search_with_sparse_vector(collection_name="test", queries=queries)
    print(results)
    
def test_hybrid_search(collection_name: str):
    embedding_function = get_embedding_function(
        embedding_engine="openai",
        embedding_model="jina-embeddings-v3",
        embedding_function=None,
        url="https://api.jina.ai/v1",
        key=os.getenv("JINA_API_KEY"),
        embedding_batch_size=10,
    )
    
    query = "Hello how you doing bro"
    embedding = embedding_function(query=query, user="test")
    
    results = VECTOR_DB_CLIENT.search(collection_name=collection_name, vectors=[embedding], queries=[query], enable_hybrid_search=True)
    print(results)
    import pdb; pdb.set_trace()

if __name__ == "__main__":
    test_hybrid_search("fb26b87a-ec3b-4510-ad4b-81fd0b42eacd")
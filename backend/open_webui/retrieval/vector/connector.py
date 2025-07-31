from open_webui.config import VECTOR_DB
import logging

if VECTOR_DB == "milvus":
    from open_webui.retrieval.vector.dbs.milvus import MilvusClient

    VECTOR_DB_CLIENT = MilvusClient()
elif VECTOR_DB == "qdrant":
    from open_webui.retrieval.vector.dbs.qdrant import QdrantClient

    VECTOR_DB_CLIENT = QdrantClient()
elif VECTOR_DB == "opensearch":
    from open_webui.retrieval.vector.dbs.opensearch import OpenSearchClient

    VECTOR_DB_CLIENT = OpenSearchClient()
elif VECTOR_DB == "pgvector":
    from open_webui.retrieval.vector.dbs.pgvector import PgvectorClient

    VECTOR_DB_CLIENT = PgvectorClient()
elif VECTOR_DB == "weaviate":
    from open_webui.retrieval.vector.dbs.weaviate import WeaviateClient

    VECTOR_DB_CLIENT = WeaviateClient()
    if not VECTOR_DB_CLIENT.warmup():
        logging.error("Weaviate client warmup failed. Please check your configuration.")
        VECTOR_DB = "chroma"  # Fallback to Chroma if Weaviate fails
        from open_webui.retrieval.vector.dbs.chroma import ChromaClient

        VECTOR_DB_CLIENT = ChromaClient()
        
else:
    from open_webui.retrieval.vector.dbs.chroma import ChromaClient

    VECTOR_DB_CLIENT = ChromaClient()

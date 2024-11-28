from open_webui.config import VECTOR_DB

if VECTOR_DB == "milvus":
    from open_webui.apps.retrieval.vector.dbs.milvus import MilvusClient

    VECTOR_DB_CLIENT = MilvusClient()
elif VECTOR_DB == "qdrant":
    from open_webui.apps.retrieval.vector.dbs.qdrant import QdrantClient

    VECTOR_DB_CLIENT = QdrantClient()
elif VECTOR_DB == "opensearch":
    from open_webui.apps.retrieval.vector.dbs.opensearch import OpenSearchClient

    VECTOR_DB_CLIENT = OpenSearchClient()
elif VECTOR_DB == "pgvector":
    from open_webui.apps.retrieval.vector.dbs.pgvector import PgvectorClient

    VECTOR_DB_CLIENT = PgvectorClient()
else:
    from open_webui.apps.retrieval.vector.dbs.chroma import ChromaClient

    VECTOR_DB_CLIENT = ChromaClient()

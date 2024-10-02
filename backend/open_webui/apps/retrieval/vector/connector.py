from open_webui.config import VECTOR_DB

match VECTOR_DB:
    case "chroma":
        from open_webui.apps.retrieval.vector.dbs.chroma import ChromaClient
        VECTOR_DB_CLIENT = ChromaClient()

    case "milvus":
        from open_webui.apps.retrieval.vector.dbs.milvus import MilvusClient
        VECTOR_DB_CLIENT = MilvusClient()

    case "qdrant":
        from open_webui.apps.retrieval.vector.dbs.qdrant import QdrantClient
        VECTOR_DB_CLIENT = QdrantClient()

    case _:
        from open_webui.apps.retrieval.vector.dbs.chroma import ChromaClient
        VECTOR_DB_CLIENT = ChromaClient()

from open_webui.apps.retrieval.vector.dbs.chroma import ChromaClient
from open_webui.apps.retrieval.vector.dbs.milvus import MilvusClient
from open_webui.apps.retrieval.vector.dbs.qdrant import QdrantClient


from open_webui.config import VECTOR_DB

match VECTOR_DB:
    case "chroma":
        VECTOR_DB_CLIENT = ChromaClient()

    case "milvus":
        VECTOR_DB_CLIENT = MilvusClient()

    case "qdrant":
        VECTOR_DB_CLIENT = QdrantClient()

    case _:
        VECTOR_DB_CLIENT = ChromaClient()

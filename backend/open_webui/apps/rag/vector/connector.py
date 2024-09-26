from open_webui.apps.rag.vector.dbs.chroma import ChromaClient
from open_webui.apps.rag.vector.dbs.milvus import MilvusClient


from open_webui.config import VECTOR_DB

match VECTOR_DB:
    case "chroma":
        VECTOR_DB_CLIENT = ChromaClient()

    case "milvus":
        VECTOR_DB_CLIENT = MilvusClient()

    case _:
        VECTOR_DB_CLIENT = ChromaClient()

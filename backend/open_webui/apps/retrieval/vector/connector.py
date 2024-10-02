from open_webui.config import VECTOR_DB

if VECTOR_DB == "milvus":
    from open_webui.apps.retrieval.vector.dbs.milvus import MilvusClient

    VECTOR_DB_CLIENT = MilvusClient()
else:
    from open_webui.apps.retrieval.vector.dbs.chroma import ChromaClient

    VECTOR_DB_CLIENT = ChromaClient()

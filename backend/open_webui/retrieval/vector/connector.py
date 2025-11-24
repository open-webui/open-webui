import logging
from open_webui.config import VECTOR_DB
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", logging.INFO))

if VECTOR_DB == "milvus":
    from open_webui.retrieval.vector.dbs.milvus import MilvusClient

    VECTOR_DB_CLIENT = MilvusClient()
    log.info(f"✅ Using Milvus as vector database (VECTOR_DB={VECTOR_DB})")
elif VECTOR_DB == "qdrant":
    from open_webui.retrieval.vector.dbs.qdrant import QdrantClient

    VECTOR_DB_CLIENT = QdrantClient()
    log.info(f"✅ Using Qdrant as vector database (VECTOR_DB={VECTOR_DB})")
elif VECTOR_DB == "opensearch":
    from open_webui.retrieval.vector.dbs.opensearch import OpenSearchClient

    VECTOR_DB_CLIENT = OpenSearchClient()
    log.info(f"✅ Using OpenSearch as vector database (VECTOR_DB={VECTOR_DB})")
elif VECTOR_DB == "pgvector":
    from open_webui.retrieval.vector.dbs.pgvector import PgvectorClient

    VECTOR_DB_CLIENT = PgvectorClient()
    log.info(f"✅ Using Pgvector as vector database (VECTOR_DB={VECTOR_DB})")
else:
    from open_webui.retrieval.vector.dbs.chroma import ChromaClient

    VECTOR_DB_CLIENT = ChromaClient()
    log.info(f"✅ Using ChromaDB as vector database (VECTOR_DB={VECTOR_DB or 'chroma'})")

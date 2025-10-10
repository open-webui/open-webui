from open_webui.config import VECTOR_DB
from open_webui.retrieval.vector.dbs.qdrant import QdrantClient

# Only Qdrant is supported - simplified configuration
if VECTOR_DB and VECTOR_DB != "qdrant":
    print(f"Warning: VECTOR_DB={VECTOR_DB} is not supported. Using Qdrant instead.")

VECTOR_DB_CLIENT = QdrantClient()

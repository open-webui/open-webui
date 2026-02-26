try:
    from enum import StrEnum  # Python 3.11+
except ImportError:
    from strenum import StrEnum  # Backport for older Python


class VectorType(StrEnum):
    MILVUS = "milvus"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    PINECONE = "pinecone"
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"
    PGVECTOR = "pgvector"
    ORACLE23AI = "oracle23ai"
    S3VECTOR = "s3vector"
    WEAVIATE = "weaviate"
    OPENGAUSS = "opengauss"

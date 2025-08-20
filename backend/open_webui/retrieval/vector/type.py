from enum import StrEnum


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

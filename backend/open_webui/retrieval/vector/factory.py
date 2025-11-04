from __future__ import annotations

from typing import Any

from open_webui.retrieval.vector.main import VectorDBBase
from open_webui.retrieval.vector.type import VectorType
from open_webui.config import (
    VECTOR_DB,
    ENABLE_QDRANT_MULTITENANCY_MODE,
    ENABLE_MILVUS_MULTITENANCY_MODE,
)
from open_webui.settings import get_settings


class Vector:

    @staticmethod
    def get_vector(vector_type: str) -> VectorDBBase:
        """
        get vector db instance by vector type
        """
        match vector_type:
            case VectorType.MILVUS:
                if ENABLE_MILVUS_MULTITENANCY_MODE:
                    from open_webui.retrieval.vector.dbs.milvus_multitenancy import (
                        MilvusClient,
                    )

                    return MilvusClient()
                else:
                    from open_webui.retrieval.vector.dbs.milvus import MilvusClient

                    return MilvusClient()
            case VectorType.QDRANT:
                if ENABLE_QDRANT_MULTITENANCY_MODE:
                    from open_webui.retrieval.vector.dbs.qdrant_multitenancy import (
                        QdrantClient,
                    )

                    return QdrantClient()
                else:
                    from open_webui.retrieval.vector.dbs.qdrant import QdrantClient

                    return QdrantClient()
            case VectorType.PINECONE:
                from open_webui.retrieval.vector.dbs.pinecone import PineconeClient

                return PineconeClient()
            case VectorType.S3VECTOR:
                from open_webui.retrieval.vector.dbs.s3vector import S3VectorClient

                return S3VectorClient()
            case VectorType.OPENSEARCH:
                from open_webui.retrieval.vector.dbs.opensearch import OpenSearchClient

                return OpenSearchClient()
            case VectorType.PGVECTOR:
                from open_webui.retrieval.vector.dbs.pgvector import PgvectorClient

                return PgvectorClient()
            case VectorType.ELASTICSEARCH:
                from open_webui.retrieval.vector.dbs.elasticsearch import (
                    ElasticsearchClient,
                )

                return ElasticsearchClient()
            case VectorType.CHROMA:
                from open_webui.retrieval.vector.dbs.chroma import ChromaClient

                return ChromaClient()
            case VectorType.ORACLE23AI:
                from open_webui.retrieval.vector.dbs.oracle23ai import Oracle23aiClient

                return Oracle23aiClient()
            case _:
                raise ValueError(f"Unsupported vector type: {vector_type}")


class LazyVectorClient:
    """Lazy proxy that defers vector client creation until first use.

    This prevents importing heavy local vector DB packages in enterprise mode
    at module import-time.
    """

    def __init__(self) -> None:
        self._client: VectorDBBase | None = None

    def _resolve(self) -> VectorDBBase:
        if self._client is not None:
            return self._client

        # Derive preferred engine considering enterprise settings
        try:
            settings = get_settings()
            engine = (settings.vector_db or "").strip().lower() or VECTOR_DB
        except Exception:
            engine = VECTOR_DB

        # Map engine string to VectorType expected by the factory
        engine_map = {
            "chroma": VectorType.CHROMA,
            "pgvector": VectorType.PGVECTOR,
            "pinecone": VectorType.PINECONE,
            "qdrant": VectorType.QDRANT,
            "milvus": VectorType.MILVUS,
            "opensearch": VectorType.OPENSEARCH,
            "s3vector": VectorType.S3VECTOR,
            "elasticsearch": VectorType.ELASTICSEARCH,
            "oracle23ai": VectorType.ORACLE23AI,
        }

        vector_type = engine_map.get(engine, engine)
        client = Vector.get_vector(vector_type)
        self._client = client
        return client

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - simple proxy
        client = self._resolve()
        return getattr(client, name)


VECTOR_DB_CLIENT: VectorDBBase = LazyVectorClient()  # type: ignore[assignment]

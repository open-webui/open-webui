from typing import Any, Type

from langchain_core.embeddings import Embeddings
from open_webui.apps.rag.vector_store.implementations import (
    Chroma,
    Milvus,
    PersistentChroma,
    PGVector,
)
from open_webui.apps.rag.vector_store.vector_store_extension import VectorStoreExtension
from open_webui.env import VECTOR_STORE_TYPE


class VectorStoreConnector:
    """VectorStoreConnector class permits to use different VectorStores
    by providing the VectorStore Type."""

    _vector_stores = {
        "chroma": Chroma,
        "persistent_chroma": PersistentChroma,
        "milvus": Milvus,
        "pgvector": PGVector,
    }

    def __init__(self, vector_store_type: str = "persistent_chroma"):
        if vector_store_type in self._vector_stores:
            self.vector_store_type = vector_store_type
        else:
            raise ValueError(f"Unknown VectorStore type: {vector_store_type}")

    def get_vs_collection(
        self,
        collection_name: str,
        embedding_function: Embeddings,
        overwrite_collection: bool = False,
        **kwargs: Any,
    ) -> VectorStoreExtension:
        """Set VectorStore with the proper collection to be used."""
        return self._vector_stores[self.vector_store_type](
            collection_name=collection_name,
            embedding_function=embedding_function,
            overwrite_collection=overwrite_collection,
            **kwargs,
        )

    @property
    def vs_class(
        self,
    ) -> Type[VectorStoreExtension]:
        return self._vector_stores[self.vector_store_type]


# Set VectorStore Connector with the defined VectorStoreType
VECTOR_STORE_CONNECTOR = VectorStoreConnector(vector_store_type=VECTOR_STORE_TYPE)

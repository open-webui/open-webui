from datetime import datetime
from typing import Any, Optional, Type

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector as LangChainPGVector
from langchain_postgres.vectorstores import DistanceStrategy
from open_webui.apps.rag.vector_store.vector_store_extension import VectorStoreExtension
from open_webui.env import PGVECTOR_CONNECTION_STR


class PGVector(LangChainPGVector, VectorStoreExtension):
    """
    PGVector Interface that overrides LangChain PGVector Class with standardized attributes.

    Args:
        embedding_function (Optional[langchain_core.embeddings]): Embedding Function
            with LangChain interface. Keep this attribute optional as this class
            can be initialized with the attribute "embeddings" coming from original
            implementation.
        collection_name (str): The collection name to use.
        overwrite_collection (bool): Whether to overwrite current collection.
        connection (str): Postgres connection string. Use postgresql+psycopg prefix to use psycopg3.
            Example: postgresql+psycopg://postgres:my_password@localhost:5432/my_database.
        **kwargs (Any): Specific attributes linked to PGVector LangChain Class.
    """

    def __init__(
        self,
        embedding_function: Optional[Embeddings] = None,
        collection_name: str = "default",
        overwrite_collection: bool = False,
        connection: str = PGVECTOR_CONNECTION_STR,
        **kwargs: Any,
    ):
        self._overwrite_collection = overwrite_collection
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        # Avoid conflict of the same attribute appearing in kwargs with
        # default value and what we add in the super().__init__ below
        if self.embedding_function is None and "embeddings" in kwargs:
            self.embedding_function = kwargs.pop("embeddings")
        if "pre_delete_collection" in kwargs:
            kwargs.pop("pre_delete_collection")
        super().__init__(
            collection_name=self.collection_name,
            embeddings=self.embedding_function,
            pre_delete_collection=self._overwrite_collection,
            connection=connection,
            **kwargs,
        )

    @classmethod
    def from_documents(
        cls: Type[LangChainPGVector],
        documents: list[Document],
        embedding: Embeddings,
        *,
        ## Modified args
        connection: str = PGVECTOR_CONNECTION_STR,
        collection_name: str = "default",
        additional_metadata: dict = {},
        ##
        distance_strategy: DistanceStrategy = DistanceStrategy.COSINE,
        ids: Optional[list[str]] = None,
        pre_delete_collection: bool = False,
        use_jsonb: bool = True,
        **kwargs: Any,
    ) -> LangChainPGVector:
        """
        Return VectorStore initialized from documents and embeddings.
        This is a copy of the class method from_documents of LangChain PGVector
        but with additional processes.
        """
        texts = [d.page_content for d in documents]
        metadatas = [{**d.metadata, **additional_metadata} for d in documents]
        # Vectorstores do not like datetime formats
        # for meta-data so convert them to string.
        for metadata in metadatas:
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    metadata[key] = str(value)
        return cls.from_texts(
            texts=texts,
            pre_delete_collection=pre_delete_collection,
            embedding=embedding,
            distance_strategy=distance_strategy,
            metadatas=metadatas,
            connection=connection,
            ids=ids,
            collection_name=collection_name,
            use_jsonb=use_jsonb,
            **kwargs,
        )

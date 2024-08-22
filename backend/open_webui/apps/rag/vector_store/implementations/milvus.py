from datetime import datetime
from typing import Any, Type

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_milvus import Milvus as LangChainMilvus
from open_webui.apps.rag.vector_store.vector_store_extension import VectorStoreExtension
from open_webui.env import MILVUS_CONNECTION_URI


class Milvus(LangChainMilvus, VectorStoreExtension):
    """
    Milvus Interface that overrides Milvus PGVector Class with standardized attributes.

    Args:
        embedding_function (langchain_core.embeddings): Embedding Function with
            LangChain interface.
        collection_name (str): The collection name to use.
        overwrite_collection (bool): Whether to overwrite current collection.
        connection_args (dict[str, any]]): The connection args used for
            this class comes in the form of a dict.
        **kwargs (Any): Specific attributes linked to PGVector LangChain Class.
    """

    def __init__(
        self,
        embedding_function: Embeddings,
        collection_name: str = "default",
        overwrite_collection: bool = False,
        connection_args: dict[str, any] = {"uri": MILVUS_CONNECTION_URI},
        **kwargs: Any,
    ):
        self._overwrite_collection = overwrite_collection
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        # Avoid conflict of the same attribute appearing in kwargs with
        # default value and what we add in the super().__init__ below
        if "drop_old" in kwargs:
            kwargs.pop("drop_old")
        super().__init__(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            drop_old=self._overwrite_collection,
            connection_args=connection_args,
            **kwargs,
        )

    def delete_collection(self) -> None:
        """Delete collection."""
        return self.col.drop()

    @classmethod
    def from_documents(
        cls: Type[LangChainMilvus],
        documents: list[Document],
        embedding: Embeddings,
        ## Modified args
        connection_args: dict[str, any] = {"uri": MILVUS_CONNECTION_URI},
        additional_metadata: dict = {},
        ##
        **kwargs: Any,
    ) -> LangChainMilvus:
        """Return VectorStore initialized from documents and embeddings.
        This is a copy of the class method from_documents of LangChain Milvus
        but with additional processes.

        Args:
            documents: List of Documents to add to the vectorstore.
            embedding: Embedding function to use.
            **kwargs: Additional keyword arguments.

        Returns:
            VectorStore: VectorStore initialized from documents and embeddings.
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
            texts,
            embedding,
            metadatas=metadatas,
            connection_args=connection_args,
            **kwargs,
        )

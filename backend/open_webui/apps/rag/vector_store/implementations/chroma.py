from datetime import datetime
from typing import Any, Dict, Optional, Type

import chromadb
from chromadb import Settings
from langchain_chroma import Chroma as LangChainChroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from open_webui.apps.rag.vector_store.vector_store_extension import VectorStoreExtension
from open_webui.env import (
    CHROMA_DATA_PATH,
    CHROMA_DATABASE,
    CHROMA_HTTP_HEADERS,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_HTTP_SSL,
    CHROMA_TENANT,
)


class Chroma(LangChainChroma, VectorStoreExtension):
    """
    Chroma Interface that overrides LangChain Chroma Class with standardized attributes and
        with HttpClient Option.

    Args:
        embedding_function (langchain_core.embeddings): Embedding Function with LangChain interface.
        collection_name (str): The collection name to use.
        overwrite_collection (bool): Whether to overwrite current collection.
        host (str): The hostname of the Chroma server. Defaults to "localhost".
        port (int): The port of the Chroma server. Defaults to 8000.
        ssl (bool): Whether to use SSL to connect to the Chroma server. Defaults to False.
        headers (dict): A dictionary of headers to send to the Chroma server. Defaults to {}.
        settings (chromadb.Settings): A dictionary of settings to communicate with the chroma server.
        tenant (str): The tenant to use for this client. Defaults to the default tenant.
        database (str): The database to use for this client. Defaults to the default database.
        **kwargs (Any): Specific attributes linked to Chroma LangChain Class.
    """

    def __init__(
        self,
        embedding_function: Embeddings,
        collection_name: str = "default",
        overwrite_collection: bool = False,
        host: str = CHROMA_HTTP_HOST,
        port: int = CHROMA_HTTP_PORT,
        ssl: bool = CHROMA_HTTP_SSL,
        headers: dict[str, str] = CHROMA_HTTP_HEADERS,
        settings: Settings = Settings(allow_reset=True, anonymized_telemetry=False),
        tenant: str = CHROMA_TENANT,
        database: str = CHROMA_DATABASE,
        **kwargs: Any,
    ):
        self._overwrite_collection = overwrite_collection
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        client = chromadb.HttpClient(
            host=host,
            port=port,
            ssl=ssl,
            headers=headers,
            settings=settings,
            tenant=tenant,
            database=database,
        )
        # Avoid conflict of the same attribute appearing in kwargs with
        # default value and what we add in the super().__init__ below
        if "client" in kwargs:
            kwargs.pop("client")
        super().__init__(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            client=client,
            **kwargs,
        )
        if self._overwrite_collection:
            self.reset_collection()

    def get_documents(self, limit: Optional[int] = None) -> list[Document]:
        """Fetch documents from the collection."""
        dict_docs = self._collection.get(limit=limit)
        return [
            Document(
                page_content=dict_docs["documents"][index],
                metadata=dict_docs["metadatas"][index],
            )
            for index, _ in enumerate(dict_docs["ids"])
        ]

    def is_collection_empty(self) -> bool:
        """Check if the collection is empty or not."""
        return len(self.get_documents(limit=1)) == 0

    def reset(self) -> bool:
        """Reset VectorStore by deleting all collections."""
        return self._client.reset()

    @classmethod
    def from_documents(
        cls: Type[LangChainChroma],
        documents: list[Document],
        embedding: Optional[Embeddings] = None,
        ids: Optional[list[str]] = None,
        ## Modified args
        collection_name: str = "default",
        additional_metadata: dict = {},
        ##
        persist_directory: Optional[str] = None,
        client_settings: Optional[Settings] = None,
        client: Optional[chromadb.ClientAPI] = None,
        collection_metadata: Optional[Dict] = None,
        **kwargs: Any,
    ) -> LangChainChroma:
        """Create a Chroma vectorstore from a list of documents.
        This is a copy of the class method from_documents of LangChain Chroma
        but with additional processes.

        Args:
            collection_name: Name of the collection to create.
            persist_directory: Directory to persist the collection.
            ids: List of document IDs. Defaults to None.
            documents: List of documents to add to the vectorstore.
            embedding: Embedding function. Defaults to None.
            client_settings: Chroma client settings.
            client: Chroma client. Documentation:
                    https://docs.trychroma.com/reference/js-client#class:-chromaclient
            collection_metadata: Collection configurations.
                                                  Defaults to None.
            **kwargs: Additional keyword arguments to initialize a Chroma client.

        Returns:
            Chroma: Chroma vectorstore.
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [{**d.metadata, **additional_metadata} for d in documents]
        # Vectorstores do not like datetime formats
        # for meta-data so convert them to string.
        for metadata in metadatas:
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    metadata[key] = str(value)
        return cls.from_texts(
            texts=texts,
            embedding=embedding,
            metadatas=metadatas,
            ids=ids,
            collection_name=collection_name,
            persist_directory=persist_directory,
            client_settings=client_settings,
            client=client,
            collection_metadata=collection_metadata,
            **kwargs,
        )


class PersistentChroma(LangChainChroma, VectorStoreExtension):
    """
    Persistent Chroma Interface that overrides LangChain Chroma Class with standardized attributes and
        with Persistent Storage Option.

    Args:
        embedding_function (langchain_core.embeddings): Embedding Function with LangChain interface.
        collection_name (str): The collection name to use.
        overwrite_collection (bool): Whether to overwrite current collection.
        path (str): The directory to save Chroma's data to. Defaults to "${DATA_DIR}/vector_db".
        settings (chromadb.Settings): A dictionary of settings to communicate with the chroma server.
        tenant (str): The tenant to use for this client. Defaults to the default tenant.
        database (str): The database to use for this client. Defaults to the default database.
        **kwargs (Any): Specific attributes linked to Chroma LangChain Class.
    """

    def __init__(
        self,
        embedding_function: Embeddings,
        collection_name: str = "default",
        overwrite_collection: bool = False,
        path: str = CHROMA_DATA_PATH,
        settings: Settings = Settings(allow_reset=True, anonymized_telemetry=False),
        tenant: str = CHROMA_TENANT,
        database: str = CHROMA_DATABASE,
        **kwargs: Any,
    ):
        self._overwrite_collection = overwrite_collection
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        client = chromadb.PersistentClient(
            path=path,
            settings=settings,
            tenant=tenant,
            database=database,
        )
        # Avoid conflict of the same attribute appearing in kwargs with
        # default value and what we add in the super().__init__
        if "client" in kwargs:
            kwargs.pop("client")
        super().__init__(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            client=client,
            **kwargs,
        )
        if self._overwrite_collection:
            self.reset_collection()

    def get_documents(self, limit: Optional[int] = None) -> list[Document]:
        """Fetch documents from the collection."""
        dict_docs = self._collection.get(limit=limit)
        return [
            Document(
                page_content=dict_docs["documents"][index],
                metadata=dict_docs["metadatas"][index],
            )
            for index, _ in enumerate(dict_docs["ids"])
        ]

    def is_collection_empty(self) -> bool:
        """Check if the collection is empty or not."""
        return len(self.get_documents(limit=1)) == 0

    def reset(self) -> bool:
        """Reset VectorStore by deleting all collections."""
        return self._client.reset()

    @classmethod
    def from_documents(
        cls: Type[LangChainChroma],
        documents: list[Document],
        embedding: Optional[Embeddings] = None,
        ids: Optional[list[str]] = None,
        ## Modified args
        collection_name: str = "default",
        additional_metadata: dict = {},
        ##
        persist_directory: Optional[str] = None,
        client_settings: Optional[Settings] = None,
        client: Optional[chromadb.ClientAPI] = None,
        collection_metadata: Optional[Dict] = None,
        **kwargs: Any,
    ) -> LangChainChroma:
        """Create a Chroma vectorstore from a list of documents.
        This is a copy of the class method from_documents of LangChain Chroma
        but with additional processes.

        Args:
            collection_name: Name of the collection to create.
            persist_directory: Directory to persist the collection.
            ids: List of document IDs. Defaults to None.
            documents: List of documents to add to the vectorstore.
            embedding: Embedding function. Defaults to None.
            client_settings: Chroma client settings.
            client: Chroma client. Documentation:
                    https://docs.trychroma.com/reference/js-client#class:-chromaclient
            collection_metadata: Collection configurations.
                                                  Defaults to None.
            **kwargs: Additional keyword arguments to initialize a Chroma client.

        Returns:
            Chroma: Chroma vectorstore.
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [{**d.metadata, **additional_metadata} for d in documents]
        # Vectorstores do not like datetime formats
        # for meta-data so convert them to string.
        for metadata in metadatas:
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    metadata[key] = str(value)
        return cls.from_texts(
            texts=texts,
            embedding=embedding,
            metadatas=metadatas,
            ids=ids,
            collection_name=collection_name,
            persist_directory=persist_directory,
            client_settings=client_settings,
            client=client,
            collection_metadata=collection_metadata,
            **kwargs,
        )

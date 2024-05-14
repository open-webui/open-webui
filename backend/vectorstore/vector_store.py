from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Optional, List, Tuple, Dict

import chromadb
from chromadb import Settings, ClientAPI
from chromadb.utils.batch_utils import create_batches


Collection = namedtuple('Collection', ['name'])


class VectorStore(ABC):
    @abstractmethod
    def reset(self) -> bool:
        pass

    @abstractmethod
    def list_collections(self) -> List[Collection]:
        pass

    @abstractmethod
    def delete_collection(self, name:str):
        pass

    @abstractmethod
    def create_collection(self, name:str, dims:int):
        pass

    @abstractmethod
    def add_docs(self, collection_name:str,
            ids,#: OneOrMany[ID],
            embeddings,#: Optional[OneOrMany[Embedding]] = None,
            metadatas,#: Optional[OneOrMany[Metadata]] = None,
            documents):#: Optional[OneOrMany[Document]] = None
        pass

    @abstractmethod
    def get_collection(self, name: str):
        pass

    #TODO results may vary beween C&Q
    @abstractmethod
    def query(self, collection_name: str,
              query_embeddings,
              n_results: int):
        pass

    # keys are: documents, metadatas
    def get_all(self, collection_name: str) -> Dict:
        pass


class Chroma(VectorStore):
    def __init__(self, client: ClientAPI):
        self._client = client

    @classmethod
    def create_remote_or_none(cls):
        from config import (CHROMA_HTTP_HOST, CHROMA_TENANT, CHROMA_DATABASE, CHROMA_HTTP_PORT,
                            CHROMA_HTTP_HEADERS,
                            CHROMA_HTTP_SSL)
        if CHROMA_HTTP_HOST != "":
            http_client = chromadb.HttpClient(host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT, headers=CHROMA_HTTP_HEADERS,
                                              ssl=CHROMA_HTTP_SSL, tenant=CHROMA_TENANT, database=CHROMA_DATABASE,
                                              settings=Settings(allow_reset=True, anonymized_telemetry=False), )
            return cls(http_client)
        else:
            return None

    @classmethod
    def create_local(cls):
        from config import (CHROMA_TENANT, CHROMA_DATABASE)
        from config import CHROMA_DATA_PATH
        local_client = chromadb.PersistentClient(
            path=CHROMA_DATA_PATH,
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
        )
        return cls(local_client)

    def reset(self):
        return self._client.reset()

    def list_collections(self):
        return [Collection(name=c.name) for c in self._client.list_collections()]

    def delete_collection(self, name):
        return self._client.delete_collection(name)

    def create_collection(self, name:str, dims:int):
        return self._client.create_collection(name)

    def get_collection(self, name):
        return self._client.get_collection(name)

    # def create_batches(self, ids, embeddings=None, metadatas=None, documents=None) -> List:
    #     return create_batches(self._client, ids, embeddings, metadatas, documents)

    def query(self, collection_name: str,
              query_embeddings,
              n_results: int):
        collection = self._client.get_collection(name=collection_name)

        return collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
        )

    def get_all(self, collection_name: str)->Dict:
        collection = self._client.get_collection(name=collection_name)
        return collection.get()

    def add_docs(self, collection_name:str,
            ids,#: OneOrMany[ID],
            embeddings,#: Optional[OneOrMany[Embedding]] = None,
            metadatas,#: Optional[OneOrMany[Metadata]] = None,
            documents):
        collection = self._client.get_collection(name=collection_name)
        for batch in create_batches(self._client,
                ids=ids,
                metadatas=metadatas,
                embeddings=embeddings,
                documents=documents,
        ):
            collection.add(*batch)

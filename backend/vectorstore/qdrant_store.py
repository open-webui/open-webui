import os
from typing import List, Dict

from vectorstore.vector_store import Collection, VectorStore

DOC_TEXT = "__doc_text"

class Qdrant(VectorStore):

    def __init__(self, client):
        self._batch_size = 10
        self._client = client

    @classmethod
    def create_or_none(cls):
        from qdrant_client import QdrantClient
        # TODO should env moved to config?
        location = os.environ.get("QDRANT_LOCATION")
        url = os.environ.get("QDRANT_URL")
        host = os.environ.get("QDRANT_HOST")
        path = os.environ.get("QDRANT_PATH")
        if location or url or host or path:
            qdrant_client = QdrantClient(location=location,
                                         url=url,
                                         port=maybe_int(os.environ.get("QDRANT_PORT")),
                                         grpc_port=maybe_int(os.environ.get("QDRANT_GRPC_PORT"), 6334),
                                         prefer_grpc=maybe_bool(os.environ.get("QDRANT_PREFER_GRPC"), False),
                                         https=maybe_bool(os.environ.get("QDRANT_HTTPS")),
                                         api_key=os.environ.get("QDRANT_API_KEY"),
                                         prefix=os.environ.get("QDRANT_PREFIX"),
                                         timeout=maybe_int(os.environ.get("QDRANT_TIMEOUT")),
                                         host=host,
                                         path=path,
                                         )
            return cls(qdrant_client)
        else:
            return None

    def reset(self) -> bool:
        for coll in self._client.get_collections():
            self._client.delete_collection(coll.name)
        return True

    def list_collections(self) -> List[Collection]:
        return [Collection(name=q.name) for q in self._client.get_collections()]

    def delete_collection(self, name):
        self._client.delete_collection(name)

    def get_collection(self, name):
        qc = self._client.get_collection(name)
        return Collection(name=name) #no name in returned obj

    def get_all(self, collection_name: str) -> Dict:
        ids = []
        docs = []
        metas = []
        offset = None
        bootstrap = True
        while offset or bootstrap:
            bootstrap = False
            results, offset = self._client.scroll(collection_name)
            for r in results:
                ids.append(r.id)
                docs.append(r.payload[DOC_TEXT])
                del r.payload[DOC_TEXT]
                metas.append(r.payload)
        return dict(ids=ids, documents=docs, metadatas=metas)

    def create_collection(self, name: str, dims: int):
        from qdrant_client.http import models
        return self._client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=dims,
                                               distance=models.Distance.EUCLID  # root of L2 which chroma uses
                                               ),
        )

    def add_docs(self, collection_name: str,
                 ids,  #: OneOrMany[ID],
                 embeddings,  #: Optional[OneOrMany[Embedding]] = None,
                 metadatas,  #: Optional[OneOrMany[Metadata]] = None,
                 documents):
        from qdrant_client.http import models
        batch = self._batch_size
        for i in range(0, len(ids), batch):
            payloads = [{DOC_TEXT: d} | m for m, d in zip(metadatas[i:i + batch], documents[i:i + batch])]
            self._client.upsert(collection_name=collection_name,
                                points=models.Batch(ids=ids[i:i + batch],
                                                    vectors=embeddings[i:i + batch],
                                                    payloads=payloads))

    def query(self, collection_name: str, query_embeddings, n_results: int):
        results = self._client.search(collection_name=collection_name, query_vector=query_embeddings, limit=n_results)
        ids = []
        docs = []
        metas = []
        dists=[]
        for r in results:
            ids.append(r.id)
            dists.append(r.score)
            docs.append(r.payload[DOC_TEXT])
            del r.payload[DOC_TEXT]
            metas.append(r.payload)
        #TODO why it's a list of list. perhapst there should be some case for empty results?
        return dict(ids=[ids], distances=[dists],documents=[docs], metadatas=[metas])


def maybe_int(str_val, def_val=None):
    return int(str_val) if str_val else def_val


def maybe_bool(str_val, def_val=None):
    return str_val == "true" if str_val else def_val



from vectorstore.qdrant_store import Qdrant
from vectorstore.vector_store import Chroma, VectorStore


def create_vector_store() -> VectorStore:
    for factory in [lambda: Chroma.create_remote_or_none(), lambda: Qdrant.create_or_none(),
                    lambda: Chroma.create_local()]:
        store = factory()
        if store:
            return store
    raise Exception("Unable to create a vector store")
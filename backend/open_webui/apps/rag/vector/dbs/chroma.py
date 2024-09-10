import chromadb
from chromadb import Settings

from open_webui.config import (
    CHROMA_DATA_PATH,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_HTTP_HEADERS,
    CHROMA_HTTP_SSL,
    CHROMA_TENANT,
    CHROMA_DATABASE,
)


class Chroma:
    def __init__(self):
        if CHROMA_HTTP_HOST != "":
            self.client = chromadb.HttpClient(
                host=CHROMA_HTTP_HOST,
                port=CHROMA_HTTP_PORT,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
                settings=Settings(allow_reset=True, anonymized_telemetry=False),
            )
        else:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DATA_PATH,
                settings=Settings(allow_reset=True, anonymized_telemetry=False),
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )

    def query_collection(self, name, query_embeddings, k):
        collection = self.client.get_collection(name=name)
        if collection:
            result = collection.query(
                query_embeddings=[query_embeddings],
                n_results=k,
            )
            return result
        return None

    def list_collections(self):
        return self.client.list_collections()

    def create_collection(self, name):
        return self.client.create_collection(name=name)

    def get_or_create_collection(self, name):
        return self.client.get_or_create_collection(name=name)

    def delete_collection(self, name):
        return self.client.delete_collection(name=name)

    def reset(self):
        return self.client.reset()

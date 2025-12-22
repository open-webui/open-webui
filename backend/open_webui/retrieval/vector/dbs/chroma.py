import chromadb
import logging
from chromadb import Settings
from chromadb.utils.batch_utils import create_batches

from typing import Optional

from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.retrieval.vector.utils import process_metadata

from open_webui.config import (
    CHROMA_DATA_PATH,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_HTTP_HEADERS,
    CHROMA_HTTP_SSL,
    CHROMA_TENANT,
    CHROMA_DATABASE,
    CHROMA_CLIENT_AUTH_PROVIDER,
    CHROMA_CLIENT_AUTH_CREDENTIALS,
)

log = logging.getLogger(__name__)


class ChromaClient(VectorDBBase):
    def __init__(self):
        settings_dict = {
            "allow_reset": True,
            "anonymized_telemetry": False,
        }
        if CHROMA_CLIENT_AUTH_PROVIDER is not None:
            settings_dict["chroma_client_auth_provider"] = CHROMA_CLIENT_AUTH_PROVIDER
        if CHROMA_CLIENT_AUTH_CREDENTIALS is not None:
            settings_dict["chroma_client_auth_credentials"] = (
                CHROMA_CLIENT_AUTH_CREDENTIALS
            )

        if CHROMA_HTTP_HOST != "":
            self.client = chromadb.HttpClient(
                host=CHROMA_HTTP_HOST,
                port=CHROMA_HTTP_PORT,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
                settings=Settings(**settings_dict),
            )
        else:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DATA_PATH,
                settings=Settings(**settings_dict),
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collection_names = self.client.list_collections()
        return collection_name in collection_names

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(name=collection_name)

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection:
                result = collection.query(
                    query_embeddings=vectors,
                    n_results=limit,
                )

                # chromadb has cosine distance, 2 (worst) -> 0 (best). Re-odering to 0 -> 1
                # https://docs.trychroma.com/docs/collections/configure cosine equation
                distances: list = result["distances"][0]
                distances = [2 - dist for dist in distances]
                distances = [[dist / 2 for dist in distances]]

                return SearchResult(
                    **{
                        "ids": result["ids"],
                        "distances": distances,
                        "documents": result["documents"],
                        "metadatas": result["metadatas"],
                    }
                )
            return None
        except Exception as e:
            return None

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        # Query the items from the collection based on the filter.
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection:
                result = collection.get(
                    where=filter,
                    limit=limit,
                )

                return GetResult(
                    **{
                        "ids": [result["ids"]],
                        "documents": [result["documents"]],
                        "metadatas": [result["metadatas"]],
                    }
                )
            return None
        except:
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.get()
            return GetResult(
                **{
                    "ids": [result["ids"]],
                    "documents": [result["documents"]],
                    "metadatas": [result["metadatas"]],
                }
            )
        return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        embeddings = [item["vector"] for item in items]
        metadatas = [process_metadata(item["metadata"]) for item in items]

        for batch in create_batches(
            api=self.client,
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        ):
            collection.add(*batch)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        embeddings = [item["vector"] for item in items]
        metadatas = [process_metadata(item["metadata"]) for item in items]

        collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the collection based on the ids.
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection:
                if ids:
                    collection.delete(ids=ids)
                elif filter:
                    collection.delete(where=filter)
        except Exception as e:
            # If collection doesn't exist, that's fine - nothing to delete
            log.debug(
                f"Attempted to delete from non-existent collection {collection_name}. Ignoring."
            )
            pass

    def reset(self):
        # Resets the database. This will delete all collections and item entries.
        return self.client.reset()

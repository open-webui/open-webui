from pymilvus import MilvusClient as Client
from pymilvus import FieldSchema, DataType
import json

from typing import Optional

from open_webui.apps.rag.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    MILVUS_URI,
)


class MilvusClient:
    def __init__(self):
        self.collection_prefix = "open_webui"
        self.client = Client(uri=MILVUS_URI)

    def _result_to_get_result(self, result) -> GetResult:
        print(result)

        ids = []
        documents = []
        metadatas = []

        for match in result:
            _ids = []
            _documents = []
            _metadatas = []

            for item in match:
                _ids.append(item.get("id"))
                _documents.append(item.get("data", {}).get("text"))
                _metadatas.append(item.get("metadata"))

            ids.append(_ids)
            documents.append(_documents)
            metadatas.append(_metadatas)

        return GetResult(
            **{
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def _result_to_search_result(self, result) -> SearchResult:
        print(result)

        ids = []
        distances = []
        documents = []
        metadatas = []

        for match in result:
            _ids = []
            _distances = []
            _documents = []
            _metadatas = []

            for item in match:
                _ids.append(item.get("id"))
                _distances.append(item.get("distance"))
                _documents.append(item.get("entity", {}).get("data", {}).get("text"))
                _metadatas.append(item.get("entity", {}).get("metadata"))

            ids.append(_ids)
            distances.append(_distances)
            documents.append(_documents)
            metadatas.append(_metadatas)

        return SearchResult(
            **{
                "ids": ids,
                "distances": distances,
                "documents": documents,
                "metadatas": metadatas,
            }
        )

    def _create_collection(self, collection_name: str, dimension: int):
        schema = self.client.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )
        schema.add_field(
            field_name="id",
            datatype=DataType.VARCHAR,
            is_primary=True,
            max_length=65535,
        )
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=dimension,
            description="vector",
        )
        schema.add_field(field_name="data", datatype=DataType.JSON, description="data")
        schema.add_field(
            field_name="metadata", datatype=DataType.JSON, description="metadata"
        )

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector", index_type="HNSW", metric_type="COSINE", params={}
        )

        self.client.create_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            schema=schema,
            index_params=index_params,
        )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        return self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.drop_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        result = self.client.search(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=vectors,
            limit=limit,
            output_fields=["data", "metadata"],
        )

        return self._result_to_search_result(result)

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        result = self.client.query(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            filter='id != ""',
        )
        return self._result_to_get_result([result])

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        if not self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        ):
            self._create_collection(
                collection_name=collection_name, dimension=len(items[0]["vector"])
            )

        return self.client.insert(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=[
                {
                    "id": item["id"],
                    "vector": item["vector"],
                    "data": {"text": item["text"]},
                    "metadata": item["metadata"],
                }
                for item in items
            ],
        )

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        if not self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        ):
            self._create_collection(
                collection_name=collection_name, dimension=len(items[0]["vector"])
            )

        return self.client.upsert(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=[
                {
                    "id": item["id"],
                    "vector": item["vector"],
                    "data": {"text": item["text"]},
                    "metadata": item["metadata"],
                }
                for item in items
            ],
        )

    def delete(self, collection_name: str, ids: list[str]):
        # Delete the items from the collection based on the ids.

        return self.client.delete(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            ids=ids,
        )

    def reset(self):
        # Resets the database. This will delete all collections and item entries.

        collection_names = self.client.list_collections()
        for collection_name in collection_names:
            if collection_name.startswith(self.collection_prefix):
                self.client.drop_collection(collection_name=collection_name)

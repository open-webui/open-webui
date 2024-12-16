from pymilvus import MilvusClient as Client
from pymilvus import FieldSchema, DataType
import json

from typing import Optional

from open_webui.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    MILVUS_URI,
)


class MilvusClient:
    def __init__(self):
        self.collection_prefix = "open_webui"
        self.client = Client(uri=MILVUS_URI)

    def _result_to_get_result(self, result) -> GetResult:
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
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 100},
        )

        self.client.create_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            schema=schema,
            index_params=index_params,
        )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collection_name = collection_name.replace("-", "_")
        return self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        collection_name = collection_name.replace("-", "_")
        return self.client.drop_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        )

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        collection_name = collection_name.replace("-", "_")
        result = self.client.search(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=vectors,
            limit=limit,
            output_fields=["data", "metadata"],
        )

        return self._result_to_search_result(result)

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        # Construct the filter string for querying
        collection_name = collection_name.replace("-", "_")
        if not self.has_collection(collection_name):
            return None

        filter_string = " && ".join(
            [
                f'metadata["{key}"] == {json.dumps(value)}'
                for key, value in filter.items()
            ]
        )

        max_limit = 16383  # The maximum number of records per request
        all_results = []

        if limit is None:
            limit = float("inf")  # Use infinity as a placeholder for no limit

        # Initialize offset and remaining to handle pagination
        offset = 0
        remaining = limit

        try:
            # Loop until there are no more items to fetch or the desired limit is reached
            while remaining > 0:
                print("remaining", remaining)
                current_fetch = min(
                    max_limit, remaining
                )  # Determine how many items to fetch in this iteration

                results = self.client.query(
                    collection_name=f"{self.collection_prefix}_{collection_name}",
                    filter=filter_string,
                    output_fields=["*"],
                    limit=current_fetch,
                    offset=offset,
                )

                if not results:
                    break

                all_results.extend(results)
                results_count = len(results)
                remaining -= (
                    results_count  # Decrease remaining by the number of items fetched
                )
                offset += results_count

                # Break the loop if the results returned are less than the requested fetch count
                if results_count < current_fetch:
                    break

            print(all_results)
            return self._result_to_get_result([all_results])
        except Exception as e:
            print(e)
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        collection_name = collection_name.replace("-", "_")
        result = self.client.query(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            filter='id != ""',
        )
        return self._result_to_get_result([result])

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection_name = collection_name.replace("-", "_")
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
        collection_name = collection_name.replace("-", "_")
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

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the collection based on the ids.
        collection_name = collection_name.replace("-", "_")
        if ids:
            return self.client.delete(
                collection_name=f"{self.collection_prefix}_{collection_name}",
                ids=ids,
            )
        elif filter:
            # Convert the filter dictionary to a string using JSON_CONTAINS.
            filter_string = " && ".join(
                [
                    f'metadata["{key}"] == {json.dumps(value)}'
                    for key, value in filter.items()
                ]
            )

            return self.client.delete(
                collection_name=f"{self.collection_prefix}_{collection_name}",
                filter=filter_string,
            )

    def reset(self):
        # Resets the database. This will delete all collections and item entries.
        collection_names = self.client.list_collections()
        for collection_name in collection_names:
            if collection_name.startswith(self.collection_prefix):
                self.client.drop_collection(collection_name=collection_name)

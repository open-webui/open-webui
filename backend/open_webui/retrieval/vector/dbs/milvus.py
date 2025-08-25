from pymilvus import MilvusClient as Client
from pymilvus import FieldSchema, DataType
from pymilvus import connections, Collection

import json
import logging
from typing import Optional

from open_webui.retrieval.vector.utils import stringify_metadata
from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import (
    MILVUS_URI,
    MILVUS_DB,
    MILVUS_TOKEN,
    MILVUS_INDEX_TYPE,
    MILVUS_METRIC_TYPE,
    MILVUS_HNSW_M,
    MILVUS_HNSW_EFCONSTRUCTION,
    MILVUS_IVF_FLAT_NLIST,
)
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class MilvusClient(VectorDBBase):
    def __init__(self):
        self.collection_prefix = "open_webui"
        if MILVUS_TOKEN is None:
            self.client = Client(uri=MILVUS_URI, db_name=MILVUS_DB)
        else:
            self.client = Client(uri=MILVUS_URI, db_name=MILVUS_DB, token=MILVUS_TOKEN)

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
                # normalize milvus score from [-1, 1] to [0, 1] range
                # https://milvus.io/docs/de/metric.md
                _dist = (item.get("distance") + 1.0) / 2.0
                _distances.append(_dist)
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

        # Use configurations from config.py
        index_type = MILVUS_INDEX_TYPE.upper()
        metric_type = MILVUS_METRIC_TYPE.upper()

        log.info(f"Using Milvus index type: {index_type}, metric type: {metric_type}")

        index_creation_params = {}
        if index_type == "HNSW":
            index_creation_params = {
                "M": MILVUS_HNSW_M,
                "efConstruction": MILVUS_HNSW_EFCONSTRUCTION,
            }
            log.info(f"HNSW params: {index_creation_params}")
        elif index_type == "IVF_FLAT":
            index_creation_params = {"nlist": MILVUS_IVF_FLAT_NLIST}
            log.info(f"IVF_FLAT params: {index_creation_params}")
        elif index_type in ["FLAT", "AUTOINDEX"]:
            log.info(f"Using {index_type} index with no specific build-time params.")
        else:
            log.warning(
                f"Unsupported MILVUS_INDEX_TYPE: '{index_type}'. "
                f"Supported types: HNSW, IVF_FLAT, FLAT, AUTOINDEX. "
                f"Milvus will use its default for the collection if this type is not directly supported for index creation."
            )
            # For unsupported types, pass the type directly to Milvus; it might handle it or use a default.
            # If Milvus errors out, the user needs to correct the MILVUS_INDEX_TYPE env var.

        index_params.add_index(
            field_name="vector",
            index_type=index_type,
            metric_type=metric_type,
            params=index_creation_params,
        )

        self.client.create_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            schema=schema,
            index_params=index_params,
        )
        log.info(
            f"Successfully created collection '{self.collection_prefix}_{collection_name}' with index type '{index_type}' and metric '{metric_type}'."
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
        # For some index types like IVF_FLAT, search params like nprobe can be set.
        # Example: search_params = {"nprobe": 10} if using IVF_FLAT
        # For simplicity, not adding configurable search_params here, but could be extended.
        result = self.client.search(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=vectors,
            limit=limit,
            output_fields=["data", "metadata"],
            # search_params=search_params # Potentially add later if needed
        )
        return self._result_to_search_result(result)

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        connections.connect(uri=MILVUS_URI, token=MILVUS_TOKEN, db_name=MILVUS_DB)

        # Construct the filter string for querying
        collection_name = collection_name.replace("-", "_")
        if not self.has_collection(collection_name):
            log.warning(
                f"Query attempted on non-existent collection: {self.collection_prefix}_{collection_name}"
            )
            return None
        filter_string = " && ".join(
            [
                f'metadata["{key}"] == {json.dumps(value)}'
                for key, value in filter.items()
            ]
        )

        collection = Collection(f"{self.collection_prefix}_{collection_name}")
        collection.load()
        all_results = []

        try:
            log.info(
                f"Querying collection {self.collection_prefix}_{collection_name} with filter: '{filter_string}', limit: {limit}"
            )

            iterator = collection.query_iterator(
                filter=filter_string,
                output_fields=[
                    "id",
                    "data",
                    "metadata",
                ],
                limit=limit,  # Pass the limit directly; None means no limit.
            )

            while True:
                result = iterator.next()
                if not result:
                    iterator.close()
                    break
                all_results += result

            log.info(f"Total results from query: {len(all_results)}")
            return self._result_to_get_result([all_results])

        except Exception as e:
            log.exception(
                f"Error querying collection {self.collection_prefix}_{collection_name} with filter '{filter_string}' and limit {limit}: {e}"
            )
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection. This can be very resource-intensive for large collections.
        collection_name = collection_name.replace("-", "_")
        log.warning(
            f"Fetching ALL items from collection '{self.collection_prefix}_{collection_name}'. This might be slow for large collections."
        )
        # Using query with a trivial filter to get all items.
        # This will use the paginated query logic.
        return self.query(collection_name=collection_name, filter={}, limit=None)

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection_name = collection_name.replace("-", "_")
        if not self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        ):
            log.info(
                f"Collection {self.collection_prefix}_{collection_name} does not exist. Creating now."
            )
            if not items:
                log.error(
                    f"Cannot create collection {self.collection_prefix}_{collection_name} without items to determine dimension."
                )
                raise ValueError(
                    "Cannot create Milvus collection without items to determine vector dimension."
                )
            self._create_collection(
                collection_name=collection_name, dimension=len(items[0]["vector"])
            )

        log.info(
            f"Inserting {len(items)} items into collection {self.collection_prefix}_{collection_name}."
        )
        return self.client.insert(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=[
                {
                    "id": item["id"],
                    "vector": item["vector"],
                    "data": {"text": item["text"]},
                    "metadata": stringify_metadata(item["metadata"]),
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
            log.info(
                f"Collection {self.collection_prefix}_{collection_name} does not exist for upsert. Creating now."
            )
            if not items:
                log.error(
                    f"Cannot create collection {self.collection_prefix}_{collection_name} for upsert without items to determine dimension."
                )
                raise ValueError(
                    "Cannot create Milvus collection for upsert without items to determine vector dimension."
                )
            self._create_collection(
                collection_name=collection_name, dimension=len(items[0]["vector"])
            )

        log.info(
            f"Upserting {len(items)} items into collection {self.collection_prefix}_{collection_name}."
        )
        return self.client.upsert(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            data=[
                {
                    "id": item["id"],
                    "vector": item["vector"],
                    "data": {"text": item["text"]},
                    "metadata": stringify_metadata(item["metadata"]),
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
        # Delete the items from the collection based on the ids or filter.
        collection_name = collection_name.replace("-", "_")
        if not self.has_collection(collection_name):
            log.warning(
                f"Delete attempted on non-existent collection: {self.collection_prefix}_{collection_name}"
            )
            return None

        if ids:
            log.info(
                f"Deleting items by IDs from {self.collection_prefix}_{collection_name}. IDs: {ids}"
            )
            return self.client.delete(
                collection_name=f"{self.collection_prefix}_{collection_name}",
                ids=ids,
            )
        elif filter:
            filter_string = " && ".join(
                [
                    f'metadata["{key}"] == {json.dumps(value)}'
                    for key, value in filter.items()
                ]
            )
            log.info(
                f"Deleting items by filter from {self.collection_prefix}_{collection_name}. Filter: {filter_string}"
            )
            return self.client.delete(
                collection_name=f"{self.collection_prefix}_{collection_name}",
                filter=filter_string,
            )
        else:
            log.warning(
                f"Delete operation on {self.collection_prefix}_{collection_name} called without IDs or filter. No action taken."
            )
            return None

    def reset(self):
        # Resets the database. This will delete all collections and item entries that match the prefix.
        log.warning(
            f"Resetting Milvus: Deleting all collections with prefix '{self.collection_prefix}'."
        )
        collection_names = self.client.list_collections()
        deleted_collections = []
        for collection_name_full in collection_names:
            if collection_name_full.startswith(self.collection_prefix):
                try:
                    self.client.drop_collection(collection_name=collection_name_full)
                    deleted_collections.append(collection_name_full)
                    log.info(f"Deleted collection: {collection_name_full}")
                except Exception as e:
                    log.error(f"Error deleting collection {collection_name_full}: {e}")
        log.info(f"Milvus reset complete. Deleted collections: {deleted_collections}")

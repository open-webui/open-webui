import os # Added import
from pymilvus import MilvusClient as Client
from pymilvus import FieldSchema, DataType
import json
import logging
from typing import Optional
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

        # Get index type from environment variable.
        # Milvus standalone (local mode) supports: FLAT, IVF_FLAT, AUTOINDEX.
        # HNSW is often preferred for performance but may require a clustered Milvus setup.
        # Defaulting to AUTOINDEX for broader compatibility, especially with Milvus standalone.
        default_index_type = "AUTOINDEX"
        milvus_index_type_env = os.getenv("MILVUS_INDEX_TYPE")

        if milvus_index_type_env:
            milvus_index_type = milvus_index_type_env.upper()
            log.info(f"Milvus index type from MILVUS_INDEX_TYPE env var: {milvus_index_type}")
        else:
            milvus_index_type = default_index_type
            log.info(f"MILVUS_INDEX_TYPE env var not set, defaulting to: {milvus_index_type}")

        index_creation_params = {}
        metric_type = os.getenv("MILVUS_METRIC_TYPE", "COSINE").upper() # Default to COSINE

        if milvus_index_type == "HNSW":
            # Parameters for HNSW
            m_env = os.getenv("MILVUS_HNSW_M", "16")
            ef_construction_env = os.getenv("MILVUS_HNSW_EFCONSTRUCTION", "100")
            try:
                m_val = int(m_env)
                ef_val = int(ef_construction_env)
            except ValueError:
                log.warning(f"Invalid HNSW params M='{m_env}' or efConstruction='{ef_construction_env}'. Defaulting to M=16, efConstruction=100.")
                m_val = 16
                ef_val = 100
            index_creation_params = {"M": m_val, "efConstruction": ef_val}
            log.info(f"Using HNSW index with metric {metric_type}, params: {index_creation_params}")
        elif milvus_index_type == "IVF_FLAT":
            # Parameters for IVF_FLAT
            nlist_env = os.getenv("MILVUS_IVF_FLAT_NLIST", "128")
            try:
                nlist = int(nlist_env)
            except ValueError:
                log.warning(f"Invalid MILVUS_IVF_FLAT_NLIST value '{nlist_env}'. Defaulting to 128.")
                nlist = 128
            index_creation_params = {"nlist": nlist}
            log.info(f"Using IVF_FLAT index with metric {metric_type}, params: {index_creation_params}")
        elif milvus_index_type == "FLAT":
            log.info(f"Using FLAT index with metric {metric_type} (no specific build-time params).")
            # No specific build-time parameters needed for FLAT
        elif milvus_index_type == "AUTOINDEX":
            log.info(f"Using AUTOINDEX with metric {metric_type} (params managed by Milvus).")
            # No specific build-time parameters needed for AUTOINDEX
        else:
            log.warning(
                f"Unsupported or unrecognized MILVUS_INDEX_TYPE: '{milvus_index_type}'. "
                f"Falling back to '{default_index_type}'. "
                f"Supported types: HNSW, IVF_FLAT, FLAT, AUTOINDEX."
            )
            milvus_index_type = default_index_type # Fallback to a safe default
            # index_creation_params remains {} which is fine for AUTOINDEX/FLAT
            log.info(f"Fell back to {default_index_type} index with metric {metric_type}.")


        index_params.add_index(
            field_name="vector",
            index_type=milvus_index_type,
            metric_type=metric_type,
            params=index_creation_params,
        )

        self.client.create_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            schema=schema,
            index_params=index_params,
        )
        log.info(f"Successfully created collection '{self.collection_prefix}_{collection_name}' with index type '{milvus_index_type}' and metric '{metric_type}'.")


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
        # Construct the filter string for querying
        collection_name = collection_name.replace("-", "_")
        if not self.has_collection(collection_name):
            log.warning(f"Query attempted on non-existent collection: {self.collection_prefix}_{collection_name}")
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
            # Milvus default limit for query if not specified is 16384, but docs mention iteration.
            # Let's set a practical high number if "all" is intended, or handle true pagination.
            # For now, if limit is None, we'll fetch in batches up to a very large number.
            # This part could be refined based on expected use cases for "get all".
            # For this function signature, None implies "as many as possible" up to Milvus limits.
            limit = 16384 * 10 # A large number to signify fetching many, will be capped by actual data or max_limit per call.
            log.info(f"Limit not specified for query, fetching up to {limit} results in batches.")


        # Initialize offset and remaining to handle pagination
        offset = 0
        remaining = limit
        
        try:
            log.info(f"Querying collection {self.collection_prefix}_{collection_name} with filter: '{filter_string}', limit: {limit}")
            # Loop until there are no more items to fetch or the desired limit is reached
            while remaining > 0:
                current_fetch = min(max_limit, remaining if isinstance(remaining, int) else max_limit)
                log.debug(f"Querying with offset: {offset}, current_fetch: {current_fetch}")
                
                results = self.client.query(
                    collection_name=f"{self.collection_prefix}_{collection_name}",
                    filter=filter_string,
                    output_fields=["id", "data", "metadata"], # Explicitly list needed fields. Vector not usually needed in query.
                    limit=current_fetch,
                    offset=offset,
                )
                
                if not results:
                    log.debug("No more results from query.")
                    break
                
                all_results.extend(results)
                results_count = len(results)
                log.debug(f"Fetched {results_count} results in this batch.")

                if isinstance(remaining, int):
                    remaining -= results_count
                
                offset += results_count
                
                # Break the loop if the results returned are less than the requested fetch count (means end of data)
                if results_count < current_fetch:
                    log.debug("Fetched less than requested, assuming end of results for this query.")
                    break
            
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
        log.warning(f"Fetching ALL items from collection '{self.collection_prefix}_{collection_name}'. This might be slow for large collections.")
        # Using query with a trivial filter to get all items.
        # This will use the paginated query logic.
        return self.query(collection_name=collection_name, filter={}, limit=None)


    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection_name = collection_name.replace("-", "_")
        if not self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{collection_name}"
        ):
            log.info(f"Collection {self.collection_prefix}_{collection_name} does not exist. Creating now.")
            if not items:
                log.error(f"Cannot create collection {self.collection_prefix}_{collection_name} without items to determine dimension.")
                raise ValueError("Cannot create Milvus collection without items to determine vector dimension.")
            self._create_collection(
                collection_name=collection_name, dimension=len(items[0]["vector"])
            )
        
        log.info(f"Inserting {len(items)} items into collection {self.collection_prefix}_{collection_name}.")
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
            log.info(f"Collection {self.collection_prefix}_{collection_name} does not exist for upsert. Creating now.")
            if not items:
                log.error(f"Cannot create collection {self.collection_prefix}_{collection_name} for upsert without items to determine dimension.")
                raise ValueError("Cannot create Milvus collection for upsert without items to determine vector dimension.")
            self._create_collection(
                collection_name=collection_name, dimension=len(items[0]["vector"])
            )
        
        log.info(f"Upserting {len(items)} items into collection {self.collection_prefix}_{collection_name}.")
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
        # Delete the items from the collection based on the ids or filter.
        collection_name = collection_name.replace("-", "_")
        if not self.has_collection(collection_name):
            log.warning(f"Delete attempted on non-existent collection: {self.collection_prefix}_{collection_name}")
            return None

        if ids:
            log.info(f"Deleting items by IDs from {self.collection_prefix}_{collection_name}. IDs: {ids}")
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
            log.info(f"Deleting items by filter from {self.collection_prefix}_{collection_name}. Filter: {filter_string}")
            return self.client.delete(
                collection_name=f"{self.collection_prefix}_{collection_name}",
                filter=filter_string,
            )
        else:
            log.warning(f"Delete operation on {self.collection_prefix}_{collection_name} called without IDs or filter. No action taken.")
            return None


    def reset(self):
        # Resets the database. This will delete all collections and item entries that match the prefix.
        log.warning(f"Resetting Milvus: Deleting all collections with prefix '{self.collection_prefix}'.")
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

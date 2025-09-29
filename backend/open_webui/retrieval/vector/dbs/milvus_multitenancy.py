import logging
from typing import Optional, Tuple, List, Dict, Any

from open_webui.config import (
    MILVUS_URI,
    MILVUS_TOKEN,
    MILVUS_DB,
    MILVUS_COLLECTION_PREFIX,
    MILVUS_INDEX_TYPE,
    MILVUS_METRIC_TYPE,
    MILVUS_HNSW_M,
    MILVUS_HNSW_EFCONSTRUCTION,
    MILVUS_IVF_FLAT_NLIST,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from pymilvus import (
    connections,
    utility,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

RESOURCE_ID_FIELD = "resource_id"


class MilvusClient(VectorDBBase):
    def __init__(self):
        # Milvus collection names can only contain numbers, letters, and underscores.
        self.collection_prefix = MILVUS_COLLECTION_PREFIX.replace("-", "_")
        connections.connect(
            alias="default",
            uri=MILVUS_URI,
            token=MILVUS_TOKEN,
            db_name=MILVUS_DB,
        )

        # Main collection types for multi-tenancy
        self.MEMORY_COLLECTION = f"{self.collection_prefix}_memories"
        self.KNOWLEDGE_COLLECTION = f"{self.collection_prefix}_knowledge"
        self.FILE_COLLECTION = f"{self.collection_prefix}_files"
        self.WEB_SEARCH_COLLECTION = f"{self.collection_prefix}_web_search"
        self.HASH_BASED_COLLECTION = f"{self.collection_prefix}_hash_based"
        self.shared_collections = [
            self.MEMORY_COLLECTION,
            self.KNOWLEDGE_COLLECTION,
            self.FILE_COLLECTION,
            self.WEB_SEARCH_COLLECTION,
            self.HASH_BASED_COLLECTION,
        ]

    def _get_collection_and_resource_id(self, collection_name: str) -> Tuple[str, str]:
        """
        Maps the traditional collection name to multi-tenant collection and resource ID.

        WARNING: This mapping relies on current Open WebUI naming conventions for
        collection names. If Open WebUI changes how it generates collection names
        (e.g., "user-memory-" prefix, "file-" prefix, web search patterns, or hash
        formats), this mapping will break and route data to incorrect collections.
        POTENTIALLY CAUSING HUGE DATA CORRUPTION, DATA CONSISTENCY ISSUES AND INCORRECT
        DATA MAPPING INSIDE THE DATABASE.
        """
        resource_id = collection_name

        if collection_name.startswith("user-memory-"):
            return self.MEMORY_COLLECTION, resource_id
        elif collection_name.startswith("file-"):
            return self.FILE_COLLECTION, resource_id
        elif collection_name.startswith("web-search-"):
            return self.WEB_SEARCH_COLLECTION, resource_id
        elif len(collection_name) == 63 and all(
            c in "0123456789abcdef" for c in collection_name
        ):
            return self.HASH_BASED_COLLECTION, resource_id
        else:
            return self.KNOWLEDGE_COLLECTION, resource_id

    def _create_shared_collection(self, mt_collection_name: str, dimension: int):
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                auto_id=False,
                max_length=36,
            ),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name=RESOURCE_ID_FIELD, dtype=DataType.VARCHAR, max_length=255),
        ]
        schema = CollectionSchema(fields, "Shared collection for multi-tenancy")
        collection = Collection(mt_collection_name, schema)

        index_params = {
            "metric_type": MILVUS_METRIC_TYPE,
            "index_type": MILVUS_INDEX_TYPE,
            "params": {},
        }
        if MILVUS_INDEX_TYPE == "HNSW":
            index_params["params"] = {
                "M": MILVUS_HNSW_M,
                "efConstruction": MILVUS_HNSW_EFCONSTRUCTION,
            }
        elif MILVUS_INDEX_TYPE == "IVF_FLAT":
            index_params["params"] = {"nlist": MILVUS_IVF_FLAT_NLIST}

        collection.create_index("vector", index_params)
        collection.create_index(RESOURCE_ID_FIELD)
        log.info(f"Created shared collection: {mt_collection_name}")
        return collection

    def _ensure_collection(self, mt_collection_name: str, dimension: int):
        if not utility.has_collection(mt_collection_name):
            self._create_shared_collection(mt_collection_name, dimension)

    def has_collection(self, collection_name: str) -> bool:
        mt_collection, resource_id = self._get_collection_and_resource_id(
            collection_name
        )
        if not utility.has_collection(mt_collection):
            return False

        collection = Collection(mt_collection)
        collection.load()
        res = collection.query(expr=f"{RESOURCE_ID_FIELD} == '{resource_id}'", limit=1)
        return len(res) > 0

    def upsert(self, collection_name: str, items: List[VectorItem]):
        if not items:
            return
        mt_collection, resource_id = self._get_collection_and_resource_id(
            collection_name
        )
        dimension = len(items[0]["vector"])
        self._ensure_collection(mt_collection, dimension)
        collection = Collection(mt_collection)

        entities = [
            {
                "id": item["id"],
                "vector": item["vector"],
                "text": item["text"],
                "metadata": item["metadata"],
                RESOURCE_ID_FIELD: resource_id,
            }
            for item in items
        ]
        collection.insert(entities)
        collection.flush()

    def search(
        self, collection_name: str, vectors: List[List[float]], limit: int
    ) -> Optional[SearchResult]:
        if not vectors:
            return None

        mt_collection, resource_id = self._get_collection_and_resource_id(
            collection_name
        )
        if not utility.has_collection(mt_collection):
            return None

        collection = Collection(mt_collection)
        collection.load()

        search_params = {"metric_type": MILVUS_METRIC_TYPE, "params": {}}
        results = collection.search(
            data=vectors,
            anns_field="vector",
            param=search_params,
            limit=limit,
            expr=f"{RESOURCE_ID_FIELD} == '{resource_id}'",
            output_fields=["id", "text", "metadata"],
        )

        ids, documents, metadatas, distances = [], [], [], []
        for hits in results:
            batch_ids, batch_docs, batch_metadatas, batch_dists = [], [], [], []
            for hit in hits:
                batch_ids.append(hit.entity.get("id"))
                batch_docs.append(hit.entity.get("text"))
                batch_metadatas.append(hit.entity.get("metadata"))
                batch_dists.append(hit.distance)
            ids.append(batch_ids)
            documents.append(batch_docs)
            metadatas.append(batch_metadatas)
            distances.append(batch_dists)

        return SearchResult(
            ids=ids, documents=documents, metadatas=metadatas, distances=distances
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ):
        mt_collection, resource_id = self._get_collection_and_resource_id(
            collection_name
        )
        if not utility.has_collection(mt_collection):
            return

        collection = Collection(mt_collection)

        # Build expression
        expr = [f"{RESOURCE_ID_FIELD} == '{resource_id}'"]
        if ids:
            # Milvus expects a string list for 'in' operator
            id_list_str = ", ".join([f"'{id_val}'" for id_val in ids])
            expr.append(f"id in [{id_list_str}]")

        if filter:
            for key, value in filter.items():
                expr.append(f"metadata['{key}'] == '{value}'")

        collection.delete(" and ".join(expr))

    def reset(self):
        for collection_name in self.shared_collections:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

    def delete_collection(self, collection_name: str):
        mt_collection, resource_id = self._get_collection_and_resource_id(
            collection_name
        )
        if not utility.has_collection(mt_collection):
            return

        collection = Collection(mt_collection)
        collection.delete(f"{RESOURCE_ID_FIELD} == '{resource_id}'")

    def query(
        self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None
    ) -> Optional[GetResult]:
        mt_collection, resource_id = self._get_collection_and_resource_id(
            collection_name
        )
        if not utility.has_collection(mt_collection):
            return None

        collection = Collection(mt_collection)
        collection.load()

        expr = [f"{RESOURCE_ID_FIELD} == '{resource_id}'"]
        if filter:
            for key, value in filter.items():
                if isinstance(value, str):
                    expr.append(f"metadata['{key}'] == '{value}'")
                else:
                    expr.append(f"metadata['{key}'] == {value}")

        results = collection.query(
            expr=" and ".join(expr),
            output_fields=["id", "text", "metadata"],
            limit=limit,
        )

        ids = [res["id"] for res in results]
        documents = [res["text"] for res in results]
        metadatas = [res["metadata"] for res in results]

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def get(self, collection_name: str) -> Optional[GetResult]:
        return self.query(collection_name, filter={}, limit=None)

    def insert(self, collection_name: str, items: List[VectorItem]):
        return self.upsert(collection_name, items)

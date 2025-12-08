from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk, scan
from typing import Optional

from open_webui.retrieval.vector.utils import process_metadata
from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import (
    OPENSEARCH_URI,
    OPENSEARCH_SSL,
    OPENSEARCH_CERT_VERIFY,
    OPENSEARCH_USERNAME,
    OPENSEARCH_PASSWORD,
)


class OpenSearchClient(VectorDBBase):
    def __init__(self):
        self.index_prefix = "open_webui"
        self.client = OpenSearch(
            hosts=[OPENSEARCH_URI],
            use_ssl=OPENSEARCH_SSL,
            verify_certs=OPENSEARCH_CERT_VERIFY,
            http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
        )

    def _get_index_name(self, dimension: int) -> str:
        return f"{self.index_prefix}_d{str(dimension)}"

    def _result_to_get_result(self, result) -> GetResult | None:
        if not result["hits"]["hits"]:
            return None

        ids = []
        documents = []
        metadatas = []

        for hit in result["hits"]["hits"]:
            ids.append(hit["_id"])
            documents.append(hit["_source"].get("text"))
            metadatas.append(hit["_source"].get("metadata"))

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def _result_to_search_result(self, result) -> SearchResult | None:
        if not result["hits"]["hits"]:
            return None

        ids = []
        distances = []
        documents = []
        metadatas = []

        for hit in result["hits"]["hits"]:
            ids.append(hit["_id"])
            distances.append(hit["_score"])
            documents.append(hit["_source"].get("text"))
            metadatas.append(hit["_source"].get("metadata"))

        return SearchResult(
            ids=[ids],
            distances=[distances],
            documents=[documents],
            metadatas=[metadatas],
        )

    def _create_index(self, dimension: int):
        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "collection": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    "vector": {
                        "type": "knn_vector",
                        "dimension": dimension,  # Adjust based on your vector dimensions
                        "index": True,
                        "similarity": "faiss",
                        "method": {
                            "name": "hnsw",
                            "space_type": "innerproduct",  # Use inner product to approximate cosine similarity
                            "engine": "faiss",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16,
                            },
                        },
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "object"},
                }
            },
        }
        self.client.indices.create(index=self._get_index_name(dimension), body=body)

    def _create_batches(self, items: list[VectorItem], batch_size=100):
        for i in range(0, len(items), batch_size):
            yield items[i : min(i + batch_size, len(items))]

    def has_collection(self, collection_name) -> bool:
        query_body = {"query": {"bool": {"filter": []}}}
        query_body["query"]["bool"]["filter"].append(
            {"term": {"collection": collection_name}}
        )

        try:
            response = self.client.count(index=f"{self.index_prefix}*", body=query_body)
            return response["count"] > 0
        except Exception as e:
            return False

    def delete_collection(self, collection_name: str):
        query = {"query": {"term": {"collection": collection_name}}}
        self.client.delete_by_query(index=f"{self.index_prefix}*", body=query)

    def search(
        self,
        collection_name: str,
        vectors: list[list[float | int]],
        filter: Optional[dict] = None,
        limit: int = 10,
    ) -> Optional[SearchResult]:
        query = {
            "size": limit,
            "_source": ["text", "metadata"],
            "query": {
                "script_score": {
                    "query": {
                        "bool": {"filter": [{"term": {"collection": collection_name}}]}
                    },
                    "script": {
                        "source": "(cosineSimilarity(params.query_value, doc[params.field]) + 1.0) / 2.0",
                        "params": {
                            "field": "vector",
                            "query_value": vectors[0],
                        },  # Assuming single query vector
                    },
                }
            },
        }

        try:
            result = self.client.search(
                index=self._get_index_name(len(vectors[0])), body=query
            )

            return self._result_to_search_result(result)
        except Exception as e:
            return None

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        if not self.has_collection(collection_name):
            return None

        query_body = {
            "query": {"bool": {"filter": []}},
            "_source": ["text", "metadata"],
        }

        for field, value in filter.items():
            query_body["query"]["bool"]["filter"].append({"term": {field: value}})
        query_body["query"]["bool"]["filter"].append(
            {"term": {"collection": collection_name}}
        )
        size = limit if limit else 10

        try:
            result = self.client.search(
                index=f"{self.index_prefix}*",
                body=query_body,
                size=size,
            )

            return self._result_to_get_result(result)

        except Exception as e:
            return None

    def _has_index(self, dimension: int):
        return self.client.indices.exists(
            index=self._get_index_name(dimension=dimension)
        )

    def get_or_create_index(self, dimension: int):
        if not self._has_index(dimension=dimension):
            self._create_index(dimension=dimension)

    def get(self, collection_name: str) -> Optional[GetResult]:
        query = {
            "query": {"bool": {"filter": [{"term": {"collection": collection_name}}]}},
            "_source": ["text", "metadata"],
        }

        results = list(scan(self.client, index=f"{self.index_prefix}*", query=query))

        return self._result_to_get_result(results)

    def insert(self, collection_name: str, items: list[VectorItem]):
        dimension = len(items[0]["vector"])

        if not self._has_index(dimension):
            self._create_index(dimension)

        for batch in self._create_batches(items):
            actions = [
                {
                    "_index": self._get_index_name(dimension),
                    "_id": item["id"],
                    "_source": {
                        "collection": collection_name,
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": process_metadata(item["metadata"]),
                    },
                }
                for item in batch
            ]
            bulk(self.client, actions)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        dimension = len(items[0]["vector"])
        if not self._has_index(dimension):
            self._create_index(dimension)

        for batch in self._create_batches(items):
            actions = [
                {
                    "_op_type": "update",
                    "_index": self._get_index_name(dimension),
                    "_id": item["id"],
                    "doc": {
                        "collection": collection_name,
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": process_metadata(item["metadata"]),
                    },
                    "doc_as_upsert": True,
                }
                for item in batch
            ]
            bulk(self.client, actions)

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        query = {
            "query": {"bool": {"filter": [{"term": {"collection": collection_name}}]}}
        }

        if ids:
            query["query"]["bool"]["filter"].append({"terms": {"_id": ids}})
        elif filter:
            for field, value in filter.items():
                query["query"]["bool"]["filter"].append(
                    {"term": {f"metadata.{field}": value}}
                )

        self.client.delete_by_query(index=f"{self.index_prefix}*", body=query)

    def reset(self):
        indices = self.client.indices.get(index=f"{self.index_prefix}_*")
        for index in indices:
            self.client.indices.delete(index=index)

from opensearchpy import OpenSearch
from typing import Optional

from open_webui.apps.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    OPENSEARCH_URI,
    OPENSEARCH_SSL,
    OPENSEARCH_CERT_VERIFY,
    OPENSEARCH_USERNAME,
    OPENSEARCH_PASSWORD,
)


class OpenSearchClient:
    def __init__(self):
        self.index_prefix = "open_webui"
        self.client = OpenSearch(
            hosts=[OPENSEARCH_URI],
            use_ssl=OPENSEARCH_SSL,
            verify_certs=OPENSEARCH_CERT_VERIFY,
            http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
        )

    def _result_to_get_result(self, result) -> GetResult:
        ids = []
        documents = []
        metadatas = []

        for hit in result["hits"]["hits"]:
            ids.append(hit["_id"])
            documents.append(hit["_source"].get("text"))
            metadatas.append(hit["_source"].get("metadata"))

        return GetResult(ids=ids, documents=documents, metadatas=metadatas)

    def _result_to_search_result(self, result) -> SearchResult:
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
            ids=ids, distances=distances, documents=documents, metadatas=metadatas
        )

    def _create_index(self, index_name: str, dimension: int):
        body = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": dimension,  # Adjust based on your vector dimensions
                        "index": true,
                        "similarity": "faiss",
                        "method": {
                            "name": "hnsw",
                            "space_type": "ip",  # Use inner product to approximate cosine similarity
                            "engine": "faiss",
                            "ef_construction": 128,
                            "m": 16,
                        },
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "object"},
                }
            }
        }
        self.client.indices.create(index=f"{self.index_prefix}_{index_name}", body=body)

    def _create_batches(self, items: list[VectorItem], batch_size=100):
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]

    def has_collection(self, index_name: str) -> bool:
        # has_collection here means has index.
        # We are simply adapting to the norms of the other DBs.
        return self.client.indices.exists(index=f"{self.index_prefix}_{index_name}")

    def delete_colleciton(self, index_name: str):
        # delete_collection here means delete index.
        # We are simply adapting to the norms of the other DBs.
        self.client.indices.delete(index=f"{self.index_prefix}_{index_name}")

    def search(
        self, index_name: str, vectors: list[list[float]], limit: int
    ) -> Optional[SearchResult]:
        query = {
            "size": limit,
            "_source": ["text", "metadata"],
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.vector, 'vector') + 1.0",
                        "params": {
                            "vector": vectors[0]
                        },  # Assuming single query vector
                    },
                }
            },
        }

        result = self.client.search(
            index=f"{self.index_prefix}_{index_name}", body=query
        )

        return self._result_to_search_result(result)

    def get_or_create_index(self, index_name: str, dimension: int):
        if not self.has_index(index_name):
            self._create_index(index_name, dimension)

    def get(self, index_name: str) -> Optional[GetResult]:
        query = {"query": {"match_all": {}}, "_source": ["text", "metadata"]}

        result = self.client.search(
            index=f"{self.index_prefix}_{index_name}", body=query
        )
        return self._result_to_get_result(result)

    def insert(self, index_name: str, items: list[VectorItem]):
        if not self.has_index(index_name):
            self._create_index(index_name, dimension=len(items[0]["vector"]))

        for batch in self._create_batches(items):
            actions = [
                {
                    "index": {
                        "_id": item["id"],
                        "_source": {
                            "vector": item["vector"],
                            "text": item["text"],
                            "metadata": item["metadata"],
                        },
                    }
                }
                for item in batch
            ]
            self.client.bulk(actions)

    def upsert(self, index_name: str, items: list[VectorItem]):
        if not self.has_index(index_name):
            self._create_index(index_name, dimension=len(items[0]["vector"]))

        for batch in self._create_batches(items):
            actions = [
                {
                    "index": {
                        "_id": item["id"],
                        "_source": {
                            "vector": item["vector"],
                            "text": item["text"],
                            "metadata": item["metadata"],
                        },
                    }
                }
                for item in batch
            ]
            self.client.bulk(actions)

    def delete(self, index_name: str, ids: list[str]):
        actions = [
            {"delete": {"_index": f"{self.index_prefix}_{index_name}", "_id": id}}
            for id in ids
        ]
        self.client.bulk(body=actions)

    def reset(self):
        indices = self.client.indices.get(index=f"{self.index_prefix}_*")
        for index in indices:
            self.client.indices.delete(index=index)

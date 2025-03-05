from elasticsearch import Elasticsearch, BadRequestError
from typing import Optional
import ssl
from elasticsearch.helpers import bulk, scan
from open_webui.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    ELASTICSEARCH_URL,
    ELASTICSEARCH_CA_CERTS,
    ELASTICSEARCH_API_KEY,
    ELASTICSEARCH_USERNAME,
    ELASTICSEARCH_PASSWORD,
    ELASTICSEARCH_CLOUD_ID,
    SSL_ASSERT_FINGERPRINT,
)


class ElasticsearchClient:
    """
    Important:
    in order to reduce the number of indexes and since the embedding vector length is fixed, we avoid creating
    an index for each file but store it as a text field, while seperating to different index
    baesd on the embedding length.
    """

    def __init__(self):
        self.index_prefix = "open_webui_collections"
        self.client = Elasticsearch(
            hosts=[ELASTICSEARCH_URL],
            ca_certs=ELASTICSEARCH_CA_CERTS,
            api_key=ELASTICSEARCH_API_KEY,
            cloud_id=ELASTICSEARCH_CLOUD_ID,
            basic_auth=(
                (ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
                if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
                else None
            ),
            ssl_assert_fingerprint=SSL_ASSERT_FINGERPRINT,
        )

    # Status: works
    def _get_index_name(self, dimension: int) -> str:
        return f"{self.index_prefix}_d{str(dimension)}"

    # Status: works
    def _scan_result_to_get_result(self, result) -> GetResult:
        if not result:
            return None
        ids = []
        documents = []
        metadatas = []

        for hit in result:
            ids.append(hit["_id"])
            documents.append(hit["_source"].get("text"))
            metadatas.append(hit["_source"].get("metadata"))

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    # Status: works
    def _result_to_get_result(self, result) -> GetResult:
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

    # Status: works
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
            ids=[ids],
            distances=[distances],
            documents=[documents],
            metadatas=[metadatas],
        )

    # Status: works
    def _create_index(self, dimension: int):
        body = {
            "mappings": {
                "properties": {
                    "collection": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": dimension,  # Adjust based on your vector dimensions
                        "index": True,
                        "similarity": "cosine",
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "object"},
                }
            }
        }
        self.client.indices.create(index=self._get_index_name(dimension), body=body)

    # Status: works

    def _create_batches(self, items: list[VectorItem], batch_size=100):
        for i in range(0, len(items), batch_size):
            yield items[i : min(i + batch_size, len(items))]

    # Status: works
    def has_collection(self, collection_name) -> bool:
        query_body = {"query": {"bool": {"filter": []}}}
        query_body["query"]["bool"]["filter"].append(
            {"term": {"collection": collection_name}}
        )

        try:
            result = self.client.count(index=f"{self.index_prefix}*", body=query_body)

            return result.body["count"] > 0
        except Exception as e:
            return None

    # @TODO: Make this delete a collection and not an index
    def delete_colleciton(self, collection_name: str):
        # TODO: fix this to include the dimension or a * prefix
        # delete_collection here means delete a bunch of documents for an index.
        # We are simply adapting to the norms of the other DBs.
        self.client.indices.delete(index=self._get_collection_name(collection_name))

    # Status: works
    def search(
        self, collection_name: str, vectors: list[list[float]], limit: int
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
                        "source": "cosineSimilarity(params.vector, 'vector') + 1.0",
                        "params": {
                            "vector": vectors[0]
                        },  # Assuming single query vector
                    },
                }
            },
        }

        result = self.client.search(
            index=self._get_index_name(len(vectors[0])), body=query
        )

        return self._result_to_search_result(result)

    # Status: only tested halfwat
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

    # Status: works
    def _has_index(self, dimension: int):
        return self.client.indices.exists(
            index=self._get_index_name(dimension=dimension)
        )

    def get_or_create_index(self, dimension: int):
        if not self._has_index(dimension=dimension):
            self._create_index(dimension=dimension)

    # Status: works
    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        query = {
            "query": {"bool": {"filter": [{"term": {"collection": collection_name}}]}},
            "_source": ["text", "metadata"],
        }
        results = list(scan(self.client, index=f"{self.index_prefix}*", query=query))

        return self._scan_result_to_get_result(results)

    # Status: works
    def insert(self, collection_name: str, items: list[VectorItem]):
        if not self._has_index(dimension=len(items[0]["vector"])):
            self._create_index(dimension=len(items[0]["vector"]))

        for batch in self._create_batches(items):
            actions = [
                {
                    "_index": self._get_index_name(dimension=len(items[0]["vector"])),
                    "_id": item["id"],
                    "_source": {
                        "collection": collection_name,
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": item["metadata"],
                    },
                }
                for item in batch
            ]
            bulk(self.client, actions)

    # Status: should work
    def upsert(self, collection_name: str, items: list[VectorItem]):
        if not self._has_index(dimension=len(items[0]["vector"])):
            self._create_index(collection_name, dimension=len(items[0]["vector"]))

        for batch in self._create_batches(items):
            actions = [
                {
                    "_index": self._get_index_name(dimension=len(items[0]["vector"])),
                    "_id": item["id"],
                    "_source": {
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": item["metadata"],
                    },
                }
                for item in batch
            ]
            self.client.bulk(actions)

    # TODO: This currently deletes by * which is not always supported in ElasticSearch.
    # Need to read a bit before changing. Also, need to delete from a specific collection
    def delete(self, collection_name: str, ids: list[str]):
        # Assuming ID is unique across collections and indexes
        actions = [
            {"delete": {"_index": f"{self.index_prefix}*", "_id": id}} for id in ids
        ]
        self.client.bulk(body=actions)

    def reset(self):
        indices = self.client.indices.get(index=f"{self.index_prefix}*")
        for index in indices:
            self.client.indices.delete(index=index)

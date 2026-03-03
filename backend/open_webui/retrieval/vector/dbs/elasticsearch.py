from elasticsearch import Elasticsearch, BadRequestError
from typing import Optional
import ssl
from elasticsearch.helpers import bulk, scan

from open_webui.retrieval.vector.utils import process_metadata
from open_webui.retrieval.vector.main import (
    VectorDBBase,
    VectorItem,
    SearchResult,
    GetResult,
)
from open_webui.config import (
    ELASTICSEARCH_URL,
    ELASTICSEARCH_CA_CERTS,
    ELASTICSEARCH_API_KEY,
    ELASTICSEARCH_USERNAME,
    ELASTICSEARCH_PASSWORD,
    ELASTICSEARCH_CLOUD_ID,
    ELASTICSEARCH_INDEX_PREFIX,
    SSL_ASSERT_FINGERPRINT,
)


class ElasticsearchClient(VectorDBBase):
    """
    Important:
    in order to reduce the number of indexes and since the embedding vector length is fixed, we avoid creating
    an index for each file but store it as a text field, while seperating to different index
    baesd on the embedding length.
    """

    def __init__(self):
        self.index_prefix = ELASTICSEARCH_INDEX_PREFIX
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
                "dynamic_templates": [
                    {
                        "strings": {
                            "match_mapping_type": "string",
                            "mapping": {"type": "keyword"},
                        }
                    }
                ],
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
                },
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

    def delete_collection(self, collection_name: str):
        query = {"query": {"term": {"collection": collection_name}}}
        self.client.delete_by_query(index=f"{self.index_prefix}*", body=query)

    # Status: works
    def search(
        self,
        collection_name: str,
        vectors: list[list[float]],
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
                        "metadata": process_metadata(item["metadata"]),
                    },
                }
                for item in batch
            ]
            bulk(self.client, actions)

    # Upsert documents using the update API with doc_as_upsert=True.
    def upsert(self, collection_name: str, items: list[VectorItem]):
        if not self._has_index(dimension=len(items[0]["vector"])):
            self._create_index(dimension=len(items[0]["vector"]))
        for batch in self._create_batches(items):
            actions = [
                {
                    "_op_type": "update",
                    "_index": self._get_index_name(dimension=len(item["vector"])),
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

    # Delete specific documents from a collection by filtering on both collection and document IDs.
    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):

        query = {
            "query": {"bool": {"filter": [{"term": {"collection": collection_name}}]}}
        }
        # logic based on chromaDB
        if ids:
            query["query"]["bool"]["filter"].append({"terms": {"_id": ids}})
        elif filter:
            for field, value in filter.items():
                query["query"]["bool"]["filter"].append(
                    {"term": {f"metadata.{field}": value}}
                )

        self.client.delete_by_query(index=f"{self.index_prefix}*", body=query)

    def reset(self):
        indices = self.client.indices.get(index=f"{self.index_prefix}*")
        for index in indices:
            self.client.indices.delete(index=index)

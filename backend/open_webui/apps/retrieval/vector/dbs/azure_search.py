import json
import logging
from typing import Optional
from collections import defaultdict

from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery, VectorizableTextQuery
from azure.search.documents.indexes.models import (
    AzureOpenAIModelName,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    ComplexField,
    SearchIndex,
    SimpleField,
    SearchField,
    SearchableField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    HnswParameters,
    SemanticSearch,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField
)

from open_webui.apps.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_API_KEY,
    AZURE_SEARCH_INDEX_NAME,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION
)
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

RRF_K = 60
REWRITE_PROMPT = """You are a helpful assistant. You help users search for the answers to their questions.
You have access to Azure AI Search index with 100's of documents. Rewrite the following question into 3 useful search queries to find the most relevant documents.
Always rewrite queries in the user input language.
Always output a JSON object in the following format:
===
Input: "scalable storage solution"
Output: { "queries": ["what is a scalable storage solution in Azure", "how to create a scalable storage solution", "steps to create a scalable storage solution"] }
===
"""


class AzureSearchClient:
    def __init__(self):
        self.search_endpoint = AZURE_SEARCH_ENDPOINT
        self.search_api_key = AZURE_SEARCH_API_KEY
        self.chat_endpoint = AZURE_OPENAI_ENDPOINT
        self.chat_api_key = AZURE_OPENAI_API_KEY
        self.chat_api_version = AZURE_OPENAI_API_VERSION
        
        self.credential = AzureKeyCredential(self.search_api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self.credential
        )
        self.chat_client = AzureOpenAI(
            azure_endpoint = self.chat_endpoint,
            api_key = self.chat_api_key,
            api_version = self.chat_api_version,
        )

        self.search_client = None
    
    def _results_to_search_results(self, results):
        search_results = {}

        for result in results:
            collection = result.get("metadata").get("file_id")
            if collection not in search_results:
                search_results[collection] = defaultdict(list)

            collection_results = search_results[collection]
            collection_results["ids"].append(result.get("id"))
            collection_results["distances"].append(result.get("rrf_score"))
            collection_results["documents"].append(result.get("chunk"))
            collection_results["metadatas"].append(result.get("metadata"))

        search_results = {
            collection: SearchResult(
                ids=[collection_results["ids"]],
                distances=[collection_results["distances"]],
                documents=[collection_results["documents"]],
                metadatas=[collection_results["metadatas"]],
            )
            for collection, collection_results in search_results.items()
        }

        return search_results

    def _create_index(self, dimension: int):
        # Define fields
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, filterable=True, key=True),
            SimpleField(name="collection", type=SearchFieldDataType.String, filterable=True),
            # SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="chunk", type=SearchFieldDataType.String),
            SearchField(
                name="text_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=dimension,  # For text-embedding-ada-002, this should be 1536
                vector_search_profile_name="vector-index-pp-search-profile",
                searchable=True
            ),
            ComplexField(
                name="metadata",
                fields=[
                    SimpleField(name="file_id", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="hash", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="name", type=SearchFieldDataType.String),
                    SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=False),
                    SimpleField(name="source", type=SearchFieldDataType.String, filterable=False),
                    SimpleField(name="start_index", type=SearchFieldDataType.Int32, filterable=False)
                ]
            )
        ]

        # Define vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="vector-index-pp-search-profile",
                    algorithm_configuration_name="vector-index-pp-algorithm",
                    vectorizer_name="vector-index-pp-vectorizer"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="vector-index-pp-algorithm",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500
                    )
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name="vector-index-pp-vectorizer",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=AZURE_OPENAI_ENDPOINT,
                        deployment_name=AzureOpenAIModelName.TEXT_EMBEDDING_ADA002,
                        api_key=AZURE_OPENAI_API_KEY,
                        model_name=AzureOpenAIModelName.TEXT_EMBEDDING_ADA002
                    )
                )
            ]
        )

        # Define semantic configuration
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="vector-index-pp-semantic-configuration",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="metadata/name"),
                        content_fields=[SemanticField(field_name="chunk")]
                    )
                )
            ]
        )

        # Create the index
        index = SearchIndex(
            name=AZURE_SEARCH_INDEX_NAME,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )

        # Create the index in Azure Search
        self.index_client.create_index(index)
    
    def load_search_client(self):
        if self.search_client is None:
            self.search_client = self.index_client.get_search_client(AZURE_SEARCH_INDEX_NAME)
    
    def has_index(self) -> bool:
        # Check if the index (collection) exists in Azure AI Search
        collections = self.index_client.list_index_names()
        return AZURE_SEARCH_INDEX_NAME in collections

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        if not self.has_index():
            return False
        
        self.load_search_client()
        results = self.search_client.search(
            filter=f"collection eq '{collection_name}'",
            include_total_count=True
        )
        return results.get_count() > 0

    def delete_collection(self, collection_name: str):
        # Delete the index (collection) from Azure AI Search
        return self.index_client.delete_index(collection_name)

    def hybrid_search(
        self, query: str, collections: list[str], file_ids: list[str], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        self.load_search_client()

        filter_query = f"not search.in(collection, '{','.join(collections)}') and search.in(metadata/file_id, '{','.join(file_ids)}')"
        results = self.search_client.search(
            search_text=query,
            query_type="semantic",
            vector_queries=[VectorizableTextQuery(text=query, k_nearest_neighbors=50, fields="text_vector")],
            semantic_configuration_name="vector-index-pp-semantic-configuration",
            filter=filter_query,
            top=limit
        )
        
        return results
    
    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        # Query the items from the collection based on the filter.
        try:
            if not self.has_collection(collection_name):
                return GetResult(ids=[[]], documents=None, metadatas=None)
            
            filter_query = " and ".join(
                [
                    f"metadata/{key} eq '{value}'"
                    for key, value in filter.items()
                ]
            )
            search_results = self.search_client.search(
                filter=filter_query,
                top=limit
            )

            # Extract results (ids, documents, and metadatas)
            ids = []
            documents = []
            metadatas = []
            for result in search_results:
                ids.append(result["id"])
                documents.append(result["chunk"])  # Assuming "chunk" is the document field
                metadatas.append(result["metadata"])  # Assuming "metadata" is in the result
            
            return GetResult(
                ids=[ids],
                documents=[documents],
                metadatas=[metadatas]
            )
        except Exception as e:
            print(e)
            return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the index (collection), if the collection does not exist, it will be created.
        self.upsert(collection_name, items)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        if not self.has_index():
            dimension = len(items[0]["vector"])
            self._create_index(dimension)
        
        self.load_search_client()
        documents = [
            {
                "id": item["id"],  # Unique ID of the document
                "collection": collection_name,  # Collection name
                # "title": item["metadata"]["name"],  # Document title (from metadata)
                "chunk": item["text"],  # Text content (document chunk)
                "text_vector": item["vector"],  # Embedding vector (1536 dimensions)

                # Metadata as a complex field
                "metadata": {
                    "file_id": item["metadata"]["file_id"],  # File ID
                    "hash": item["metadata"]["hash"],  # Hash of the document
                    "name": item["metadata"]["name"],  # Name of the document
                    "page": item["metadata"]["page"] if "page" in item["metadata"] else 0,  # Page number
                    "source": item["metadata"]["source"] if "source" in item["metadata"] else item["metadata"]["path"],  # File source path
                    "start_index": item["metadata"]["start_index"]  # Start index of the chunk in the document
                }
            }
            for item in items
        ]
        self.search_client.upload_documents(documents)

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        # Delete the items from the index based on the ids.
        self.load_search_client()
        if ids:
            documents = [{"id": id for id in ids}]
        elif filter:
            key, value = list(filter.items())[0]
            fitler_query = f"metadata/{key} eq '{value}'"
            search_results = self.search_client.search(
                filter=fitler_query
            )
            pages = search_results.by_page()
            documents = [
                {"id": document["id"]}
                for page in pages
                for document in page
            ]
        
        self.search_client.delete_documents(documents)

    def reset(self):
        # Resets the service. This will delete all indexes and item entries.
        self.index_client.delete_index(AZURE_SEARCH_INDEX_NAME)

    def rewrite_query(self, messages: list[dict]):
        messages = [
            message["content"]
            for message in messages[-10:]
        ]

        query = messages.pop()
        conversation_history = '\n'.join(messages)
        response = self.chat_client.chat.completions.create(
            model="gpt-4o",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": f"Conversation history: {conversation_history}"},
                {"role": "user", "content": f"Input: {query}"}
            ],
            temperature=0
        )
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            print("JSON decoding error:", e)
            raise

    def compute_rrf(self, rewritten_queries: list[str], collections: list[str], file_ids: list[str], limit: int):
        # Store results per query
        results_per_query = []
        
        for query in rewritten_queries['queries']:
            results = self.hybrid_search(query, collections, file_ids, limit)
            results_list = list(results)
            results_per_query.append(results_list)
        
        # Map document IDs to their ranks per query
        doc_rankings = defaultdict(dict)
        
        for q_idx, results in enumerate(results_per_query):
            for rank, result in enumerate(results):
                doc_id = result['id']  # Ensure 'chunk_id' is unique
                doc_rankings[doc_id][q_idx] = rank + 1  # Rank starts from 1
        
        # Compute RRF scores
        rrf_scores = {}
        for doc_id, ranks in doc_rankings.items():
            rrf_score = sum(1 / (RRF_K + rank) for rank in ranks.values())
            rrf_scores[doc_id] = rrf_score
        
        # Sort documents by their RRF scores in descending order
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Retrieve document details
        final_results = []
        for doc_id, score in sorted_docs:
            # Find the document in the results_per_query to get its details
            for results in results_per_query:
                for result in results:
                    if result['id'] == doc_id:
                        final_results.append({
                            'id': doc_id,
                            'collection': result.get('collection'),
                            'rrf_score': score,
                            'chunk': result.get('chunk'),
                            'metadata': result.get('metadata')
                        })
                        break
                else:
                    continue
                break
        
        return self._results_to_search_results(final_results[:limit])
        
import logging

import weaviate
from weaviate.classes.query import Filter
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery

from weaviate.util import generate_uuid5
import re

from typing import Optional, List, Union

from open_webui.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    WEAVIATE_HTTP_HOST,
    WEAVIATE_HTTP_PORT,
    WEAVIATE_GRPC_HOST,
    WEAVIATE_GRPC_PORT,
    WEAVIATE_API_KEY,
)

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def build_filter(filter_dict, operator="Equal"):
    """
    Converte um dicionário de filtros em um objeto Filter do Weaviate.

    Parâmetros:
        - filter_dict (dict): Dicionário onde as chaves são os caminhos dos campos e os valores são os valores a serem filtrados.
        - operator (str): Operador a ser usado (exemplo: "Equal", "GreaterThan", "LessThan", "Like").

    Retorna:
        - Filter: Objeto de filtro do Weaviate ou None se `filter_dict` for vazio.
    """
    if not filter_dict:
        return None  # Retorna None se não houver filtros

    filters = None

    for key, value in filter_dict.items():
        # Criando o filtro corretamente usando os métodos do Weaviate
        if operator == "Equal":
            condition = Filter.by_property(key).equal(value)
        elif operator == "GreaterThan":
            condition = Filter.by_property(key).greater_than(value)
        elif operator == "LessThan":
            condition = Filter.by_property(key).less_than(value)
        elif operator == "Like":
            condition = Filter.by_property(key).like(value)
        else:
            raise ValueError(f"Operador '{operator}' não suportado.")

        if filters is None:
            filters = condition
        else:
            filters = filters & condition  # Usa AND para combinar filtros

    return filters


class WeaviateClient:
    def __init__(self):
        self.client = weaviate.connect_to_custom(
            http_host=WEAVIATE_HTTP_HOST,  # Hostname for the HTTP API connection
            http_port=WEAVIATE_HTTP_PORT,  # Default is 80, WCD uses 443
            # Whether to use https (secure) for the HTTP API connection
            http_secure=False,
            grpc_host=WEAVIATE_GRPC_HOST,  # Hostname for the gRPC API connection
            grpc_port=WEAVIATE_GRPC_PORT,  # Default is 50051, WCD uses 443
            grpc_secure=False,  # Whether to use a secure channel for the gRPC API connection
            auth_credentials=Auth.api_key(
                WEAVIATE_API_KEY
            ),  # API key for authentication
        )

    def transform_collection_name(self, collection_name: str) -> str:
        """
        Transforms the collection name to a valid Weaviate class name.
        Weaviate class names must start with a letter and can only contain letters, numbers, and underscores.
        """
        collection_name = collection_name.replace("-", "").lower()
        if not (collection_name.startswith("file") or collection_name.startswith("collection")):
            collection_name = f"collection{collection_name}"
        return collection_name

    def has_collection(self, collection_name: str) -> bool:
        """
        Checks if a collection (class) already exists.
        """
        # try:
        collection_name = self.transform_collection_name(collection_name)
        collection_names = self.client.collections.list_all()
        return collection_name in collection_names
        # except Exception:
        #    return False

    def _ensure_collection(self, collection_name: str):
        """
        Ensures that the collection exists; if not, it creates it.
        """
        collection_name = self.transform_collection_name(collection_name)
        log.info(f"Collection para buscar: {collection_name}")
        if not self.has_collection(collection_name):
            log.info("Creating collection %s", collection_name)
            self.create_collection(collection_name)

    def create_collection(self, collection_name: str):
        """
        Creates a collection with a default configuration:
          - Uses 'text2vec-openai' vectorizer based on the 'text' property
          - Defines 'documents' and 'metadata' properties
        """
        collection_name = self.transform_collection_name(collection_name)
        self.client.collections.create(
            collection_name,
            vectorizer_config=[
                Configure.NamedVectors.text2vec_aws(
                    name="text",
                    source_properties=["text"],
                    vector_index_config=Configure.VectorIndex.hnsw(),
                    region="sa-east-1",
                    model="amazon.titan-embed-text-v2:0"
                ),
            ],
            properties=[
                Property(name="file_id", data_type=DataType.TEXT),
                Property(name="documents", data_type=DataType.TEXT),
                Property(name="hash", data_type=DataType.TEXT),
                Property(
                    name="metadata",
                    data_type=DataType.OBJECT,
                    nested_properties=[
                        Property(name="name", data_type=DataType.TEXT),
                        Property(name="content_type", data_type=DataType.TEXT),
                        # Objeto vazio
                        Property(name="size", data_type=DataType.INT),
                        Property(name="collection_name",
                                 data_type=DataType.TEXT),
                        Property(name="created_by", data_type=DataType.TEXT),
                        Property(name="file_id", data_type=DataType.TEXT),
                        Property(name="source", data_type=DataType.TEXT),
                        Property(name="start_index", data_type=DataType.INT),
                        Property(name="embedding_config",
                                 data_type=DataType.TEXT),
                        # Será armazenado como JSON string
                    ],
                ),
            ],
        )

    def delete_collection(self, collection_name: str):
        """
        Deletes a collection (class) from Weaviate.
        """
        collection_name = self.transform_collection_name(collection_name)
        self.client.collections.delete(collection_name)

    def insert(self, collection_name: str, items: List[VectorItem]):
        """
        Inserts items into the collection. If the collection does not exist, it will be created.
        Each item contains the properties 'file_id', 'text', and 'metadata'.
        """
        collection_name = self.transform_collection_name(collection_name)
        self._ensure_collection(collection_name)
        collection = self.client.collections.get(collection_name)

        data_object = [
            {
                "file_id": item["id"],  # Identificador único
                "documents": item["text"],  # Conteúdo textual
                "hash": item["metadata"]["hash"],
                "metadata": item["metadata"],  # Metadados (JSON)
            }
            for item in items
        ]

        with collection.batch.dynamic() as batch:
            for data_row in data_object:
                obj_uuid = generate_uuid5(data_row)
                batch.add_object(properties=data_row, uuid=obj_uuid)
                if batch.number_errors > 10:
                    print("Batch import stopped due to excessive errors.")
                    break

        print(
            f"Inserted {len(items)} items into collection '{collection_name}'.")

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """
        Removes all collections from Weaviate.
        WARNING: This operation deletes ALL data.
        """
        collection_name = self.transform_collection_name(collection_name)
        self._ensure_collection(collection_name)
        coll = self.client.collections.get(collection_name)
        for item in items:
            data = {
                "file_id": item["id"],
                "documents": item["text"],
                "hash": item["metadata"]["hash"],
                "metadata": [item["metadata"]],
            }
            try:
                # Tenta buscar o objeto pelo id
                obj = coll.query.fetch_object_by_id(
                    item["id"], include_vector=True)
                if obj:
                    coll.data.update(data)
                else:
                    coll.data.insert(data)
            except Exception:
                coll.data.insert(data)

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """
        Consulta os objetos da collection utilizando um filtro (no formato Weaviate)
        e retorna os resultados encapsulados em GetResult.
        """
        collection_name = self.transform_collection_name(collection_name)
        collection = self.client.collections.get(collection_name)

        filter_condition = build_filter(filter)

        try:
            if collection:

                results = collection.query.fetch_objects(
                    filters=filter_condition, limit=limit  # Número máximo de resultados
                )
                items = [
                    r for r in results.objects
                ]  # Supõe que a resposta contenha a lista de objetos em 'objects'
                log.info(items)
                if items:
                    ids = [obj.properties.get("file_id", "") for obj in items]
                    docs = [obj.properties.get("documents", "")
                            for obj in items]
                    meta = [obj.properties.get("metadata", {})
                            for obj in items]
                    return GetResult(ids=[ids], documents=[docs], metadatas=[meta])
        except:
            pass
        return None

    def get(
        self, collection_name: str, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """
        Retorna todos os objetos da collection (limitado a 1000 itens).
        """
        collection_name = self.transform_collection_name(collection_name)
        collection = self.client.collections.get(collection_name)
        response = collection.query.fetch_objects(limit=limit)
        items = response.objects
        if items:
            ids = [obj.properties.get("file_id", "") for obj in items]
            docs = [obj.properties.get("documents", "") for obj in items]
            meta = [obj.properties.get("metadata", {}) for obj in items]
            return GetResult(ids=[ids], documents=[docs], metadatas=[meta])
        return None

    def search(
        self, collection_name: str, query: str, limit: int
    ) -> Optional[SearchResult]:
        """
        Performs a similarity search using the 'near_text' feature.
        Returns results wrapped in SearchResult, including ids, documents,
        metadata, and distances (if available).
        """
        collection_name = self.transform_collection_name(collection_name)
        collection = self.client.collections.get(collection_name)
        all_ids = []
        all_docs = []
        all_meta = []
        all_dists = []

        # Realiza consulta por similaridade usando o vetor

        response = collection.query.near_text(
            query=query, limit=limit, return_metadata=MetadataQuery(
                distance=True)
        )

        # response = collection.query.hybrid(
        #     query=query,
        #     alpha=0.75,
        #     max_vector_distance=0.4,
        #     return_metadata=MetadataQuery(score=True, explain_score=True),
        #     limit=limit,
        # )

        ids = []
        distances = []
        documents = []
        metadatas = []

        if not response:
            return SearchResult(
                ids=ids,
                distances=distances,
                documents=documents,
                metadatas=metadatas,
            )

        items = response.objects
        ids = [obj.properties.get("file_id", "") for obj in items]
        docs = [obj.properties.get("documents", "") for obj in items]
        meta = [obj.properties.get("metadata", {}) for obj in items]
        # Supõe que a distância esteja disponível em _additional.distance
        dists = [obj.metadata.distance for obj in items]
        all_ids.append(ids)
        all_docs.append(docs)
        all_meta.append(meta)
        all_dists.append(dists)
        if all_ids:
            return SearchResult(
                ids=all_ids, documents=all_docs, metadatas=all_meta, distances=all_dists
            )
        return None

    def hybrid_search(
        self, collection_name: str, query: str, limit: int
    ) -> Optional[SearchResult]:
        """
        Performs a hybrid search using both keyword and vector search.
        Returns results wrapped in SearchResult, including ids, documents,
        metadata, and relevance scores.
        """
        collection_name = self.transform_collection_name(collection_name)
        collection = self.client.collections.get(collection_name)
        all_ids = []
        all_docs = []
        all_meta = []
        all_dists = []

        # Performs similarity query using vector

        response = collection.query.hybrid(
            query=query,
            alpha=0.5,
            return_metadata=MetadataQuery(score=True, explain_score=True),
            limit=limit,
        )

        ids = []
        distances = []
        documents = []
        metadatas = []

        if not response:
            return SearchResult(
                ids=ids,
                distances=distances,
                documents=documents,
                metadatas=metadatas,
            )

        items = response.objects
        ids = [obj.properties.get("file_id", "") for obj in items]
        docs = [obj.properties.get("documents", "") for obj in items]
        meta = [obj.properties.get("metadata", {}) for obj in items]
        # Assumes distance is available in metadata.score
        dists = [obj.metadata.score for obj in items]
        all_ids.append(ids)
        all_docs.append(docs)
        all_meta.append(meta)
        all_dists.append(dists)
        if all_ids:
            return SearchResult(
                ids=all_ids, documents=all_docs, metadatas=all_meta, distances=all_dists
            )
        return None

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[dict] = None,
    ):
        """
        Removes objects from the collection based on a list of ids or using a filter.
        If a filter is provided, performs the query to obtain the corresponding ids and deletes them.
        """
        collection_name = self.transform_collection_name(collection_name)
        collection = self.client.collections.get(collection_name)

        if ids:
            for obj_id in ids:
                collection.data.delete(uuid=obj_id)
        elif filter:
            for idx, f_ in filter.items():
                log.info(f"Filer: {f_}")
                collection.data.delete_many(
                    where=Filter.by_property(idx).contains_any([f_])
                )

    def reset(self):
        """
        Removes all collections from Weaviate.
        CAUTION: This operation deletes ALL data.
        """
        collections = self.client.collections.list_all()
        for coll in collections:
            self.client.collections.delete(coll)

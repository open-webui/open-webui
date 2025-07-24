import logging
import requests
import re

from typing import Optional, List, Union

from open_webui.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    WEAVIATE_HTTP_HOST,
    WEAVIATE_HTTP_PORT,
    WEAVIATE_API_KEY,
)

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

WEAVIATE_URL = f"http://{WEAVIATE_HTTP_HOST}:{WEAVIATE_HTTP_PORT}"

def get_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WEAVIATE_API_KEY}"
    }

def build_graphql_filter(filter_dict, operator="Equal"):
    """
    Constrói a cláusula 'where' em sintaxe GraphQL para o seu schema,
    aceitando campos aninhados via tuplas/listas no filter_dict:
        exemplo: {("metadata", "name"): "Exemplo", "hash": "abc"}
    """
    def get_value_key(value):
        if isinstance(value, bool):
            return "valueBoolean"
        elif isinstance(value, int):
            return "valueInt"
        elif isinstance(value, float):
            return "valueNumber"
        elif isinstance(value, str):
            return "valueString"
        else:
            raise ValueError(f"Tipo de valor '{type(value)}' não suportado.")
    def format_path(key):
        if isinstance(key, (tuple, list)):
            return "[" + ",".join(f'"{k}"' for k in key) + "]"
        else:
            return f'["{key}"]'
    conditions = []
    for key, value in filter_dict.items():
        gk = get_value_key(value)
        vstr = f'"{value}"' if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else value
        path_str = format_path(key)
        condition = f'{{path: {path_str}, operator: {operator}, {gk}: {vstr}}}'
        conditions.append(condition)
    if len(conditions) == 1:
        return conditions[0]
    return f'{{operator: And, operands: [{", ".join(conditions)}]}}'


class WeaviateClient:
    def __init__(self):
        self.base_url = WEAVIATE_URL
        self.headers = get_headers()

    def transform_collection_name(self, collection_name: str) -> str:
        """
        Transforms the collection name to a valid Weaviate class name.
        Weaviate class names must start with a letter and can only contain letters, numbers, and underscores.
        """
        collection_name = collection_name.replace("-", "").lower()
        if not (collection_name.startswith("file") or collection_name.startswith("collection")):
            collection_name = f"collection{collection_name}"
        return collection_name.capitalize()

    def has_collection(self, collection_name: str) -> bool:
        url = f"{self.base_url}/v1/schema"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            classes = [c['class'] for c in resp.json().get("classes",[])]
            return self.transform_collection_name(collection_name) in classes
        return False

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
        class_name = self.transform_collection_name(collection_name)
        schema = {
            "class": class_name,
            "vectorizer": "text2vec-aws",  # nome do plugin/integração, ex: text2vec-aws
            "moduleConfig": {
                "text2vec-aws": {
                    "name": "text",
                    "region": "us-east-1",
                    "model": "amazon.titan-embed-text-v2:0",
                    "vectorIndexType": "hnsw",
                    "sourceProperties": ["text"]
                }
            },
            "properties": [
                    {"name": "file_id", "dataType": ["text"]},
                    {"name": "documents", "dataType": ["text"]},
                    {"name": "hash", "dataType": ["text"]},
                    {"name": "name", "dataType": ["text"]},
                    {
                        "name": "metadata",
                        "dataType": ["object"],
                        "nestedProperties": [
                            {"name": "content_type", "dataType": ["text"]},
                            {"name": "size", "dataType": ["int"]},
                            {"name": "collection_name", "dataType": ["text"]},
                            {"name": "created_by", "dataType": ["text"]},
                            {"name": "source", "dataType": ["text"]},
                            {"name": "start_index", "dataType": ["int"]},
                            {"name": "embedding_config", "dataType": ["text"]},
                        ]
                    }
            ]
        }

        url = f"{self.base_url}/v1/schema"
        resp = requests.post(url, headers=self.headers, json=schema)
        log.info(f"Create collection {class_name}")
        if not resp.ok:
            raise Exception(f"Error creating collection: {resp.text}")

    def delete_collection(self, collection_name: str):
        """
        Exclui uma collection (class) inteira do Weaviate via REST.
        """
        class_name = self.transform_collection_name(collection_name)
        url = f"{self.base_url}/v1/schema/{class_name}"
        resp = requests.delete(url, headers=self.headers)
        if resp.ok:
            log.info(f"Deleted collection (class) {class_name}")
        else:
            log.error(f"Failed to delete collection {class_name}: {resp.status_code} {resp.text}")

    def insert(self, collection_name: str, items: List[VectorItem]):
        class_name = self.transform_collection_name(collection_name)
        self._ensure_collection(class_name)
        log.info(f"Inserting items into collection: {class_name}")
        url = f"{self.base_url}/v1/objects"
        for item in items:
            # Remover a chave hash
            hash = item["metadata"].get("hash")
            name = item["metadata"].get("name")
            item["metadata"].pop("hash", None)
            item["metadata"].pop("name", None)
            data = {
                "class": class_name,
                "properties": {
                    "file_id": item["id"],
                    "documents": item["text"],
                    "hash": hash,
                    "name": name,
                    "metadata": item["metadata"],
                }
            }
            resp = requests.post(url, headers=self.headers, json=data)
            if resp.status_code not in [200, 201]:
                log.error(f"Failed to insert: {resp.text}")

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
        self, collection_name: str, filter: dict, limit: Optional[int] = 1
    ) -> Optional[GetResult]:
        collection_name = self.transform_collection_name(collection_name)
        where_clause = build_graphql_filter(filter)
        
        query = """
        {
            Get {
                %s (limit: %d
                  where: %s) {
                  file_id
                  documents
                  metadata {
                    collection_name
                  }
                }
            }
        }
        """ % (collection_name, limit, where_clause)
        url = f"{self.base_url}/v1/graphql"
        try:
            resp = requests.post(url, headers=self.headers, json={"query": query})
            resp.raise_for_status()
            items = resp.json().get("data", {}).get("Get", {}).get(collection_name, [])
            log.info(items)
            if items:
                ids = [obj.get("file_id", "") for obj in items]
                docs = [obj.get("documents", "") for obj in items]
                meta = [obj.get("metadata", {}) for obj in items]
                return GetResult(ids=[ids], documents=[docs], metadatas=[meta])
        except Exception as e:
            log.error(f"Erro na query: {e}")
        return None

    def get(
        self, collection_name: str, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """
        Retorna todos os objetos da collection (limitado a 1000 itens).
        """
        class_name = self.transform_collection_name(collection_name)
        url = f"{self.base_url}/v1/graphql"
        query = ("""
            {
            Get {
                %s {
                documents
                file_id
                hash
                name
                }
            }
            }
            """, class_name)
        
        body = {"query": query}
        
        try:
            resp = requests.post(url, headers=self.headers, json=body)
            items = resp.json().get("data", {}).get("Get", {}).get(class_name, [])
            log.info(items)
            if items:
                ids = [obj.get("file_id", "") for obj in items]
                docs = [obj.get("documents", "") for obj in items]
                meta = [obj.get("metadata", {}) for obj in items]
                return GetResult(ids=ids, documents=docs, metadatas=meta)
        except Exception as e:
            log.error(f"Erro na query: {e}")
        return None

    def search(self, collection_name: str, query: str, limit: int = 10) -> Optional[list]:
        """
        Busca por similaridade vetorial usando nearText via GraphQL.
        """
        class_name = self.transform_collection_name(collection_name)
        graphql_query = f"""
            {{
                Get {{
                    {class_name} (
                    nearText: {{
                        concepts: ["{query}"]
                    }}
                    limit: {limit}
                    ) {{
                    file_id
                    documents
                    name
                    metadata {{
                        collection_name
                    }}
                    _additional {{
                        id
                        distance
                        vector
                    }}
                    }}
                }}
            }}
        """
        url = f"{self.base_url}/v1/graphql"
        resp = requests.post(url, headers=self.headers, json={"query": graphql_query})
        
        
        if resp.ok:
            items = resp.json().get("data", {}).get("Get", {}).get(class_name, [])
            ids = [obj.get("file_id", "") for obj in items]
            docs = [obj.get("documents", "") for obj in items]
            meta = [obj.get("metadata", {}) for obj in items]
            distance = [obj.get('_additional', {}).get("distance", "") for obj in items]
            return SearchResult(
                ids=[ids], documents=[docs], metadatas=[meta], distances=[distance]
            )
           
        else:
            log.error(f"Error in search: {resp.status_code} {resp.text}")
            return None
        
    def hybrid_search(self, collection_name: str, query: str, limit: int = 10, alpha: float = 0.5) -> Optional[list]:
        """
        Busca híbrida texto/vetor via GraphQL (campo 'hybrid').
        """
        class_name = self.transform_collection_name(collection_name)
        graphql_query = f"""
        {{
        Get {{
            {class_name}(
            hybrid: {{
                query: "{query}"
                alpha: {alpha}
            }}
            limit: {limit}
            ) {{
            file_id
            documents
            name
            metadata {{
                collection_name
            }}
            _additional {{
                id
                score
                vector
            }}
            }}
        }}
        }}
        """
        url = f"{self.base_url}/v1/graphql"
        resp = requests.post(url, headers=self.headers, json={"query": graphql_query})
        if resp.ok:
            items = resp.json().get("data", {}).get("Get", {}).get(class_name, [])
            ids = [obj.get("file_id", "") for obj in items]
            docs = [obj.get("documents", "") for obj in items]
            meta = [obj.get("metadata", {}) for obj in items]
            score = [obj.get('_additional', {}).get("score", "") for obj in items]
            return SearchResult(
                ids=[ids], documents=[docs], metadatas=[meta], distances=[score]
            )
        else:
            log.error(f"Error in hybrid_search: {resp.status_code} {resp.text}")
            return None

    
    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[dict] = None,
) -> None:
        """
        Remove objetos de uma collection por lista de IDs ou por filtro (GraphQL).
        - Se ids: deleta objetos diretamente pelos UUIDs informados.
        - Se filtro: procura objetos que satisfaçam o filtro e deleta todos encontrados.
        """
        class_name = self.transform_collection_name(collection_name)
        if ids:
            for obj_id in ids:
                url = f"{self.base_url}/v1/objects/{class_name}/{obj_id}"
                resp = requests.delete(url, headers=self.headers)
                if resp.ok:
                    log.info(f"Deleted object {obj_id}")
                else:
                    log.error(f"Failed to delete {obj_id}: {resp.status_code} {resp.text}")
        elif filter:
            # Busca os objetos pelo filtro (usando GraphQL para coletar IDs)
            where_clause = build_graphql_filter(filter)
            graphql_query = f"""
            {{
            Get {{
                {class_name}(
                where: {where_clause}
                limit: 1000
                ) {{
                _additional {{ id }}
                }}
            }}
            }}
            """
            url = f"{self.base_url}/v1/graphql"
            resp = requests.post(url, headers=self.headers, json={"query": graphql_query})
            if resp.ok:
                obj_list = resp.json().get("data", {}).get("Get", {}).get(class_name, [])
                ids_to_delete = [obj["_additional"]["id"] for obj in obj_list]
                if ids_to_delete:
                    self.delete(class_name, ids=ids_to_delete)
            else:
                log.error(f"Error querying for delete: {resp.status_code} {resp.text}")

    def reset(self):
        # Remove todas as classes
        url = f"{self.base_url}/v1/schema"
        schema = requests.get(url, headers=self.headers).json()
        for cl in schema.get("classes", []):
            cname = cl["class"]
            del_url = f"{self.base_url}/v1/schema/{cname}"
            resp = requests.delete(del_url, headers=self.headers)
            if resp.ok:
                log.info(f"Deleted {cname}")
            else:
                log.error(f"Could not delete {cname}: {resp.text}")

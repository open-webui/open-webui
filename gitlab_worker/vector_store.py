import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .config import (
    VECTOR_DB_PROVIDER,
    VECTOR_DB_URL,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_PREFIX,
    QDRANT_ON_DISK,
)

log = logging.getLogger(__name__)


class ChromaStore:
    def __init__(self, url: str):
        import chromadb
        from chromadb import Settings

        self.url = url
        if url.startswith('http'):
            host = url.split('://')[1].split(':')[0]
            port = int(url.split(':')[-1].split('/')[0]) if ':' in url.split('://')[1] else 8000
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
        else:
            self.client = chromadb.PersistentClient(
                path=url,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

    def has_collection(self, collection_name: str) -> bool:
        try:
            return collection_name in self.client.list_collections()
        except Exception as e:
            log.error(f'Error checking collection {collection_name}: {e}')
            return False

    def create_collection(self, collection_name: str) -> None:
        try:
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={'hnsw:space': 'cosine'},
            )
            log.info(f'Created collection: {collection_name}')
        except Exception as e:
            log.error(f'Error creating collection {collection_name}: {e}')

    def delete_collection(self, collection_name: str) -> None:
        try:
            if self.has_collection(collection_name):
                self.client.delete_collection(name=collection_name)
                log.info(f'Deleted collection: {collection_name}')
        except Exception as e:
            log.error(f'Error deleting collection {collection_name}: {e}')

    def insert(self, collection_name: str, items: List[Dict[str, Any]]) -> None:
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={'hnsw:space': 'cosine'},
            )
            ids = [item.get('id', f'item_{i}') for i, item in enumerate(items)]
            embeddings = [item.get('vector', item.get('embedding', [])) for item in items]
            documents = [item.get('text', '') for item in items]
            metadatas = [item.get('metadata', {}) for item in items]
            collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
            log.info(f'Inserted {len(items)} items into collection {collection_name}')
        except Exception as e:
            log.error(f'Error inserting into collection {collection_name}: {e}')


class QdrantStore:
    def __init__(self, url: str, api_key: str = '', prefix: str = 'gitlab'):
        from qdrant_client import QdrantClient as Qclient
        from qdrant_client.http.models import PointStruct

        self.PointStruct = PointStruct
        self.prefix = prefix

        parsed = urlparse(url)
        host = parsed.hostname or url
        port = parsed.port or 6333

        self.client = Qclient(
            url=url,
            api_key=api_key or None,
            timeout=120,
        )
        log.info(f'Connected to Qdrant at {url}')

    def _collection_name(self, name: str) -> str:
        return f'{self.prefix}_{name}'

    def has_collection(self, collection_name: str) -> bool:
        try:
            return self.client.collection_exists(self._collection_name(collection_name))
        except Exception as e:
            log.error(f'Error checking Qdrant collection {collection_name}: {e}')
            return False

    def create_collection(self, collection_name: str, vector_size: int = 768) -> None:
        from qdrant_client.http.models import VectorParams, Distance, HnswConfigDiff

        full_name = self._collection_name(collection_name)
        try:
            if not self.client.collection_exists(full_name):
                self.client.create_collection(
                    collection_name=full_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                        on_disk=QDRANT_ON_DISK,
                    ),
                    hnsw_config=HnswConfigDiff(m=16),
                )
                log.info(f'Created Qdrant collection: {full_name} (dim={vector_size})')
        except Exception as e:
            log.error(f'Error creating Qdrant collection {full_name}: {e}')

    def delete_collection(self, collection_name: str) -> None:
        try:
            full_name = self._collection_name(collection_name)
            if self.client.collection_exists(full_name):
                self.client.delete_collection(full_name)
                log.info(f'Deleted Qdrant collection: {full_name}')
        except Exception as e:
            log.error(f'Error deleting Qdrant collection {collection_name}: {e}')

    def insert(self, collection_name: str, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        full_name = self._collection_name(collection_name)
        try:
            vector_size = len(items[0].get('vector', items[0].get('embedding', [])))
            if not self.client.collection_exists(full_name):
                self.create_collection(collection_name, vector_size)

            points = [
                self.PointStruct(
                    id=item.get('id', f'item_{i}'),
                    vector=item.get('vector', item.get('embedding', [])),
                    payload={
                        'text': item.get('text', ''),
                        'metadata': item.get('metadata', {}),
                    },
                )
                for i, item in enumerate(items)
            ]
            self.client.upsert(full_name, points)
            log.info(f'Inserted {len(items)} points into Qdrant collection {full_name}')
        except Exception as e:
            log.error(f'Error inserting into Qdrant collection {full_name}: {e}')


class VectorStore:
    def __init__(self):
        self.provider = VECTOR_DB_PROVIDER
        self._store = self._create_store()

    def _create_store(self):
        if self.provider == 'chroma':
            log.info(f'Using Chroma vector store at {VECTOR_DB_URL}')
            return ChromaStore(url=VECTOR_DB_URL)
        elif self.provider == 'qdrant':
            log.info(f'Using Qdrant vector store at {QDRANT_URL}')
            return QdrantStore(url=QDRANT_URL, api_key=QDRANT_API_KEY, prefix=QDRANT_COLLECTION_PREFIX)
        else:
            raise ValueError(f'Unsupported vector DB provider: {self.provider}')

    def has_collection(self, collection_name: str) -> bool:
        return self._store.has_collection(collection_name)

    def create_collection(self, collection_name: str, vector_size: int = 768) -> None:
        if self.provider == 'qdrant':
            self._store.create_collection(collection_name, vector_size)
        else:
            self._store.create_collection(collection_name)

    def delete_collection(self, collection_name: str) -> None:
        self._store.delete_collection(collection_name)

    def insert(self, collection_name: str, items: List[Dict[str, Any]]) -> None:
        self._store.insert(collection_name, items)


vector_store = VectorStore()

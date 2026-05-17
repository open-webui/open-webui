import logging
from typing import List, Dict, Any

from qdrant_client import QdrantClient as Qclient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, HnswConfigDiff

from .config import QDRANT_URL, QDRANT_API_KEY, QDRANT_ON_DISK

log = logging.getLogger(__name__)


class QdrantStore:
    """Qdrant-only vector store. No local disk, no Chroma fallback.

    Collections are named directly (e.g. ``gitlab_owner_repo``) without any
    prefix so they match the names used by the main Open WebUI backend.
    """

    def __init__(self, url: str, api_key: str = ''):
        self.client = Qclient(
            url=url,
            api_key=api_key or None,
            timeout=120,
        )
        log.info(f'Connected to Qdrant at {url}')

    # --- Collection lifecycle ------------------------------------------------

    def has_collection(self, collection_name: str) -> bool:
        try:
            return self.client.collection_exists(collection_name)
        except Exception as e:
            log.error(f'Error checking collection {collection_name}: {e}')
            return False

    def create_collection(self, collection_name: str, vector_size: int = 768) -> None:
        try:
            if not self.client.collection_exists(collection_name):
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                        on_disk=QDRANT_ON_DISK,
                    ),
                    hnsw_config=HnswConfigDiff(m=16),
                )
                log.info(f'Created Qdrant collection: {collection_name} (dim={vector_size})')
        except Exception as e:
            log.error(f'Error creating Qdrant collection {collection_name}: {e}')

    def delete_collection(self, collection_name: str) -> None:
        try:
            if self.client.collection_exists(collection_name):
                self.client.delete_collection(collection_name)
                log.info(f'Deleted Qdrant collection: {collection_name}')
        except Exception as e:
            log.error(f'Error deleting Qdrant collection {collection_name}: {e}')

    # --- Write ---------------------------------------------------------------

    def insert(self, collection_name: str, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        try:
            vector_size = len(items[0].get('vector', items[0].get('embedding', [])))
            if not self.client.collection_exists(collection_name):
                self.create_collection(collection_name, vector_size)

            points = [
                PointStruct(
                    id=item.get('id', f'item_{i}'),
                    vector=item.get('vector', item.get('embedding', [])),
                    payload={
                        'text': item.get('text', ''),
                        'metadata': item.get('metadata', {}),
                    },
                )
                for i, item in enumerate(items)
            ]
            self.client.upsert(collection_name, points)
            log.info(f'Inserted {len(items)} points into Qdrant collection {collection_name}')
        except Exception as e:
            log.error(f'Error inserting into Qdrant collection {collection_name}: {e}')

    # --- Read ----------------------------------------------------------------

    def search(self, collection_name: str, vector: list[float], limit: int = 10):
        try:
            if not self.client.collection_exists(collection_name):
                return []
            result = self.client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit,
            )
            return result
        except Exception as e:
            log.error(f'Error searching collection {collection_name}: {e}')
            return []

    def count(self, collection_name: str) -> int:
        try:
            if not self.client.collection_exists(collection_name):
                return 0
            return self.client.count(collection_name).count
        except Exception:
            return 0


# Singleton
vector_store = QdrantStore(url=QDRANT_URL, api_key=QDRANT_API_KEY)

import logging
from typing import List, Union

import httpx

from .config import OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL

log = logging.getLogger(__name__)


class OllamaEmbedder:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_EMBEDDING_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.embedding_dim = 768

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=120.0) as client:
            embeddings = []
            for idx, text in enumerate(texts):
                try:
                    response = await client.post(
                        f'{self.base_url}/api/embeddings',
                        json={'model': self.model, 'prompt': text[:2048]},  # Truncate long texts
                    )
                    response.raise_for_status()
                    data = response.json()
                    embedding = data.get('embedding', [])
                    embeddings.append(embedding)
                    log.debug(f'Embedded text {idx+1}/{len(texts)}, length: {len(text)}, embedding dim: {len(embedding)}')
                except Exception as e:
                    log.error(f'Failed to embed text {idx+1}/{len(texts)}: {e}')
                    # Use zero embedding as fallback
                    embeddings.append([0.0] * self.embedding_dim)

            log.info(f'Generated embeddings for {len(texts)} texts using model {self.model}')
            return embeddings

    async def embed_single(self, text: str) -> List[float]:
        result = await self.embed([text])
        return result[0] if result else []

    async def get_embedding_dim(self) -> int:
        return self.embedding_dim


embedder = OllamaEmbedder()
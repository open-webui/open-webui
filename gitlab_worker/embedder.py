import logging
import asyncio
from typing import List, Union

import httpx

from .config import OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL

log = logging.getLogger(__name__)


class OllamaEmbedder:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_EMBEDDING_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.embedding_dim = 768
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests to Ollama

    async def _embed_text(self, client: httpx.AsyncClient, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.embedding_dim

        async with self.semaphore:
            try:
                # Ollama api/embeddings supports a single prompt
                response = await client.post(
                    f'{self.base_url}/api/embeddings',
                    json={'model': self.model, 'prompt': text[:4096]},  # Increased limit slightly
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get('embedding', [])
                
                if not embedding:
                    log.warning("Received empty embedding from Ollama")
                    return [0.0] * self.embedding_dim
                
                # Update dim if we found a different one
                if len(embedding) != self.embedding_dim:
                    self.embedding_dim = len(embedding)
                
                return embedding
            except Exception as e:
                log.error(f'Failed to embed text: {e}')
                return [0.0] * self.embedding_dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=120.0) as client:
            tasks = [self._embed_text(client, text) for text in texts]
            embeddings = await asyncio.gather(*tasks)
            
            log.info(f'Generated embeddings for {len(texts)} texts using model {self.model}')
            return list(embeddings)

    async def embed_single(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            return await self._embed_text(client, text)

    async def get_embedding_dim(self) -> int:
        return self.embedding_dim


embedder = OllamaEmbedder()
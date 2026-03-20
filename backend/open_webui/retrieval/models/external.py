import logging
import requests
import threading
from typing import Optional, List, Tuple
from urllib.parse import quote


from open_webui.env import ENABLE_FORWARD_USER_INFO_HEADERS, REQUESTS_VERIFY
from open_webui.retrieval.models.base_reranker import BaseReranker
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


class ExternalReranker(BaseReranker):
    # Supported API formats for external reranker endpoints
    FORMAT_COHERE = 'cohere'  # Cohere/Jina: {"documents": [...], "model": ..., "top_n": N}
    FORMAT_TEI = 'tei'  # TEI: {"texts": [...], "truncate": true}

    # Class-level cache: survives re-instantiation (e.g. config updates).
    # Keyed by URL so different endpoints can use different formats.
    _format_cache: dict = {}
    _format_lock = threading.Lock()

    def __init__(
        self,
        api_key: str,
        url: str = 'http://localhost:8080/v1/rerank',
        model: str = 'reranker',
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key
        self.url = url
        self.model = model
        self.timeout = timeout

    def _build_payload(self, query: str, docs: list, api_format: str) -> dict:
        if api_format == self.FORMAT_TEI:
            return {
                'query': query,
                'texts': docs,
                'truncate': True,
            }
        return {
            'model': self.model,
            'query': query,
            'documents': docs,
            'top_n': len(docs),
        }

    def predict(self, sentences: List[Tuple[str, str]], user=None) -> Optional[List[float]]:
        query = sentences[0][0]
        docs = [i[1] for i in sentences]

        try:
            log.info(f'ExternalReranker:predict:model {self.model}')
            log.info(f'ExternalReranker:predict:query {query}')

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            # Detect API format on first call (thread-safe).
            # The first thread to arrive does the detection; others wait and reuse.
            if self.url not in self._format_cache:
                with self._format_lock:
                    if self.url not in self._format_cache:
                        self._format_cache[self.url] = self._detect_format(headers, query, docs)

            payload = self._build_payload(query, docs, self._format_cache[self.url])

            r = requests.post(
                f'{self.url}',
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=REQUESTS_VERIFY,
            )

            r.raise_for_status()
            data = r.json()

            return self._parse_response(data)

        except Exception as e:
            log.exception(f'Error in external reranking: {e}')
            return None

    def _detect_format(self, headers: dict, query: str, docs: list) -> str:
        """Detect the API format by trying Cohere first, falling back to TEI.

        Sends a single probe request with Cohere format. If the endpoint
        returns 422 (validation error), it likely expects TEI format instead.
        """
        payload = self._build_payload(query, docs, self.FORMAT_COHERE)
        try:
            r = requests.post(
                f'{self.url}',
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=REQUESTS_VERIFY,
            )
        except Exception:
            # Network error — default to Cohere, let predict() handle the error
            return self.FORMAT_COHERE

        if r.status_code == 422:
            log.info(f'ExternalReranker: Cohere format rejected, using TEI format')
            return self.FORMAT_TEI

        log.info(f'ExternalReranker: detected API format: {self.FORMAT_COHERE}')
        return self.FORMAT_COHERE

    @staticmethod
    def _parse_response(data) -> Optional[List[float]]:
        """Parse reranking response in either Cohere/Jina or TEI format.

        Cohere/Jina: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
        TEI:         [{"index": 0, "score": 0.9}, ...]
        """
        results = None

        if isinstance(data, list):
            # TEI format: flat array
            results = data
        elif isinstance(data, dict) and 'results' in data:
            # Cohere/Jina format: wrapped in {"results": [...]}
            results = data['results']

        if not results:
            log.error('No results found in external reranking response')
            return None

        sorted_results = sorted(results, key=lambda x: x['index'])

        # Support both "relevance_score" (Cohere/Jina) and "score" (TEI)
        return [
            result.get('relevance_score', result.get('score', 0.0))
            for result in sorted_results
        ]

import asyncio
import logging
from typing import List, Optional, Tuple
from urllib.parse import quote

import requests
from open_webui.env import (
    ENABLE_FORWARD_USER_INFO_HEADERS,
    RAG_EXTERNAL_RERANKER_API_AUTH_TYPE,
    REQUESTS_VERIFY,
)
from open_webui.retrieval.models.base_reranker import BaseReranker
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


class ExternalReranker(BaseReranker):
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

    def predict(self, sentences: List[Tuple[str, str]], user=None) -> Optional[List[float]]:
        query = sentences[0][0]
        docs = [i[1] for i in sentences]

        payload = {
            'model': self.model,
            'query': query,
            'documents': docs,
            'top_n': len(docs),
        }

        try:
            log.info(f'ExternalReranker:predict:model {self.model}')
            log.info(f'ExternalReranker:predict:query {query}')

            api_key = self.api_key
            if RAG_EXTERNAL_RERANKER_API_AUTH_TYPE == 'system_oauth' and user is not None:
                # Mirrors the embedding connection's system_oauth auth type.
                # predict() runs in a worker thread (asyncio.to_thread), so a
                # private event loop is safe for the async token lookup.
                # Lazy import: retrieval.utils would be a circular import here.
                from open_webui.retrieval.utils import get_system_oauth_access_token

                access_token = None
                try:
                    access_token = asyncio.run(get_system_oauth_access_token(user))
                except Exception as e:
                    log.error(f'Error resolving system OAuth token for reranking: {e}')

                if access_token:
                    api_key = access_token
                else:
                    log.warning(
                        'RAG_EXTERNAL_RERANKER_API_AUTH_TYPE=system_oauth but no OAuth '
                        f'token available for user {user.id}; falling back to the '
                        'static RAG_EXTERNAL_RERANKER_API_KEY'
                    )

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            r = requests.post(
                f'{self.url}',
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=REQUESTS_VERIFY,
            )

            r.raise_for_status()
            data = r.json()

            if 'results' in data:
                sorted_results = sorted(data['results'], key=lambda x: x['index'])
                return [result['relevance_score'] for result in sorted_results]
            else:
                log.error('No results found in external reranking response')
                return None

        except Exception as e:
            log.exception(f'Error in external reranking: {e}')
            return None

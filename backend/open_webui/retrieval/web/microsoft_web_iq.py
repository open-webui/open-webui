from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)

DEFAULT_MICROSOFT_WEB_IQ_API_BASE_URL = 'https://api.microsoft.ai/v3'


def search_microsoft_web_iq(
    api_base_url: str,
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
    language: str = 'en',
    user=None,
) -> list[SearchResult]:
    try:
        api_base_url = (api_base_url or DEFAULT_MICROSOFT_WEB_IQ_API_BASE_URL).rstrip('/')
        headers = {
            'host': urlparse(api_base_url).netloc or 'api.microsoft.ai',
            'x-apikey': api_key,
            'content-type': 'application/json',
        }
        if user is not None:
            headers = include_user_info_headers(headers, user)

        response = requests.post(
            f'{api_base_url}/search/web',
            json={
                'query': query,
                'maxResults': count,
                'language': language,
                'contentFormat': 'passage',
            },
            headers=headers,
        )
        response.raise_for_status()

        results = response.json().get('webResults', [])
        if filter_list:
            results = get_filtered_results(results, filter_list)

        return [
            SearchResult(
                link=result['url'],
                title=result.get('title'),
                snippet=result.get('content'),
            )
            for result in results
        ]
    except Exception as e:
        log.error(f'Error searching with Microsoft Web IQ API: {e}')
        return []

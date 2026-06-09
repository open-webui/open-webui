from __future__ import annotations

import logging
from typing import Any

import requests

from open_webui.retrieval.web.iflow_client import IFLOW_REQUEST_TIMEOUT, first_str, iflow_post, unwrap_iflow_data
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def _extract_organic_results(body: dict[str, Any]) -> list[dict[str, Any]]:
    data = unwrap_iflow_data(body)
    if isinstance(data, dict):
        organic = data.get('organic')
        if isinstance(organic, list):
            return [item for item in organic if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    organic = body.get('organic')
    if isinstance(organic, list):
        return [item for item in organic if isinstance(item, dict)]
    results = body.get('results')
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    return []


def search_iflow(
    api_key: str,
    base_url: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
) -> list[SearchResult]:
    """Search the web using the iFlow Search API."""
    try:
        body = iflow_post(
            api_key,
            base_url,
            '/api/search/webSearch',
            {'keywords': query, 'num': count},
            timeout=IFLOW_REQUEST_TIMEOUT,
        )
        results = _extract_organic_results(body)
        mapped = [
            {
                'url': first_str(item, 'link', 'url', 'href'),
                'title': first_str(item, 'title'),
                'snippet': first_str(item, 'snippet', 'content', 'description'),
            }
            for item in results
            if first_str(item, 'link', 'url', 'href')
        ]

        if filter_list:
            mapped = get_filtered_results(mapped, filter_list)

        return [
            SearchResult(
                link=item['url'],
                title=item.get('title') or None,
                snippet=item.get('snippet') or None,
            )
            for item in mapped[:count]
        ]
    except requests.exceptions.RequestException as e:
        log.error('iFlow web search request failed: %s', e)
        raise Exception(f'iFlow search failed: {e}') from e
    except Exception as e:
        log.error('Error searching iFlow: %s', e)
        raise Exception(f'iFlow search error: {e}') from e

import logging

import requests
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)

PARALLEL_API_BASE = 'https://api.parallel.ai'
PARALLEL_REQUEST_TIMEOUT = (5, 10)  # (connect, read) seconds


def search_parallel(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str] | None = None,
) -> list[SearchResult]:
    """Search using Parallel Search API and return the results as a list of SearchResult objects.

    API reference: https://docs.parallel.ai/api-reference/search/search

    Args:
        api_key: A Parallel Search API key
        query: The query to search for
        count: Number of results to return; pass 0 to let Parallel decide
        filter_list: Optional list of domains to restrict results to
    """
    log.info(f'Running Parallel search for query: {query}')

    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'open-webui',
    }

    advanced_settings: dict = {}
    if count:
        advanced_settings['max_results'] = count
    if filter_list:
        advanced_settings['source_policy'] = {'include_domains': filter_list}

    payload: dict = {
        'search_queries': [query],
        'mode': 'basic',
    }
    if advanced_settings:
        payload['advanced_settings'] = advanced_settings

    try:
        response = requests.post(
            f'{PARALLEL_API_BASE}/v1/search',
            headers=headers,
            json=payload,
            timeout=PARALLEL_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as e:
        body = getattr(e.response, 'text', '')
        log.error(f'Parallel search HTTP error: {e}; body={body[:500]}')
        return []
    except Exception as e:
        log.error(f'Error searching Parallel: {e}')
        return []

    results = []
    for result in data.get('results', []):
        url = result.get('url')
        if not url:
            continue
        excerpts = result.get('excerpts', [])
        results.append(
            SearchResult(
                link=url,
                title=result.get('title') or url,
                snippet='\n\n'.join(excerpts),
            )
        )

    log.info(f'Found {len(results)} results')
    return results

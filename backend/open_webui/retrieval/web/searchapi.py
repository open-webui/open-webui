import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_searchapi(
    api_key: str,
    engine: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using searchapi.io's API and return the results as a list of SearchResult objects.

    Args:
      api_key (str): A searchapi.io API key
      query (str): The query to search for
    """
    url = 'https://www.searchapi.io/api/v1/search'

    engine = engine or 'google'

    payload = {'engine': engine, 'q': query, 'api_key': api_key}
    if engine.startswith('google'):
        payload['link'] = 'resolved'

    url = f'{url}?{urlencode(payload)}'
    response = requests.request('GET', url, timeout=30)
    response.raise_for_status()

    json_response = response.json()
    log.debug('results from searchapi search: %s', json_response)

    # top_stories entries carry no position, so the merged list keeps API order
    results = [
        *json_response.get('organic_results', []),
        *json_response.get('top_stories', []),
    ]
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result.get('link', ''),
            title=result.get('title'),
            snippet=result.get('snippet'),
        )
        for result in results[:count]
    ]

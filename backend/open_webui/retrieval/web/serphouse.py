import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_serphouse(
    api_key: str,
    engine: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using SERPHouse API and return the results as a list of SearchResult objects.

    Args:
      api_key (str): A SERPHouse API key
      engine (str): Search engine domain (e.g. google.com, bing.com)
      query (str): The query to search for
      count (int): Maximum number of results to return
    """
    url = 'https://api.serphouse.com/serp/live'

    domain = engine or 'google.com'

    params = {
        'q': query,
        'domain': domain,
        'lang': 'en',
        'device': 'desktop',
        'serp_type': 'web',
        'num_result': str(min(count, 10)),
    }

    headers = {'Authorization': f'Bearer {api_key}'}

    url = f'{url}?{urlencode(params)}'
    response = requests.request('GET', url, headers=headers)

    json_response = response.json()
    log.info(f'results from serphouse search: {json_response}')

    organic = (
        json_response.get('results', {})
        .get('results', {})
        .get('organic', [])
    )
    results = sorted(organic, key=lambda x: x.get('position', 0))
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result['link'],
            title=result.get('title'),
            snippet=result.get('snippet'),
        )
        for result in results[:count]
    ]

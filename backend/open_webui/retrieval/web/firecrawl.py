import logging
from typing import Optional, List

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_firecrawl(
    firecrawl_url: str,
    firecrawl_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    try:
        url = firecrawl_url.rstrip('/')
        response = requests.post(
            f'{url}/v1/search',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {firecrawl_api_key}',
            },
            json={
                'query': query,
                'limit': count,
                'timeout': count * 3000,
            },
            timeout=count * 3 + 10,
        )
        response.raise_for_status()
        data = response.json().get('data', {})

        results = [
            SearchResult(
                link=r.get('url', ''),
                title=r.get('title', ''),
                snippet=r.get('description', ''),
            )
            for r in data.get('web', [])
        ]

        if filter_list:
            results = get_filtered_results(results, filter_list)

        results = results[:count]
        log.info(f'FireCrawl search results: {results}')
        return results
    except Exception as e:
        log.error(f'Error in FireCrawl search: {e}')
        return []

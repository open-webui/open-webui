import logging
from dataclasses import dataclass
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)

LINKUP_API_BASE = 'https://api.linkup.so/v1'


@dataclass
class LinkupResult:
    url: str
    name: str
    content: str


def search_linkup(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    depth: str = 'standard',
) -> list[SearchResult]:
    """Search using Linkup Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Linkup API key
        query (str): The query to search for
        count (int): Number of results to return
        filter_list (Optional[list[str]]): List of domains to filter results by
        depth (str): Search depth - 'fast', 'standard', or 'deep'
    """
    log.info(f'Searching with Linkup for query: {query}')

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    payload = {
        'q': query,
        'depth': depth,
        'outputType': 'searchResults',
        'maxResults': count or 5,
    }

    # Separate include/exclude domains based on '!' prefix
    if filter_list:
        include_domains = [d for d in filter_list if not d.startswith('!')]
        exclude_domains = [d.lstrip('!') for d in filter_list if d.startswith('!')]
        if include_domains:
            payload['includeDomains'] = include_domains
        if exclude_domains:
            payload['excludeDomains'] = exclude_domains

    try:
        response = requests.post(f'{LINKUP_API_BASE}/search', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get('results', []):
            results.append(
                LinkupResult(
                    url=result.get('url', ''),
                    name=result.get('name', ''),
                    content=result.get('content', ''),
                )
            )

        log.info(f'Found {len(results)} results')
        return [
            SearchResult(
                link=result.url,
                title=result.name,
                snippet=result.content,
            )
            for result in results
        ]
    except Exception as e:
        log.error(f'Error searching Linkup: {e}')
        return []

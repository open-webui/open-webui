import logging

import requests
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)

EXA_API_BASE = 'https://api.exa.ai'


def search_exa(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str] | None = None,
    max_content_length: int | None = None,
) -> list[SearchResult]:
    """Search using Exa Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Exa Search API key
        query (str): The query to search for
        count (int): Number of results to return
        filter_list (list[str] | None): List of domains to filter results by
        max_content_length (int | None): Maximum characters per result; None leaves text unlimited.
    """
    log.info('Searching with Exa for query: %s', query)

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    payload = {
        'query': query,
        'numResults': count or 5,
        'includeDomains': filter_list,
        'contents': {'text': {'maxCharacters': max_content_length} if max_content_length is not None else True},
        'type': 'auto',  # Use the auto search type (keyword or neural)
    }

    try:
        response = requests.post(f'{EXA_API_BASE}/search', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        results = data['results']
        log.info('Found %s results', len(results))
        return [
            SearchResult(
                link=result['url'],
                title=result['title'],
                snippet=(result.get('text') or '')[:max_content_length],
            )
            for result in results
        ]
    except Exception as e:
        log.error(f'Error searching Exa: {e}')
        return []

import logging
from typing import Optional, Literal

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def search_linkup(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    api_url: str = 'https://api.linkup.so/v1/search',
    depth: Literal['fast', 'standard', 'deep'] = 'standard',
    output_type: Literal['searchResults', 'sourcedAnswer', 'structured'] = 'searchResults',
    user=None,
) -> list[SearchResult]:
    """
    Search using Linkup's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Linkup API key
        query (str): The query to search for
        count (int): The number of results to return
        filter_list (Optional[list[str]]): List of domains to filter
        api_url (str): Linkup API base URL
        depth (str): Search depth (fast, standard, deep)
        output_type (str): Output type (searchResults, sourcedAnswer, structured)
        user: Optional user object for forwarding user info headers

    Returns:
        list[SearchResult]: A list of search results
    """

    # Handle PersistentConfig object
    if hasattr(api_key, '__str__'):
        api_key = str(api_key)

    if hasattr(api_url, '__str__'):
        api_url = str(api_url)

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    # Forward user info headers if user is provided
    if user is not None:
        headers = include_user_info_headers(headers, user)

    # Linkup API expects snake_case parameters
    payload = {
        'q': query,
        'depth': depth,
        'outputType': output_type,
        'maxResults': count,
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        json_response = response.json()

        if output_type == 'sourcedAnswer':
            search_results = json_response.get('sources', [])
        else:
            search_results = json_response.get('results', [])

        if filter_list:
            search_results = get_filtered_results(search_results, filter_list)

        results = [
            SearchResult(
                link=result.get('url', ''),
                title=result.get('name') or result.get('title'),
                snippet=result.get('content') or result.get('text') or result.get('snippet'),
            )
            for result in search_results
        ][:count]

        return results

    except requests.exceptions.RequestException as e:
        log.error(f'Linkup API request failed: {e}')
        raise Exception(f'Linkup search failed: {str(e)}')
    except Exception as e:
        log.error(f'Error searching Linkup: {e}')
        raise Exception(f'Linkup search error: {str(e)}')

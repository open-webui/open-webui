import logging
from typing import Optional

import requests

from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)

DEFAULT_LINKUP_PARAMS = {
    'url': 'https://api.linkup.so/v1/search',
    'depth': 'standard',
    'outputType': 'sourcedAnswer',
}


def search_linkup(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    params: Optional[dict] = None,
) -> list[SearchResult]:
    """Search using the Linkup Search API.

    ``params`` is forwarded almost verbatim as the JSON body; only ``q``
    and ``maxResults`` are injected automatically.  The special key
    ``url`` (default ``https://api.linkup.so/v1/search``) is popped and
    used as the endpoint.
    """
    if hasattr(api_key, '__str__'):
        api_key = str(api_key)

    merged = {**DEFAULT_LINKUP_PARAMS, **(params or {})}
    api_url = str(merged.pop('url', DEFAULT_LINKUP_PARAMS['url']))

    payload = {**merged, 'q': query, 'maxResults': count}

    try:
        response = requests.post(
            api_url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        json_response = response.json()

        output_type = merged.get('outputType', 'sourcedAnswer')
        search_results = (
            json_response.get('sources', [])
            if output_type == 'sourcedAnswer'
            else json_response.get('results', [])
        )

        if filter_list:
            search_results = get_filtered_results(search_results, filter_list)

        return [
            SearchResult(
                link=r.get('url', ''),
                title=r.get('name') or r.get('title'),
                snippet=r.get('content') or r.get('text') or r.get('snippet'),
            )
            for r in search_results
        ][:count]

    except requests.exceptions.RequestException as e:
        log.error(f'Linkup API request failed: {e}')
        raise Exception(f'Linkup search failed: {str(e)}')
    except Exception as e:
        log.error(f'Error searching Linkup: {e}')
        raise Exception(f'Linkup search error: {str(e)}')

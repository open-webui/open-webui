from __future__ import annotations

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results


def search_staan(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str] | None = None,
    market: str | None = None,
    max_snippets: int | None = None,
) -> list[SearchResult]:
    """Search using Staan's Web Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Staan API key
        query (str): The query to search for
        count (int): The maximum number of results to return
        filter_list (list[str] | None): The domains to allow or block
        market (str | None): The market to search in, e.g. 'en-us'
        max_snippets (int | None): The maximum extra snippets to request per result

    Returns:
        A list of SearchResult objects.
    """
    url = 'https://api.staan.ai/v2/search/web'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    params = {'q': query, 'market': market}

    if max_snippets:
        params['extra_snippets'] = 'true'
        params['max_snippets'] = max_snippets

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    results = response.json().get('web', {}).get('results', [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result.get('url', ''),
            title=result.get('title'),
            snippet=_build_snippet(result),
        )
        for result in results[:count]
    ]


def _build_snippet(result: dict) -> str:
    """Combine the snippet and the extra snippets list into a single string."""
    parts = [result.get('snippet')]
    parts.extend(extra.get('chunk') for extra in result.get('extra_snippets', []))
    return '\n\n'.join(part for part in parts if part)

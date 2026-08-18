from __future__ import annotations

import logging

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)

OLOSTEP_SEARCH_URL = "https://api.olostep.com/v1/searches"


def search_olostep(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str] | None = None,
) -> list[SearchResult]:
    """Search using Olostep's Search API and return the results as a list of
    SearchResult objects.

    Args:
        api_key (str): An Olostep API key
        query (str): The query to search for
        count (int): The maximum number of results to return
        filter_list (list[str] | None): Optional domain filter list

    Returns:
        A list of SearchResult objects.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    data = {"query": query, "limit": count}

    response = requests.post(
        OLOSTEP_SEARCH_URL,
        headers=headers,
        json=data,
        timeout=count * 3 + 10,
    )
    response.raise_for_status()

    json_response = response.json()

    results = (json_response.get("result") or {}).get("links") or []
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"],
            title=result.get("title", ""),
            snippet=result.get("description"),
        )
        for result in results[:count]
        if result.get("url")
    ]

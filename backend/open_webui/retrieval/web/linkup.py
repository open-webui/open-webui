import logging
from typing import Optional, Literal

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)

DEPTH_OPTIONS = Literal["standard", "deep"]


def search_linkup(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    depth: DEPTH_OPTIONS = "standard",
) -> list[SearchResult]:
    """Search using Linkup's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Linkup API key
        query (str): The query to search for
        count (int): The maximum number of results to return
        filter_list (Optional[list[str]]): List of domains to filter results by
        depth (str): Search depth - "standard" or "deep"

    Returns:
        list[SearchResult]: A list of search results
    """
    url = "https://api.linkup.so/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "depth": depth,
        "outputType": "searchResults",
    }

    # Add domain filters if provided
    if filter_list:
        include_domains = [d for d in filter_list if not d.startswith("!")]
        exclude_domains = [d[1:] for d in filter_list if d.startswith("!")]

        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("results", [])

    # Apply additional filtering if needed
    if filter_list:
        results = get_filtered_results(results, filter_list)

    # Limit to requested count
    results = results[:count] if count else results

    return [
        SearchResult(
            link=result.get("url", ""),
            title=result.get("name", ""),
            snippet=result.get("content", ""),
        )
        for result in results
    ]

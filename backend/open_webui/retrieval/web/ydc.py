import logging
from typing import Optional, List

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_youcom(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    language: str = "EN",
) -> List[SearchResult]:
    """Search using You.com's YDC Index API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A You.com API key
        query (str): The query to search for
        count (int): Maximum number of results to return
        filter_list (list[str], optional): Domain filter list
        language (str): Language code for search results (default: "EN")
    """
    url = "https://ydc-index.io/v1/search"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": api_key,
    }
    params = {
        "query": query,
        "count": count,
        "language": language,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("results", {}).get("web", [])

    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"],
            title=result.get("title"),
            snippet=_build_snippet(result),
        )
        for result in results[:count]
    ]


def _build_snippet(result: dict) -> str:
    """Combine the description and snippets list into a single string.

    The You.com API returns a short ``description`` plus a ``snippets``
    list with richer passages.  Merging them gives downstream retrieval
    (embedding, BM25, bypass-loader context) the most content to work with.
    """
    parts: list[str] = []

    description = result.get("description")
    if description:
        parts.append(description)

    snippets = result.get("snippets")
    if snippets and isinstance(snippets, list):
        parts.extend(snippets)

    return "\n\n".join(parts)

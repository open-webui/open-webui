import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_serpstack(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    https_enabled: bool = True,
) -> list[SearchResult]:
    """Search using serpstack.com's and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A serpstack.com API key
        query (str): The query to search for
        https_enabled (bool): Whether to use HTTPS or HTTP for the API request
    """
    url = f"{'https' if https_enabled else 'http'}://api.serpstack.com/search"

    headers = {"Content-Type": "application/json"}
    params = {
        "access_key": api_key,
        "query": query,
    }

    response = requests.request("POST", url, headers=headers, params=params)
    response.raise_for_status()

    json_response = response.json()
    results = sorted(
        json_response.get("organic_results", []), key=lambda x: x.get("position", 0)
    )
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("snippet")
        )
        for result in results[:count]
    ]

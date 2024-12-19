import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_mojeek(
    api_key: str, query: str, count: int, filter_list: Optional[list[str]] = None
) -> list[SearchResult]:
    """Search using Mojeek's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Mojeek Search API key
        query (str): The query to search for
    """
    url = "https://api.mojeek.com/search"
    headers = {
        "Accept": "application/json",
    }
    params = {"q": query, "api_key": api_key, "fmt": "json", "t": count}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    json_response = response.json()
    results = json_response.get("response", {}).get("results", [])
    print(results)
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("desc")
        )
        for result in results
    ]

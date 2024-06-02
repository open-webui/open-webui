import logging

import requests

from apps.rag.search.main import SearchResult
from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_brave(api_key: str, query: str, count: int) -> list[SearchResult]:
    """Search using Brave's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Brave Search API key
        query (str): The query to search for
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": count}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("web", {}).get("results", [])
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("snippet")
        )
        for result in results[:count]
    ]

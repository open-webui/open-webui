import json
import logging
from typing import List
import requests

from apps.rag.search.main import SearchResult, filter_by_whitelist
from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_serper(api_key: str, query: str, count: int, whitelist:List[str]) -> list[SearchResult]:
    """Search using serper.dev's API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A serper.dev API key
        query (str): The query to search for
    """
    url = "https://google.serper.dev/search"

    payload = json.dumps({"q": query})
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()

    json_response = response.json()
    results = sorted(
        json_response.get("organic", []), key=lambda x: x.get("position", 0)
    )
    filtered_results = filter_by_whitelist(results, whitelist)
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in filtered_results[:count]
    ]

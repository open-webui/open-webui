import logging

import requests

from apps.rag.search.main import SearchResult
from config import SRC_LOG_LEVELS, RAG_WEB_SEARCH_RESULT_COUNT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_searxng(query_url: str, query: str) -> list[SearchResult]:
    """Search a SearXNG instance for a query and return the results as a list of SearchResult objects.

    Args:
        query_url (str): The URL of the SearXNG instance to search. Must contain "<query>" as a placeholder
        query (str): The query to search for
    """
    url = query_url.replace("<query>", query)
    if "&format=json" not in url:
        url += "&format=json"
    log.debug(f"searching {url}")

    r = requests.get(
        url,
        headers={
            "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
            "Accept": "text/html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        },
    )
    r.raise_for_status()

    json_response = r.json()
    results = json_response.get("results", [])
    sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("content")
        )
        for result in sorted_results[:RAG_WEB_SEARCH_RESULT_COUNT]
    ]

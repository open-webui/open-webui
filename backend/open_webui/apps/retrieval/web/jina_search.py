import logging

import requests
from open_webui.apps.retrieval.web.main import SearchResult
from open_webui.env import SRC_LOG_LEVELS
from yarl import URL

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_jina(api_key: str, query: str, count: int) -> list[SearchResult]:
    """
    Search using Jina's Search API and return the results as a list of SearchResult objects.
    Args:
        query (str): The query to search for
        count (int): The number of results to return

    Returns:
        list[SearchResult]: A list of search results
    """
    jina_search_endpoint = "https://s.jina.ai/"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    url = str(URL(jina_search_endpoint + query))
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    results = []
    for result in data["data"][:count]:
        results.append(
            SearchResult(
                link=result["url"],
                title=result.get("title"),
                snippet=result.get("content"),
            )
        )

    return results

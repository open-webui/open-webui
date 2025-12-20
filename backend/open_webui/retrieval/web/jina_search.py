import logging

import requests
from open_webui.retrieval.web.main import SearchResult
from yarl import URL

log = logging.getLogger(__name__)


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

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": api_key,
        "X-Retain-Images": "none",
    }

    payload = {"q": query, "count": count if count <= 10 else 10}

    url = str(URL(jina_search_endpoint))
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    results = []
    for result in data["data"]:
        results.append(
            SearchResult(
                link=result["url"],
                title=result.get("title"),
                snippet=result.get("content"),
            )
        )

    return results

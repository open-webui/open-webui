import logging

import requests
from open_webui.retrieval.web.main import SearchResult, SearchParameters
from open_webui.env import SRC_LOG_LEVELS
from yarl import URL

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_jina(
    params : SearchParameters,
    api_key : str,
) -> list[SearchResult]:
    """
    Search using Jina's Search API and return the results as a list of SearchResult objects.
    Args expected in params:
        params.query (str): The query to search for
        params.count (int): The number of results to return

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

    payload = {"q": params.query, "count": params.count if params.count <= 10 else 10}

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

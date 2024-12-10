import logging
from typing import Optional

import requests
from open_webui.apps.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_google_pse(
    api_key: str,
    search_engine_id: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using Google's Programmable Search Engine API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Programmable Search Engine API key
        search_engine_id (str): A Programmable Search Engine ID
        query (str): The query to search for
    """
    url = "https://www.googleapis.com/customsearch/v1"

    headers = {"Content-Type": "application/json"}
    params = {
        "cx": search_engine_id,
        "q": query,
        "key": api_key,
        "num": count,
    }

    response = requests.request("GET", url, headers=headers, params=params)
    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("items", [])
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("snippet"),
        )
        for result in results
    ]

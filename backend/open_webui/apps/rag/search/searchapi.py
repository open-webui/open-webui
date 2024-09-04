import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from open_webui.apps.rag.search.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_searchapi(
    api_key: str,
    engine: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using searchapi.io's API and return the results as a list of SearchResult objects.

    Args:
      api_key (str): A searchapi.io API key
      query (str): The query to search for
    """
    url = "https://www.searchapi.io/api/v1/search"

    engine = engine or "google"

    payload = {"engine": engine, "q": query, "api_key": api_key}

    url = f"{url}?{urlencode(payload)}"
    response = requests.request("GET", url)

    json_response = response.json()
    log.info(f"results from searchapi search: {json_response}")

    results = sorted(
        json_response.get("organic_results", []), key=lambda x: x.get("position", 0)
    )
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["link"], title=result["title"], snippet=result["snippet"]
        )
        for result in results[:count]
    ]

import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results, SearchParameters
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_searchapi(
    params : SearchParameters,
    api_key : str,
    engine : str,
) -> list[SearchResult]:
    """Search using searchapi.io's API and return the results as a list of SearchResult objects.

    Args expected in params:
      api_key (str): A searchapi.io API key
      params.query (str): The query to search for
    """
    url = "https://www.searchapi.io/api/v1/search"

    engine = engine or "google"

    payload = {"engine": engine, "q": params.query, "api_key": api_key}

    url = f"{url}?{urlencode(payload)}"
    response = requests.request("GET", url)

    json_response = response.json()
    log.info(f"results from searchapi search: {json_response}")

    results = sorted(
        json_response.get("organic_results", []), key=lambda x: x.get("position", 0)
    )
    results = get_filtered_results(results, params)
    return [
        SearchResult(
            link=result["link"], title=result["title"], snippet=result["snippet"]
        )
        for result in results[:params.count]
    ]

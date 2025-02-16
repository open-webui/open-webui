import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results, SearchParameters
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_mojeek(
    params : SearchParameters,
    api_key : str,
) -> list[SearchResult]:
    """Search using Mojeek's Search API and return the results as a list of SearchResult objects.

    Args expected in params:
        api_key (str): A Mojeek Search API key
        params.query (str): The query to search for
    """
    url = "https://api.mojeek.com/search"
    headers = {
        "Accept": "application/json",
    }
    url_params = {"q": params.query, "api_key": api_key, "fmt": "json", "t": params.count}

    response = requests.get(url, headers=headers, params=url_params)
    response.raise_for_status()
    json_response = response.json()
    results = json_response.get("response", {}).get("results", [])
    print(results)

    results = get_filtered_results(results, params)
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("desc")
        )
        for result in results
    ]

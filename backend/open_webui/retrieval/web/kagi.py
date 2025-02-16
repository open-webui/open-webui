import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results, SearchParameters
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_kagi(
    params : SearchParameters,    
    api_key : str,
) -> list[SearchResult]:
    """Search using Kagi's Search API and return the results as a list of SearchResult objects.

    The Search API will inherit the settings in your account, including results personalization and snippet length.

    Args expected in params:
        api_key (str): A Kagi Search API key
        params.query (str): The query to search for
        params.count (int): The number of results to return
    """
    url = "https://kagi.com/api/v0/search"
    headers = {
        "Authorization": f"Bot {api_key}",
    }
    url_params = {"q": params.query, "limit": params.count}

    response = requests.get(url, headers=headers, params=url_params)
    response.raise_for_status()
    json_response = response.json()
    search_results = json_response.get("data", [])

    results = [
        SearchResult(
            link=result["url"], title=result["title"], snippet=result.get("snippet")
        )
        for result in search_results
        if result["t"] == 0
    ]

    print(results)

    results = get_filtered_results(results, params)
    return results

import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results, SearchParameters
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_brave(
    params : SearchParameters,
    api_key : str,
) -> list[SearchResult]:
    """Search using Brave's Search API and return the results as a list of SearchResult objects.

    Args expected in params:
        api_key (str): A Brave Search API key
        query (str): The query to search for
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    url_params = {"q": params.query, "count": params.count}

    response = requests.get(url, headers=headers, params=url_params)
    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("web", {}).get("results", [])
    results = get_filtered_results(results, params)

    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("snippet")
        )
        for result in results[:params.count]
    ]

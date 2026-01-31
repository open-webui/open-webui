import logging
import time
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_brave(
    api_key: str, query: str, count: int, filter_list: Optional[list[str]] = None
) -> list[SearchResult]:
    """Search using Brave's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Brave Search API key
        query (str): The query to search for
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": count}

    response = requests.get(url, headers=headers, params=params)

    # Handle 429 rate limiting - Brave free tier allows 1 request/second
    # If rate limited, wait 1 second and retry once before failing
    if response.status_code == 429:
        log.info("Brave Search API rate limited (429), retrying after 1 second...")
        time.sleep(1)
        response = requests.get(url, headers=headers, params=params)

    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("web", {}).get("results", [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in results[:count]
    ]

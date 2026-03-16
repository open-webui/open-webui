import json
import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_serper(
    api_key: str, query: str, count: int, filter_list: Optional[list[str]] = None
) -> list[SearchResult]:
    """Search using serper.dev's API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A serper.dev API key
        query (str): The query to search for
    """
    url = "https://google.serper.dev/search"

    payload = json.dumps({"q": query})
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()

    json_response = response.json()
    results = sorted(
        json_response.get("organic", []), key=lambda x: x.get("position", 0)
    )
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in results[:count]
    ]

import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from open_webui.apps.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_serply(
    api_key: str,
    query: str,
    count: int,
    hl: str = "us",
    limit: int = 10,
    device_type: str = "desktop",
    proxy_location: str = "US",
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using serper.dev's API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A serply.io API key
        query (str): The query to search for
        hl (str): Host Language code to display results in (reference https://developers.google.com/custom-search/docs/xml_results?hl=en#wsInterfaceLanguages)
        limit (int): The maximum number of results to return [10-100, defaults to 10]
    """
    log.info("Searching with Serply")

    url = "https://api.serply.io/v1/search/"

    query_payload = {
        "q": query,
        "language": "en",
        "num": limit,
        "gl": proxy_location.upper(),
        "hl": hl.lower(),
    }

    url = f"{url}{urlencode(query_payload)}"
    headers = {
        "X-API-KEY": api_key,
        "X-User-Agent": device_type,
        "User-Agent": "open-webui",
        "X-Proxy-Location": proxy_location,
    }

    response = requests.request("GET", url, headers=headers)
    response.raise_for_status()

    json_response = response.json()
    log.info(f"results from serply search: {json_response}")

    results = sorted(
        json_response.get("results", []), key=lambda x: x.get("realPosition", 0)
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

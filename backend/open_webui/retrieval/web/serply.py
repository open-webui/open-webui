import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results, SearchParameters
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_serply(
    params : SearchParameters,
    api_key : str,
    hl : str = "us",
    device_type : str = "desktop",
    proxy_location : str = "US",
) -> list[SearchResult]:
    """Search using serper.dev's API and return the results as a list of SearchResult objects.

    Args expected in params:
        api_key (str): A serply.io API key
        hl (str): Host Language code to display results in (reference https://developers.google.com/custom-search/docs/xml_results?hl=en#wsInterfaceLanguages)
    """
    log.info("Searching with Serply")

    url = "https://api.serply.io/v1/search/"

    query_payload = {
        "q": params.query,
        "language": "en",
        "num": params.count,
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
    results = get_filtered_results(results, params)
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in results[:params.count]
    ]

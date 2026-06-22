import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = (10, 120)


def search_serphouse(
    api_key: str,
    engine: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using SERPHouse API and return SearchResult objects."""

    api_key = (api_key or "").strip()
    if not api_key:
        raise Exception("SERPHouse API key is missing")

    domain = (engine or "google.com").strip() or "google.com"

    try:
        count = int(count or 5)
    except ValueError:
        count = 5

    url = "https://api.serphouse.com/serp/live"

    params = {
        "q": query,
        "domain": domain,
        "device": "desktop",
        "serp_type": "web",
        "page": 1,
        "num_result": min(count, 10),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    json_response = response.json()
    log.info("results from SERPHouse search: %s", json_response)

    results_root = json_response.get("results", {})
    serp_results = results_root.get("results", {})

    organic_results = serp_results.get("organic", [])

    results = sorted(
        organic_results,
        key=lambda x: x.get("position", 0),
    )

    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result.get("link", ""),
            title=result.get("title"),
            snippet=result.get("snippet"),
        )
        for result in results[:count]
        if result.get("link")
    ]
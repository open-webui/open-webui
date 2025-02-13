import logging
from typing import Optional

import requests
import json
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def _parse_response(response):
    result = {}
    if "data" in response:
        data = response["data"]
        if "webPages" in data:
            webPages = data["webPages"]
            if "value" in webPages:
                result["webpage"] = [
                    {
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "summary": item.get("summary", ""),
                        "siteName": item.get("siteName", ""),
                        "siteIcon": item.get("siteIcon", ""),
                        "datePublished": item.get("datePublished", "")
                        or item.get("dateLastCrawled", ""),
                    }
                    for item in webPages["value"]
                ]
    return result


def search_bocha(
    api_key: str, query: str, count: int, filter_list: Optional[list[str]] = None
) -> list[SearchResult]:
    """Search using Bocha's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Bocha Search API key
        query (str): The query to search for
    """
    url = "https://api.bochaai.com/v1/web-search?utm_source=ollama"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = json.dumps(
        {"query": query, "summary": True, "freshness": "noLimit", "count": count}
    )

    response = requests.post(url, headers=headers, data=payload, timeout=5)
    response.raise_for_status()
    results = _parse_response(response.json())
    print(results)
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"], title=result.get("name"), snippet=result.get("summary")
        )
        for result in results.get("webpage", [])[:count]
    ]

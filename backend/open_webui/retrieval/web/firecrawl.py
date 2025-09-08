import logging
from typing import Optional, List
from urllib.parse import urljoin

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_firecrawl(
    firecrawl_url: str,
    firecrawl_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    try:
        firecrawl_search_url = urljoin(firecrawl_url, "/v1/search")
        response = requests.post(
            firecrawl_search_url,
            headers={
                "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
                "Authorization": f"Bearer {firecrawl_api_key}",
            },
            json={
                "query": query,
                "limit": count,
            },
        )
        response.raise_for_status()
        results = response.json().get("data", [])
        if filter_list:
            results = get_filtered_results(results, filter_list)
        results = [
            SearchResult(
                link=result.get("url"),
                title=result.get("title"),
                snippet=result.get("description"),
            )
            for result in results[:count]
        ]
        log.info(f"External search results: {results}")
        return results
    except Exception as e:
        log.error(f"Error in External search: {e}")
        return []

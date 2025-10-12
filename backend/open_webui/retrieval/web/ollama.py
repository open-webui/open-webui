import logging
from dataclasses import dataclass
from typing import Optional

import requests
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_ollama_cloud(
    url: str,
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using Ollama Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Ollama Search API key
        query (str): The query to search for
        count (int): Number of results to return
        filter_list (Optional[list[str]]): List of domains to filter results by
    """
    log.info(f"Searching with Ollama for query: {query}")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"query": query, "max_results": count}

    try:
        response = requests.post(f"{url}/api/web_search", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        log.info(f"Found {len(results)} results")

        return [
            SearchResult(
                link=result.get("url", ""),
                title=result.get("title", ""),
                snippet=result.get("content", ""),
            )
            for result in results
        ]
    except Exception as e:
        log.error(f"Error searching Ollama: {e}")
        return []

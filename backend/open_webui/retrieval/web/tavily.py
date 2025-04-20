import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult
from open_webui.env import SRC_LOG_LEVELS

import tavily

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_tavily(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    # **kwargs,
) -> list[SearchResult]:
    """Search using Tavily's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Tavily Search API key
        query (str): The query to search for

    Returns:
        list[SearchResult]: A list of search results
    """
    tavily_client = tavily.TavilyClient(api_key=api_key)
    response = tavily_client.search(query, max_results=count)
    results = response.get("results", [])
    return [
        SearchResult(
            link=result["url"],
            title=result["title"],
            snippet=result["content"],
        )
        for result in results
    ]

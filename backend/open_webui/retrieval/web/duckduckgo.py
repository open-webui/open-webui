import logging
from typing import Optional

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_duckduckgo(
    query: str, count: int, filter_list: Optional[list[str]] = None
) -> list[SearchResult]:
    """
    Search using DuckDuckGo's Search API and return the results as a list of SearchResult objects.
    Args:
        query (str): The query to search for
        count (int): The number of results to return

    Returns:
        list[SearchResult]: A list of search results
    """
    # Use the DDGS context manager to create a DDGS object
    search_results = []
    with DDGS() as ddgs:
        # Use the ddgs.text() method to perform the search
        try:
            search_results = ddgs.text(
                query, safesearch="moderate", max_results=count, backend="lite"
            )
        except RatelimitException as e:
            log.error(f"RatelimitException: {e}")
    if filter_list:
        search_results = get_filtered_results(search_results, filter_list)

    # Return the list of search results
    return [
        SearchResult(
            link=result["href"],
            title=result.get("title"),
            snippet=result.get("body"),
        )
        for result in search_results
    ]

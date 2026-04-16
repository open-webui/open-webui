import logging
import os
from typing import Optional

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from ddgs import DDGS
from ddgs.exceptions import RatelimitException

log = logging.getLogger(__name__)


def search_duckduckgo(
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    concurrent_requests: Optional[int] = None,
    backend: Optional[str] = 'auto',
) -> list[SearchResult]:
    """
    Search using DuckDuckGo's Search API and return the results as a list of SearchResult objects.
    Args:
        query (str): The query to search for
        count (int): The number of results to return
        backend (str): The search backend to use (auto, duckduckgo, google, brave, etc.)

    Returns:
        list[SearchResult]: A list of search results
    """
    proxy = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    # httpx (used internally by ddgs) reliably reads uppercase env vars;
    # ensure they are set so the proxy is picked up regardless of ddgs version
    if proxy:
        os.environ.setdefault("HTTPS_PROXY", proxy)
        os.environ.setdefault("HTTP_PROXY", proxy)

    # Use the DDGS context manager to create a DDGS object
    search_results = []
    with DDGS(proxy=proxy) as ddgs:
        if concurrent_requests:
            ddgs.threads = concurrent_requests

        # Use the ddgs.text() method to perform the search
        try:
            search_results = ddgs.text(query, safesearch='moderate', max_results=count, backend=backend)
        except RatelimitException as e:
            log.error(f'RatelimitException: {e}')
    if filter_list:
        search_results = get_filtered_results(search_results, filter_list)

    # Return the list of search results
    return [
        SearchResult(
            link=result['href'],
            title=result.get('title'),
            snippet=result.get('body'),
        )
        for result in search_results
    ]

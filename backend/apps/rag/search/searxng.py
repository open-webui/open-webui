import logging
import requests

from typing import List

from apps.rag.search.main import SearchResult
from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_searxng(
    query_url: str, query: str, count: int, **kwargs
) -> List[SearchResult]:
    """
    Search a SearXNG instance for a given query and return the results as a list of SearchResult objects.

    The function allows passing additional parameters such as language or time_range to tailor the search result.

    Args:
        query_url (str): The base URL of the SearXNG server.
        query (str): The search term or question to find in the SearXNG database.
        count (int): The maximum number of results to retrieve from the search.

    Keyword Args:
        language (str): Language filter for the search results; e.g., "en-US". Defaults to an empty string.
        safesearch (int): Safe search filter for safer web results; 0 = off, 1 = moderate, 2 = strict. Defaults to 1 (moderate).
        time_range (str): Time range for filtering results by date; e.g., "2023-04-05..today" or "all-time". Defaults to ''.
        categories: (Optional[List[str]]): Specific categories within which the search should be performed, defaulting to an empty string if not provided.

    Returns:
        List[SearchResult]: A list of SearchResults sorted by relevance score in descending order.

    Raise:
        requests.exceptions.RequestException: If a request error occurs during the search process.
    """

    # Default values for optional parameters are provided as empty strings or None when not specified.
    language = kwargs.get("language", "en-US")
    safesearch = kwargs.get("safesearch", "1")
    time_range = kwargs.get("time_range", "")
    categories = "".join(kwargs.get("categories", []))

    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
        "safesearch": safesearch,
        "language": language,
        "time_range": time_range,
        "categories": categories,
        "theme": "simple",
        "image_proxy": 0,
    }

    # Legacy query format
    if "<query>" in query_url:
        # Strip all query parameters from the URL
        query_url = query_url.split("?")[0]

    log.debug(f"searching {query_url}")

    response = requests.get(
        query_url,
        headers={
            "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
            "Accept": "text/html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        },
        params=params,
    )

    response.raise_for_status()  # Raise an exception for HTTP errors.

    json_response = response.json()
    results = json_response.get("results", [])
    sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("content")
        )
        for result in sorted_results[:count]
    ]

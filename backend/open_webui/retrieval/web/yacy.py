import logging
from typing import Optional

import requests
from requests.auth import HTTPDigestAuth
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_yacy(
    query_url: str,
    username: Optional[str],
    password: Optional[str],
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """
    Search a Yacy instance for a given query and return the results as a list of SearchResult objects.

    The function accepts username and password for authenticating to Yacy.

    Args:
        query_url (str): The base URL of the Yacy server.
        username (str): Optional YaCy username.
        password (str): Optional YaCy password.
        query (str): The search term or question to find in the Yacy database.
        count (int): The maximum number of results to retrieve from the search.

    Returns:
        list[SearchResult]: A list of SearchResults sorted by relevance score in descending order.

    Raise:
        requests.exceptions.RequestException: If a request error occurs during the search process.
    """

    # Use authentication if either username or password is set
    yacy_auth = None
    if username or password:
        yacy_auth = HTTPDigestAuth(username, password)

    params = {
        "query": query,
        "contentdom": "text",
        "resource": "global",
        "maximumRecords": count,
        "nav": "none",
    }

    # Check if provided a json API URL
    if not query_url.endswith("yacysearch.json"):
        # Strip all query parameters from the URL
        query_url = query_url.rstrip("/") + "/yacysearch.json"

    log.debug(f"searching {query_url}")

    response = requests.get(
        query_url,
        auth=yacy_auth,
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
    results = json_response.get("channels", [{}])[0].get("items", [])
    sorted_results = sorted(results, key=lambda x: x.get("ranking", 0), reverse=True)
    if filter_list:
        sorted_results = get_filtered_results(sorted_results, filter_list)
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in sorted_results[:count]
    ]

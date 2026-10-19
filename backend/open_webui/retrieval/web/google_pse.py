import logging
from typing import Optional

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.web.utils import get_json_with_timeout

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_google_pse(
    api_key: str,
    search_engine_id: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    request_timeout: Optional[int] = None,
) -> list[SearchResult]:
    """Search using Google's Programmable Search Engine API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Programmable Search Engine API key
        search_engine_id (str): A Programmable Search Engine ID
        query (str): The query to search for
        count (int): Number of results to return
        filter_list (Optional[list[str]]): Optional list of domains to filter
        request_timeout (Optional[int]): Optional timeout override in seconds for this request
    """
    url = "https://www.googleapis.com/customsearch/v1"

    headers = {"Content-Type": "application/json"}
    params = {
        "cx": search_engine_id,
        "q": query,
        "key": api_key,
        "num": count,
    }

    log.info("Google PSE query (length=%d)", len(query))
    json_response = get_json_with_timeout(
        url,
        provider_name="Google PSE",
        headers=headers,
        params=params,
        timeout_seconds=request_timeout,
    )
    results = json_response.get("items", [])

    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("snippet"),
        )
        for result in results
    ]

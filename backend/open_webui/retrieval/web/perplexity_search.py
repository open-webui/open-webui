import logging
from typing import Optional, Literal
import requests

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def search_perplexity_search(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    api_url: str = "https://api.perplexity.ai/search",
    user=None,
) -> list[SearchResult]:
    """Search using Perplexity API and return the results as a list of SearchResult objects.

    Args:
      api_key (str): A Perplexity API key
      query (str): The query to search for
      count (int): Maximum number of results to return
      filter_list (Optional[list[str]]): List of domains to filter results
      api_url (str): Custom API URL (defaults to https://api.perplexity.ai/search)
      user: Optional user object for forwarding user info headers

    """

    # Handle PersistentConfig object
    if hasattr(api_key, "__str__"):
        api_key = str(api_key)

    if hasattr(api_url, "__str__"):
        api_url = str(api_url)

    try:
        url = api_url

        # Create payload for the API call
        payload = {
            "query": query,
            "max_results": count,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Forward user info headers if user is provided
        if user is not None:
            headers = include_user_info_headers(headers, user)

        # Make the API request
        response = requests.request("POST", url, json=payload, headers=headers)
        # Parse the JSON response
        json_response = response.json()

        # Extract citations from the response
        results = json_response.get("results", [])

        return [
            SearchResult(
                link=result["url"], title=result["title"], snippet=result["snippet"]
            )
            for result in results
        ]

    except Exception as e:
        log.error(f"Error searching with Perplexity Search API: {e}")
        return []

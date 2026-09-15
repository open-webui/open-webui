from __future__ import annotations

"""
Staan.ai Web Search integration for Open WebUI.

This module provides a small adapter around the Staan.ai Web Search API,
allowing Open WebUI to use Staan.ai as an external web search provider.

The search_staan() function:
    - Sends a web search request to the Staan.ai API.
    - Supports Open WebUI's query, result count, market, and URL filtering
      parameters.
    - Optionally requests additional relevant snippets from Staan.ai.
    - Converts Staan.ai results into Open WebUI SearchResult objects.
    - Filters results using Open WebUI's standard filtering mechanism.

API endpoint:
    https://api.staan.ai/v2/search/web

Authentication:
    The Staan.ai API key is passed using the HTTP Bearer authentication
    header.

Expected Staan.ai response structure:
    {
        "web": {
            "results": [
                {
                    "url": "...",
                    "title": "...",
                    "snippet": "...",
                    "extra_snippets": [
                        {"chunk": "..."}
                    ]
                }
            ]
        }
    }

This module does not expose or store the API key. The key is supplied
by Open WebUI when search_staan() is called.
"""

import logging

import requests

from open_webui.retrieval.web.main import SearchResult, get_filtered_results


# Logger used to report search requests and API errors.
log = logging.getLogger(__name__)

# Base URL of the Staan.ai v2 API.
STAAN_API_BASE_URL = "https://api.staan.ai/v2"


def format_extra_snippets(result):
    """
    Combine the main snippet with additional snippets returned by Staan.ai.

    Staan.ai can return several relevant text chunks for a search result.
    These chunks are appended to the main snippet and separated by blank
    lines so that Open WebUI receives a richer text description.
    """
    snippet = result.get("snippet", "") or ""

    extra_snippets = result.get("extra_snippets", [])

    # Extract the "chunk" field from each additional snippet.
    extra = "\n\n".join(
        item.get("chunk", "")
        for item in extra_snippets
        if item.get("chunk")
    )

    if extra:
        return f"{snippet}\n\n{extra}"

    return snippet


def search_staan(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
    market: str = "fr-fr",
    extra_snippets: int = 2,
) -> list[SearchResult]:
    """
    Search the web using the Staan.ai Search API.

    Args:
        api_key:
            Staan.ai API key used for authentication.

        query:
            Search query submitted to Staan.ai.

        count:
            Maximum number of search results returned to Open WebUI.

        filter_list:
            Optional list of URL/domain filters supported by Open WebUI.
            The standard Open WebUI filtering function is used.

        market:
            Search market/localization used by Staan.ai.
            Defaults to French results ("fr-fr").

        extra_snippets:
            Number of additional relevant snippets requested from Staan.ai.
            Set to 0 to disable additional snippets.

    Returns:
        A list of Open WebUI SearchResult objects containing the URL,
        title, and combined snippets returned by Staan.ai.

    Raises:
        requests.HTTPError:
            If the Staan.ai API returns an HTTP error response.
        requests.RequestException:
            If the HTTP request itself fails.
    """

    # Staan.ai web search endpoint.
    url = f"{STAAN_API_BASE_URL}/search/web"

    # Authenticate using the API key supplied by Open WebUI.
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    # Basic search parameters.
    params = {
        "q": query,
        "market": market,
    }

    # Request additional relevant snippets when enabled.
    #
    # min_score limits the returned snippets to those with a minimum
    # relevance score.
    if extra_snippets > 0:
        params.update({
            "extra_snippets": "true",
            "max_snippets": extra_snippets,
            "min_score": 0.2,
        })

    log.debug(
        "Staan web search: query=%r count=%d market=%s",
        query,
        count,
        market,
    )

    # Perform the search request.
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15,
    )

    # Log the API response body before raising the HTTP error.
    # This makes configuration/API problems easier to diagnose.
    if not response.ok:
        log.error(
            "Staan API error: HTTP %s - %s",
            response.status_code,
            response.text,
        )

    # Raise an exception for any HTTP error response.
    response.raise_for_status()

    # Decode the JSON response returned by Staan.ai.
    payload = response.json()

    # Extract the list of web search results.
    results = payload.get("web", {}).get("results", [])

    # Apply Open WebUI's standard URL/domain filtering if requested.
    if filter_list:
        results = get_filtered_results(results, filter_list)

    # Convert Staan.ai results to the format expected by Open WebUI.
    #
    # Only results containing a valid URL are returned.
    return [
        SearchResult(
            link=result["url"],
            title=result.get("title", ""),
            snippet=format_extra_snippets(result),
        )
        for result in results[:count]
        if result.get("url")
    ]

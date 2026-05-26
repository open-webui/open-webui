"""
Exa Search API Integration for Open WebUI.

Search remains Exa-backed, but all HTTP I/O in this module is async via
aiohttp so tool calls and subagent runs never block the event loop.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List

import aiohttp
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

EXA_API_BASE = "https://api.exa.ai"


@dataclass
class ExaSearchResult:
    """Result from Exa search API"""

    url: str
    title: str
    snippet: str
    published_date: Optional[str] = None
    author: Optional[str] = None


@dataclass
class ExaContentResult:
    """Result from Exa contents API"""

    url: str
    title: str
    text: str
    published_date: Optional[str] = None
    author: Optional[str] = None


async def _post_exa_json(
    api_key: str,
    path: str,
    payload: dict,
    timeout_seconds: int,
) -> dict:
    """POST JSON to Exa and return decoded JSON with good error context."""
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{EXA_API_BASE}{path}",
            headers=headers,
            json=payload,
        ) as response:
            response_text = await response.text()

            if response.status >= 400:
                raise Exception(
                    f"Exa API {path} failed: HTTP {response.status} {response_text[:500]}"
                )

            try:
                return await response.json(content_type=None)
            except Exception as e:
                raise Exception(f"Exa API {path} returned invalid JSON: {e}")


async def search_exa(
    api_key: str,
    query: str,
    num_results: int = 10,
    search_type: str = "auto",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> List[SearchResult]:
    """
    Search using Exa Search API and return the results.
    This performs search ONLY - no content fetching.

    Args:
        api_key: Exa API key
        query: The search query
        num_results: Number of results to return (max 100)
        search_type: Search type - "auto", "neural", or "keyword"
        include_domains: List of domains to include in search
        exclude_domains: List of domains to exclude from search

    Returns:
        List of SearchResult objects with link, title, and snippet
    """
    log.info(f"Exa search for query: {query}")

    payload = {
        "query": query,
        "numResults": min(num_results, 100),
        "type": search_type,
        # Only return basic info for search results, no full text
        "contents": {
            "highlights": {
                "numSentences": 2,
                "highlightsPerUrl": 1,
            }
        },
    }

    # Add domain filters if provided
    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains

    try:
        data = await _post_exa_json(
            api_key=api_key,
            path="/search",
            payload=payload,
            timeout_seconds=30,
        )

        results = []
        for result in data.get("results", []):
            # Use highlights as snippet, fallback to empty string
            highlights = result.get("highlights", [])
            snippet = highlights[0] if highlights else ""

            results.append(
                SearchResult(
                    link=result.get("url", ""),
                    title=result.get("title", ""),
                    snippet=snippet,
                )
            )

        log.info(f"Exa search found {len(results)} results")
        return results

    except aiohttp.ClientError as e:
        log.error(f"Exa search client error: {e}")
        raise Exception(f"Exa search failed: {e}")
    except TimeoutError as e:
        log.error(f"Exa search timeout: {e}")
        raise Exception(f"Exa search timed out: {e}")


async def fetch_exa_contents(
    api_key: str,
    urls: List[str],
    max_characters: int = 10000,
    livecrawl: str = "fallback",
) -> List[ExaContentResult]:
    """
    Fetch full content from URLs using Exa Contents API.

    Deprecated for built-in web_fetch: web_fetch now uses Jina Reader. This
    remains async for compatibility with any older code that still imports it.

    Args:
        api_key: Exa API key
        urls: List of URLs to fetch content from
        max_characters: Maximum characters to return per page
        livecrawl: Crawl mode - "never", "fallback", "always"

    Returns:
        List of ExaContentResult objects with full text content
    """
    if not urls:
        return []

    log.info(f"Exa fetch contents for {len(urls)} URLs")

    payload = {
        "urls": urls,
        "text": {
            "maxCharacters": max_characters,
            "includeHtmlTags": False,
        },
        "livecrawl": livecrawl,
        "livecrawlTimeout": 10000,
    }

    try:
        data = await _post_exa_json(
            api_key=api_key,
            path="/contents",
            payload=payload,
            timeout_seconds=60,
        )

        results = []
        for result in data.get("results", []):
            results.append(
                ExaContentResult(
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    text=result.get("text", ""),
                    published_date=result.get("publishedDate"),
                    author=result.get("author"),
                )
            )

        # Log any errors from the statuses
        statuses = data.get("statuses", [])
        for status in statuses:
            if status.get("status") != "success":
                log.warning(
                    f"Exa fetch failed for {status.get('id')}: {status.get('error')}"
                )

        log.info(f"Exa fetch returned content for {len(results)} URLs")
        return results

    except aiohttp.ClientError as e:
        log.error(f"Exa contents fetch client error: {e}")
        raise Exception(f"Exa contents fetch failed: {e}")
    except TimeoutError as e:
        log.error(f"Exa contents fetch timeout: {e}")
        raise Exception(f"Exa contents fetch timed out: {e}")

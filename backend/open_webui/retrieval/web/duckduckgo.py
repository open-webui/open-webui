import logging
import os
import time
from typing import Optional

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from ddgs import DDGS
from ddgs.exceptions import RatelimitException

log = logging.getLogger(__name__)

# Cooldown durations (seconds).  Retrying immediately after a rate-limit or
# bot-detection extends the IP block — back off meaningfully instead.
_COOLDOWN_RATELIMIT_S = 30
_COOLDOWN_BOT_S = 60

_cooldown_until: float = 0.0  # monotonic timestamp; 0 = no active cooldown


def _activate_cooldown(seconds: float) -> None:
    global _cooldown_until
    _cooldown_until = max(_cooldown_until, time.monotonic() + seconds)


def _cooldown_remaining() -> float:
    return max(0.0, _cooldown_until - time.monotonic())


# Mimic a real browser navigation request.  DuckDuckGo (and many other
# services) inspect Sec-Fetch-* headers to distinguish browser traffic from
# bots — missing these headers is one of the most common detection triggers.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Site": "same-origin",
    # Referer tells DuckDuckGo the request originates from its own HTML frontend
    "Referer": "https://html.duckduckgo.com/",
}


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
    # Bail out early during a cooldown — hitting the network while blocked
    # resets the ban timer on DuckDuckGo's side.
    remaining = _cooldown_remaining()
    if remaining > 0:
        raise RuntimeError(
            f"DuckDuckGo rate-limit cooldown active — retry in {int(remaining) + 1}s"
        )

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

    search_results = []
    with DDGS(proxy=proxy, headers=_BROWSER_HEADERS) as ddgs:
        if concurrent_requests:
            ddgs.threads = concurrent_requests

        try:
            search_results = ddgs.text(query, safesearch='moderate', max_results=count, backend=backend)
        except RatelimitException as e:
            # Activate cooldown before logging — prevents any concurrent call
            # from slipping through while we handle the exception.
            _activate_cooldown(_COOLDOWN_RATELIMIT_S)
            log.error(f'RatelimitException: {e}')

    if filter_list:
        search_results = get_filtered_results(search_results, filter_list)

    return [
        SearchResult(
            link=result['href'],
            title=result.get('title'),
            snippet=result.get('body'),
        )
        for result in search_results
    ]

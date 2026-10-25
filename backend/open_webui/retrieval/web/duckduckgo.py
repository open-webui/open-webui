from __future__ import annotations

import logging
import urllib.request
from random import shuffle

from open_webui.env import USE_SLIM
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)

DDGS_DEFAULT_BACKEND = 'auto'
DDGS_AUTO_BACKENDS = frozenset((DDGS_DEFAULT_BACKEND, 'all'))
DDGS_BACKEND_SEPARATOR = ','
DDGS_TEXT_BACKENDS = (
    'brave',
    'duckduckgo',
    'google',
    'grokipedia',
    'mojeek',
    'startpage',
    'wikipedia',
    'yahoo',
    'yandex',
)
DDGS_UNKNOWN_BACKENDS_ERROR = 'Unknown DDGS backends in exclusion list'
DDGS_EMPTY_BACKENDS_ERROR = 'DDGS backend exclusion removed every available text backend'


def get_ddgs_backend(backend: str | None, excluded_backends: list[str] | None) -> str:
    selected_backend = backend or DDGS_DEFAULT_BACKEND
    if selected_backend not in DDGS_AUTO_BACKENDS:
        return selected_backend

    excluded = {item.strip().lower() for item in excluded_backends or [] if item.strip()}
    if not excluded:
        return selected_backend

    unknown = excluded.difference(DDGS_TEXT_BACKENDS)
    if unknown:
        raise ValueError(f'{DDGS_UNKNOWN_BACKENDS_ERROR}: {DDGS_BACKEND_SEPARATOR.join(sorted(unknown))}')

    allowed = [item for item in DDGS_TEXT_BACKENDS if item not in excluded]
    if not allowed:
        raise ValueError(DDGS_EMPTY_BACKENDS_ERROR)

    shuffle(allowed)
    return DDGS_BACKEND_SEPARATOR.join(allowed)


def search_duckduckgo(
    query: str,
    count: int,
    filter_list: list[str] | None = None,
    concurrent_requests: int | None = None,
    backend: str | None = DDGS_DEFAULT_BACKEND,
    excluded_backends: list[str] | None = None,
) -> list[SearchResult]:
    """
    Search using DuckDuckGo's Search API and return the results as a list of SearchResult objects.
    Args:
        query (str): The query to search for
        count (int): The number of results to return
        backend (str): The search backend to use (auto, duckduckgo, google, brave, etc.)
        excluded_backends (list[str]): Backends to exclude when backend is auto or all

    Returns:
        list[SearchResult]: A list of search results
    """
    if USE_SLIM:
        raise ValueError(
            'DDGS is unavailable in slim. Configure another web search provider in Admin Settings > Web Search.'
        )

    selected_backend = get_ddgs_backend(backend, excluded_backends)

    from ddgs import DDGS

    # The ddgs library (primp-based) does not auto-detect proxy env vars.
    # Resolve via stdlib getproxies() — same pattern as the other loaders.
    env_proxies = urllib.request.getproxies()
    proxy = env_proxies.get('https') or env_proxies.get('http')
    with DDGS(proxy=proxy) as ddgs:
        if concurrent_requests:
            ddgs.threads = concurrent_requests

        search_results = ddgs.text(
            query,
            safesearch='moderate',
            max_results=count,
            backend=selected_backend,
        )
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

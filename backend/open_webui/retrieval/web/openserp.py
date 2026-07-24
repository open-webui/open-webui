from __future__ import annotations

import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)


async def search_openserp(
    base_url: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
) -> list[SearchResult]:
    """Query an OpenSERP instance and return normalised results.

    OpenSERP aggregates results from 6 engines (google, bing, yandex,
    baidu, duckduckgo, ecosia) at once via ``/mega/search``.

    No API key is required -- only a reachable OpenSERP base URL.
    """
    url = f"{base_url.rstrip('/')}/mega/search"
    params = {"text": query, "limit": count}

    log.debug("searching OpenSERP at %s", url)

    session = await get_session()
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        payload = await response.json()

    results = payload.get("results", [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=item.get("url", ""),
            title=item.get("title"),
            snippet=item.get("snippet"),
        )
        for item in results[:count]
    ]

from __future__ import annotations

import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)


async def search_serpstack(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
    https_enabled: bool = True,
) -> list[SearchResult]:
    """Query the serpstack.com API and return normalised results.

    Uses HTTPS by default; set ``https_enabled=False`` for free-tier HTTP access.
    """
    scheme = 'https' if https_enabled else 'http'
    url = f'{scheme}://api.serpstack.com/search'
    params = {'access_key': api_key, 'query': query}

    session = await get_session()
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        payload = await response.json()

    organic = sorted(payload.get('organic_results', []), key=lambda x: x.get('position', 0))
    if filter_list:
        organic = get_filtered_results(organic, filter_list)

    return [
        SearchResult(
            link=item.get('url', ''),
            title=item.get('title'),
            snippet=item.get('snippet'),
        )
        for item in organic[:count]
    ]

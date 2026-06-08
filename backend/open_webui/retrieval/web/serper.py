from __future__ import annotations

import json
import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)


async def search_serper(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
) -> list[SearchResult]:
    """Query the serper.dev Google Search API and return normalised results.

    Results are sorted by their position field before truncation.
    """
    url = 'https://google.serper.dev/search'
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    session = await get_session()
    async with session.post(url, headers=headers, data=json.dumps({'q': query})) as response:
        response.raise_for_status()
        payload = await response.json()

    organic = sorted(payload.get('organic', []), key=lambda item: item.get('position', 0))
    if filter_list:
        organic = get_filtered_results(organic, filter_list)

    return [
        SearchResult(
            link=item.get('link', ''),
            title=item.get('title'),
            snippet=item.get('snippet'),
        )
        for item in organic[:count]
    ]

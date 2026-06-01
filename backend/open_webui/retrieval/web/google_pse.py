from __future__ import annotations

import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)


async def search_google_pse(
    api_key: str,
    search_engine_id: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
    referer: str | None = None,
) -> list[SearchResult]:
    """Query Google Programmable Search Engine with automatic pagination.

    The PSE API returns at most 10 results per request, so this function
    issues multiple requests when ``count > 10``.
    """
    url = 'https://www.googleapis.com/customsearch/v1'
    headers: dict[str, str] = {'Content-Type': 'application/json'}
    if referer:
        headers['Referer'] = referer

    all_items: list[dict] = []
    start_index = 1  # PSE uses 1-based pagination

    session = await get_session()
    remaining = count
    while remaining > 0:
        page_size = min(remaining, 10)
        params = {
            'cx': search_engine_id,
            'q': query,
            'key': api_key,
            'num': str(page_size),
            'start': str(start_index),
        }

        async with session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            payload = await response.json()

        items = payload.get('items', [])
        if not items:
            break

        all_items.extend(items)
        remaining -= len(items)
        start_index += 10

    if filter_list:
        all_items = get_filtered_results(all_items, filter_list)

    return [
        SearchResult(
            link=item.get('link', ''),
            title=item.get('title'),
            snippet=item.get('snippet'),
        )
        for item in all_items
    ]

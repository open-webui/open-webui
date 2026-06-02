from __future__ import annotations

import asyncio
import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

# Brave free-tier rate limit: 1 request per second.
_RATE_LIMIT_RETRY_DELAY = 1.0


async def search_brave(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
) -> list[SearchResult]:
    """Query the Brave Web Search API and return normalised results.

    Retries once on HTTP 429 (rate-limit) after a short delay.
    """
    url = 'https://api.search.brave.com/res/v1/web/search'
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': api_key,
    }
    params = {'q': query, 'count': count}

    session = await get_session()
    async with session.get(url, headers=headers, params=params) as response:
        if response.status == 429:
            log.info('Brave Search rate-limited (429); retrying after %.1fs', _RATE_LIMIT_RETRY_DELAY)
            await asyncio.sleep(_RATE_LIMIT_RETRY_DELAY)
            async with session.get(url, headers=headers, params=params) as retry_resp:
                retry_resp.raise_for_status()
                payload = await retry_resp.json()
        else:
            response.raise_for_status()
            payload = await response.json()

    web_results = payload.get('web', {}).get('results', [])
    if filter_list:
        web_results = get_filtered_results(web_results, filter_list)

    return [
        SearchResult(
            link=item.get('url', ''),
            title=item.get('title'),
            snippet=item.get('description'),
        )
        for item in web_results[:count]
    ]

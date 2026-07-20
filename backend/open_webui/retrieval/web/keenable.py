from __future__ import annotations

import asyncio
import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

KEENABLE_BASE_URL = 'https://api.keenable.ai'
# With an API key → the authenticated endpoint (higher rate limits); without a
# key → the public keyless endpoint (lower limits). Both accept the same params
# and return the same response shape, so Keenable works out of the box and a key
# is only needed to raise limits.
_SEARCH_PATH = '/v1/search'
_PUBLIC_SEARCH_PATH = '/v1/search/public'
# Retry once on a keyless rate-limit (HTTP 429) after a short delay.
_RATE_LIMIT_RETRY_DELAY = 1.0


async def search_keenable(
    api_key: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
) -> list[SearchResult]:
    """Query the Keenable Search API and return normalised results.

    Runs keyless by default against the public endpoint; if ``api_key`` is set,
    the authenticated endpoint is used instead (higher rate limits). Retries
    once on HTTP 429 before surfacing a hint to configure an API key.
    """
    path = _SEARCH_PATH if api_key else _PUBLIC_SEARCH_PATH
    url = f'{KEENABLE_BASE_URL}{path}'
    headers = {
        'Accept': 'application/json',
        # Traffic attribution — Keenable records the calling app via this header.
        'X-Keenable-Title': 'Open WebUI',
    }
    if api_key:
        headers['X-API-Key'] = api_key
    params = {'query': query, 'mode': 'pro'}

    session = await get_session()
    async with session.get(url, headers=headers, params=params) as response:
        if response.status == 429:
            log.info('Keenable Search rate-limited (429); retrying after %.1fs', _RATE_LIMIT_RETRY_DELAY)
            await asyncio.sleep(_RATE_LIMIT_RETRY_DELAY)
            async with session.get(url, headers=headers, params=params) as retry_resp:
                if retry_resp.status == 429 and not api_key:
                    raise Exception('Keenable Search rate limit reached; set KEENABLE_SEARCH_API_KEY to raise limits')
                retry_resp.raise_for_status()
                payload = await retry_resp.json()
        else:
            response.raise_for_status()
            payload = await response.json()

    results = payload.get('results', [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=item.get('url', ''),
            title=item.get('title'),
            snippet=item.get('snippet') or item.get('description'),
        )
        for item in results[:count]
    ]

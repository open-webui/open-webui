from __future__ import annotations

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session


async def search_serphouse(
    api_key: str,
    domain: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
) -> list[SearchResult]:
    """Query SERPHouse and return normalised organic results."""
    session = await get_session()
    async with session.get(
        'https://api.serphouse.com/serp/live',
        params={
            'q': query,
            'domain': (domain or 'google.com').strip() or 'google.com',
            'device': 'desktop',
            'serp_type': 'web',
            'page': 1,
            'num_result': count,
        },
        headers={'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'},
    ) as response:
        response.raise_for_status()
        payload = await response.json()

    organic = payload.get('results', {}).get('results', {}).get('organic', [])
    organic = sorted(organic, key=lambda item: item.get('position', 0))
    if filter_list:
        organic = get_filtered_results(organic, filter_list)

    return [
        SearchResult(
            link=item.get('link', ''),
            title=item.get('title'),
            snippet=item.get('snippet'),
        )
        for item in organic[:count]
        if item.get('link')
    ]

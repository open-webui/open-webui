import logging
import time
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)


def search_brave_llm_context(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    context_tokens: int = 8192,
) -> list[SearchResult]:
    """Search using Brave's LLM Context API and return pre-extracted, relevance-scored
    page content ready for LLM consumption.

    Uses /res/v1/llm/context instead of /res/v1/web/search. Same API key, same pricing.
    Returns full extracted passages per URL rather than short snippets, eliminating
    the need for post-search scraping.

    Args:
        api_key (str): A Brave Search API key (same key as web search)
        query (str): The query to search for
        count (int): Maximum number of results to return
        filter_list (list[str], optional): Domain filter list
        context_tokens (int): Maximum total tokens to retrieve (1024–32768, default 8192)
    """
    url = 'https://api.search.brave.com/res/v1/llm/context'
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': api_key,
    }
    params = {
        'q': query,
        'count': count,
        'maximum_number_of_tokens': context_tokens,
    }

    response = requests.get(url, headers=headers, params=params)

    # Handle 429 rate limiting - same rate limits as web search
    if response.status_code == 429:
        log.info('Brave LLM Context API rate limited (429), retrying after 1 second...')
        time.sleep(1)
        response = requests.get(url, headers=headers, params=params)

    response.raise_for_status()

    json_response = response.json()
    results = json_response.get('grounding', {}).get('generic', [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result['url'],
            title=result.get('title'),
            snippet='\n\n'.join(result.get('snippets', [])),
        )
        for result in results[:count]
    ]

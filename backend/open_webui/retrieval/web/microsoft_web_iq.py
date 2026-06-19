import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def search_microsoft_web_iq(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    language: str = 'en',
    user=None,
) -> list[SearchResult]:
    """Search using Microsoft Web IQ API and return the results as a list of SearchResult objects.

    Args:
      api_key (str): A Microsoft Web IQ API key
      query (str): The query to search for
      count (int): Maximum number of results to return
      filter_list (Optional[list[str]]): List of domains to filter results
      language (str): 2-letter ISO 639-1 language code for the search results
      user: Optional user object for forwarding user info headers

    """

    # Handle ConfigVar object
    if hasattr(api_key, '__str__'):
        api_key = str(api_key)

    if hasattr(language, '__str__'):
        language = str(language)

    try:
        url = 'https://api.microsoft.ai/v3/search/web'

        # The web API does not return a `snippet` field. Use contentFormat=passage
        # so a model extracts the query-relevant paragraphs into `content`.
        payload = {
            'query': query,
            'maxResults': count,
            'language': language,
            'contentFormat': 'passage',
        }

        headers = {
            'host': 'api.microsoft.ai',
            'x-apikey': api_key,
            'content-type': 'application/json',
        }

        # Forward user info headers if user is provided
        if user is not None:
            headers = include_user_info_headers(headers, user)

        response = requests.request('POST', url, json=payload, headers=headers)
        response.raise_for_status()
        json_response = response.json()

        results = json_response.get('webResults', [])
        if filter_list:
            results = get_filtered_results(results, filter_list)

        return [
            SearchResult(
                link=result['url'],
                title=result.get('title'),
                snippet=result.get('content'),
            )
            for result in results
        ]

    except Exception as e:
        log.error(f'Error searching with Microsoft Web IQ API: {e}')
        return []

import base64
import logging
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)

# SERPHouse live SERP requests can take a while because results are fetched in real time.
DEFAULT_TIMEOUT = (10, 120)
DEFAULT_LOCATION = 'United States'


def _decode_bing_redirect(link: str) -> Optional[str]:
    """Extract destination URL from Bing click-tracking redirects."""
    parsed = urlparse(link)
    if 'bing.' not in parsed.netloc or '/ck/' not in parsed.path:
        return None

    # Bing query strings often start with "!&&"; strip leading punctuation before parsing.
    query = parse_qs(parsed.query.lstrip('!&'))
    encoded = (query.get('u') or [None])[0]
    if not encoded:
        return None

    payload = encoded[2:] if encoded.startswith('a1') else encoded
    payload += '=' * (-len(payload) % 4)
    try:
        return base64.b64decode(payload).decode('utf-8')
    except Exception:
        return None


def _normalize_link(link: str) -> str:
    if not link:
        return link

    try:
        parsed = urlparse(link)
        if 'google.' in parsed.netloc and parsed.path in ('/url', '/imgres'):
            query = parse_qs(parsed.query)
            for key in ('url', 'q'):
                if key in query and query[key]:
                    return query[key][0]

        if decoded := _decode_bing_redirect(link):
            return decoded
    except Exception:
        pass

    return link


def _extract_organic_results(json_response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract organic web results from SERPHouse response shapes."""
    results = json_response.get('results')
    if not isinstance(results, dict):
        return []

    organic = results.get('organic')
    if isinstance(organic, list):
        return organic

    nested = results.get('results')
    if isinstance(nested, dict):
        organic = nested.get('organic')
        if isinstance(organic, list):
            return organic

    top_level_organic = json_response.get('organic')
    if isinstance(top_level_organic, list):
        return top_level_organic

    return []


def search_serphouse(
    api_key: str,
    engine: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using serphouse.com's API and return the results as a list of SearchResult objects.

    Args:
      api_key (str): A serphouse.com API key
      engine (str): Search domain (e.g. google.com)
      query (str): The query to search for
    """
    api_key = (api_key or '').strip()
    if not api_key:
        raise Exception('SERPHouse API key is missing')

    url = 'https://api.serphouse.com/serp/live'
    domain = (engine or 'google.com').strip() or 'google.com'

    params = {
        'q': query,
        'domain': domain,
        'device': 'desktop',
        'serp_type': 'web',
        'loc': DEFAULT_LOCATION,
        'page': '1',
        'num_result': str(min(count, 10)),
    }

    headers = {'Authorization': f'Bearer {api_key}'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise Exception(
            'SERPHouse search timed out. The live API can take up to 2 minutes; try again or use fewer results.'
        ) from exc
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None:
            if exc.response.status_code == 401:
                raise Exception('SERPHouse authentication failed. Check your API key in Web Search settings.') from exc

            try:
                error_body = exc.response.json()
                error_msg = error_body.get('msg') or error_body.get('message')
                error_details = error_body.get('error')
                if error_msg:
                    if error_details:
                        raise Exception(f'SERPHouse API error: {error_msg} ({error_details})') from exc
                    raise Exception(f'SERPHouse API error: {error_msg}') from exc
            except ValueError:
                pass

        raise

    json_response = response.json()
    log.info('results from serphouse search: %s', json_response.get('status'))

    if json_response.get('status') != 'success':
        raise Exception(json_response.get('msg', 'SERPHouse search failed'))

    results = _extract_organic_results(json_response)
    results = sorted(results, key=lambda x: x.get('position', 0))

    normalized_results = []
    for result in results:
        raw_link = result.get('link') or result.get('url') or result.get('displayed_link') or ''
        link = _normalize_link(raw_link.strip())
        if not link:
            continue

        normalized = {**result, 'link': link}
        normalized_results.append(normalized)

    if filter_list:
        normalized_results = get_filtered_results(normalized_results, filter_list)

    search_results = []
    for result in normalized_results[:count]:
        snippet = result.get('snippet') or result.get('description') or result.get('text')
        search_results.append(
            SearchResult(
                link=result['link'],
                title=result.get('title') or result.get('site_title'),
                snippet=snippet,
            )
        )

    if not search_results:
        raise Exception('SERPHouse returned no organic web results for this query')

    return search_results

import logging
import re
from typing import Any, List, Optional

import requests
from fastapi import Request
from open_webui.env import FORWARD_SESSION_INFO_HEADER_CHAT_ID
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)

PLACEHOLDER_PATTERN = re.compile(r'\{\{\s*(query|count|urls)\s*\}\}', re.IGNORECASE)


def render_payload(payload: Any, variables: dict[str, Any]) -> Any:
    """Replace ``{{query}}``, ``{{count}}``, and ``{{urls}}`` placeholders.

    A placeholder that occupies the whole string keeps the type of the
    replacement (e.g. ``{{count}}`` becomes an integer and ``{{urls}}`` a
    list). Placeholders embedded in a larger string are replaced inline.
    """
    if isinstance(payload, dict):
        return {key: render_payload(value, variables) for key, value in payload.items()}
    if isinstance(payload, list):
        return [render_payload(item, variables) for item in payload]
    if isinstance(payload, str):
        match = PLACEHOLDER_PATTERN.fullmatch(payload.strip())
        if match:
            variable = variables.get(match.group(1).lower())
            return variable if variable is not None else payload

        def replace(match):
            variable = variables.get(match.group(1).lower())
            if variable is None:
                return match.group(0)
            if isinstance(variable, list):
                return ','.join(str(item) for item in variable)
            return str(variable)

        return PLACEHOLDER_PATTERN.sub(replace, payload)
    return payload


def search_custom(
    request: Request,
    custom_url: str,
    custom_method: str,
    custom_payload: dict,
    custom_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    user=None,
) -> List[SearchResult]:
    try:
        if not custom_url:
            raise ValueError('Custom web search URL is not configured')

        method = (custom_method or 'POST').strip().upper()
        if method not in ('GET', 'POST'):
            raise ValueError(f'Unsupported HTTP method: {custom_method}')

        payload = custom_payload if isinstance(custom_payload, dict) else {}
        rendered_payload = render_payload(payload, {'query': query, 'count': count})

        # Keep the default external-provider behavior when no payload is configured.
        if not rendered_payload:
            rendered_payload = {'query': query, 'count': count}

        headers = {
            # LICENSE covers this Open WebUI user-agent identifier.
            # Do not alter, remove, obscure, or replace it except as LICENSE permits:
            # https://docs.openwebui.com/license.
            'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui) RAG Bot',
        }
        if custom_api_key:
            headers['Authorization'] = f'Bearer {custom_api_key}'
        headers = include_user_info_headers(headers, user)

        chat_id = getattr(request.state, 'chat_id', None)
        if chat_id:
            headers[FORWARD_SESSION_INFO_HEADER_CHAT_ID] = str(chat_id)

        if method == 'GET':
            response = requests.get(custom_url, headers=headers, params=rendered_payload)
        else:
            response = requests.post(custom_url, headers=headers, json=rendered_payload)

        response.raise_for_status()
        results = response.json()
        if not isinstance(results, list):
            raise ValueError('Custom search response must be a JSON array')

        if filter_list:
            results = get_filtered_results(results, filter_list)

        results = [
            SearchResult(
                link=result.get('link') or result.get('url'),
                title=result.get('title'),
                snippet=result.get('snippet') or result.get('description'),
            )
            for result in results[:count]
        ]
        log.debug('Custom search results: %s', results)
        return results
    except Exception as e:
        log.error(f'Error in Custom search: {e}')
        return []

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests
from langchain_core.documents import Document
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

if TYPE_CHECKING:
    from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)

# fastCRW's native /v1 API: /search takes `categories`, /scrape takes `deadlineMs`
# rather than a `timeout`, and self-hosted instances are keyless.
DEFAULT_CRW_API_BASE_URL = 'https://fastcrw.com/api'
CRW_RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
CRW_MAX_RETRIES = 2
CRW_MAX_DEADLINE_MS = 60000


def build_crw_url(base_url: str | None, path: str) -> str:
    base_url = (base_url or DEFAULT_CRW_API_BASE_URL).rstrip('/')
    path = path.lstrip('/')

    # Respect an explicitly versioned base URL; default to the native /v1 API.
    if base_url.endswith(('/v1', '/v2')):
        return f'{base_url}/{path}'

    return f'{base_url}/v1/{path}'


def build_crw_headers(api_key: str | None) -> dict[str, str]:
    headers = {'Content-Type': 'application/json'}
    # Self-hosted fastCRW runs keyless; only send auth when a key is configured.
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    return headers


def parse_crw_categories(categories: Any) -> list[str]:
    if not categories:
        return []

    if isinstance(categories, str):
        items = categories.split(',')
    elif isinstance(categories, (list, tuple)):
        items = categories
    else:
        return []

    return [str(item).strip() for item in items if str(item).strip()]


def get_crw_timeout_seconds(timeout: Any) -> float | None:
    if timeout in (None, ''):
        return None

    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        return None

    return timeout if timeout > 0 else None


def get_crw_deadline_ms(timeout: Any) -> int | None:
    # `deadlineMs` is capped at 60s server-side.
    timeout_seconds = get_crw_timeout_seconds(timeout)
    if timeout_seconds is None:
        return None

    return min(CRW_MAX_DEADLINE_MS, max(1000, int(timeout_seconds * 1000)))


def get_crw_client_timeout_seconds(timeout: Any, fallback: float = 60) -> float:
    # Keep the local HTTP timeout slightly above fastCRW's scrape deadline.
    return (get_crw_timeout_seconds(timeout) or fallback) + 10


def request_crw_json(
    url: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any],
    timeout: float | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    retry = Retry(
        total=CRW_MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=CRW_RETRY_STATUS_CODES,
        allowed_methods=frozenset({'POST'}),
        raise_on_status=False,
    )

    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=retry))
        session.mount('http://', HTTPAdapter(max_retries=retry))
        response = session.post(url, headers=headers, json=json, timeout=timeout, verify=verify)
        response.raise_for_status()
        return response.json()


def get_crw_result_url(result: dict[str, Any]) -> str:
    metadata = result.get('metadata') or {}
    return result.get('url') or metadata.get('sourceURL') or ''


def unwrap_crw_results(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get('data')

    # /v1 wraps results next to an optional `answer`; hosted returns the list directly.
    if isinstance(data, dict):
        data = data.get('results', data)

    # Grouped results (`sources`, Firecrawl v2): {"web": [...], "news": [...]}.
    if isinstance(data, dict):
        data = data.get('web')

    return data if isinstance(data, list) else []


def scrape_crw_url(
    crw_url: str,
    crw_api_key: str,
    url: str,
    *,
    verify_ssl: bool = True,
    timeout: Any = None,
    params: dict[str, Any] | None = None,
) -> Document | None:
    payload = {
        'url': url,
        'formats': ['markdown'],
        'onlyMainContent': True,
        **(params or {}),
    }
    deadline_ms = get_crw_deadline_ms(timeout)
    if deadline_ms is not None:
        payload['deadlineMs'] = deadline_ms

    response = request_crw_json(
        build_crw_url(crw_url, 'scrape'),
        headers=build_crw_headers(crw_api_key),
        json=payload,
        timeout=get_crw_client_timeout_seconds(timeout),
        verify=verify_ssl,
    )

    # A blocked or errored page still carries whatever partial `data` was recovered.
    if not response.get('success', True):
        log.warning(f'fastCRW scrape of {url} reported: {response.get("error")}')

    data = response.get('data') or {}
    content = data.get('markdown') or ''
    if not isinstance(content, str) or not content.strip():
        return None

    metadata = data.get('metadata') or {}
    document_metadata = {'source': get_crw_result_url(data) or url}
    if metadata.get('title'):
        document_metadata['title'] = metadata['title']
    if metadata.get('description'):
        document_metadata['description'] = metadata['description']

    return Document(page_content=content, metadata=document_metadata)


def search_crw(
    crw_url: str,
    crw_api_key: str,
    query: str,
    count: int,
    filter_list: list[str] | None = None,
    categories: Any = None,
) -> list[SearchResult]:
    from open_webui.retrieval.web.main import SearchResult, get_filtered_results

    try:
        payload: dict[str, Any] = {'query': query, 'limit': count}

        # Routes the query to curated source groups (research, github, pdf).
        parsed_categories = parse_crw_categories(categories)
        if parsed_categories:
            payload['categories'] = parsed_categories

        response = request_crw_json(
            build_crw_url(crw_url, 'search'),
            headers=build_crw_headers(crw_api_key),
            json=payload,
            timeout=count * 3 + 10,
        )
        results = unwrap_crw_results(response)

        if filter_list:
            results = get_filtered_results(results, filter_list)

        search_results = []
        for result in results[:count]:
            url = get_crw_result_url(result)
            if not url:
                continue

            search_results.append(
                SearchResult(
                    link=url,
                    title=result.get('title'),
                    snippet=result.get('description') or result.get('snippet'),
                )
            )

        log.info(f'fastCRW search results: {search_results}')
        return search_results
    except Exception as e:
        log.error(f'Error in fastCRW search: {e}')
        return []

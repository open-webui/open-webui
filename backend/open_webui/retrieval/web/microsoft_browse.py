from __future__ import annotations

import logging
import time
from typing import Any

import requests
from langchain_core.documents import Document

log = logging.getLogger(__name__)

MICROSOFT_BROWSE_URL = 'https://api.microsoft.ai/v3/browse'
# 202 = on-demand crawl in progress (retry after `retryAfter`); 5xx = transient.
BROWSE_RETRY_STATUS_CODES = {202, 429, 500, 502, 503, 504}
BROWSE_MAX_RETRIES = 2


def _get_browse_timeout_seconds(timeout: Any, fallback: float = 60) -> float:
    if timeout in (None, ''):
        return fallback
    try:
        value = float(timeout)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def _get_browse_retry_delay(data: Any, headers: Any, attempt: int) -> float:
    # browse returns retryAfter as a duration string like "60s"
    retry_after = None
    if isinstance(data, dict):
        retry_after = data.get('retryAfter')
    if not retry_after and headers:
        retry_after = headers.get('Retry-After')
    if retry_after:
        try:
            return min(10.0, max(0.0, float(str(retry_after).rstrip('s'))))
        except (TypeError, ValueError):
            pass
    return min(8.0, float(2**attempt))


def browse_microsoft_url(
    api_key: str,
    url: str,
    *,
    language: str = 'en',
    verify_ssl: bool = True,
    timeout: Any = None,
) -> Document | None:
    """Fetch a single URL's content via the Microsoft Browse API.

    Returns a langchain Document, or None if the page has no usable content
    (e.g. a 202 on-demand-crawl response that never resolved).
    """
    if hasattr(api_key, '__str__'):
        api_key = str(api_key)
    if hasattr(language, '__str__'):
        language = str(language)

    payload = {
        'url': url,
        'contentFormat': 'markdown',
        'liveCrawl': 'fallback',
        'renderDynamicPages': True,
        'language': language,
    }
    headers = {
        'host': 'api.microsoft.ai',
        'x-apikey': api_key,
        'content-type': 'application/json',
    }
    request_timeout = _get_browse_timeout_seconds(timeout)

    data: dict[str, Any] = {}
    for attempt in range(BROWSE_MAX_RETRIES + 1):
        response = requests.post(
            MICROSOFT_BROWSE_URL,
            json=payload,
            headers=headers,
            timeout=request_timeout,
            verify=verify_ssl,
        )

        if response.status_code in BROWSE_RETRY_STATUS_CODES and attempt < BROWSE_MAX_RETRIES:
            try:
                body = response.json()
            except Exception:
                body = {}
            delay = _get_browse_retry_delay(body, response.headers, attempt)
            log.warning(
                'Microsoft Browse %s returned HTTP %s; retrying in %.1fs',
                url,
                response.status_code,
                delay,
            )
            time.sleep(delay)
            continue

        response.raise_for_status()
        data = response.json()
        break

    content = data.get('content') or ''
    if not isinstance(content, str) or not content.strip():
        return None

    metadata = {'source': data.get('url') or url}
    if data.get('title'):
        metadata['title'] = data['title']

    return Document(page_content=content, metadata=metadata)

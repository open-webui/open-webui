from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_IFLOW_BASE_URL = 'https://platform.iflow.cn'
IFLOW_REQUEST_TIMEOUT = 30
_RATE_LIMIT_RETRY_DELAY = 1.0


def normalize_iflow_base_url(base_url: str | None) -> str:
    url = (base_url or DEFAULT_IFLOW_BASE_URL).strip()
    return url.rstrip('/')


def iflow_post(
    api_key: str,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    timeout: int = IFLOW_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """POST to an iFlow Search API endpoint with Bearer auth.

    Retries once on HTTP 429. Never logs the API key or Authorization header.
    """
    url = f'{normalize_iflow_base_url(base_url)}{path}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code == 429:
        log.info('iFlow API rate-limited (429); retrying after %.1fs', _RATE_LIMIT_RETRY_DELAY)
        time.sleep(_RATE_LIMIT_RETRY_DELAY)
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError('iFlow API returned a non-object JSON response')
    return body


def unwrap_iflow_data(body: dict[str, Any]) -> Any:
    if 'data' in body:
        return body.get('data')
    return body


def first_str(item: dict[str, Any], *keys: str, default: str = '') -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return default

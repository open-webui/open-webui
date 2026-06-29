import logging
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import requests
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

log = logging.getLogger(__name__)

DEFAULT_MICROSOFT_WEB_IQ_API_BASE_URL = 'https://api.microsoft.ai/v3'
MICROSOFT_BROWSE_RETRY_STATUS_CODES = {202, 429, 500, 502, 503, 504}
MICROSOFT_BROWSE_MAX_RETRIES = 2


class MicrosoftWebIQLoader(BaseLoader):
    def __init__(
        self,
        urls: str | list[str],
        api_base_url: str,
        api_key: str,
        language: str = 'en',
        verify_ssl: bool = True,
        timeout: Any = None,
        continue_on_failure: bool = True,
    ) -> None:
        self.urls = urls if isinstance(urls, list) else [urls]
        self.api_base_url = (api_base_url or DEFAULT_MICROSOFT_WEB_IQ_API_BASE_URL).rstrip('/')
        self.api_key = api_key
        self.language = language
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.continue_on_failure = continue_on_failure

    def lazy_load(self) -> Iterator[Document]:
        for url in self.urls:
            try:
                doc = self._browse_url(url)
                if doc is not None:
                    yield doc
            except Exception as e:
                if self.continue_on_failure:
                    log.warning(f'Error browsing {url} with Microsoft Web IQ: {e}')
                else:
                    raise e

    def _browse_url(self, url: str) -> Document | None:
        headers = {
            'host': urlparse(self.api_base_url).netloc or 'api.microsoft.ai',
            'x-apikey': self.api_key,
            'content-type': 'application/json',
        }
        payload = {
            'url': url,
            'contentFormat': 'markdown',
            'liveCrawl': 'fallback',
            'renderDynamicPages': True,
            'language': self.language,
        }
        try:
            request_timeout = float(self.timeout)
        except (TypeError, ValueError):
            request_timeout = 60
        request_timeout = request_timeout if request_timeout > 0 else 60

        data: dict[str, Any] = {}
        for attempt in range(MICROSOFT_BROWSE_MAX_RETRIES + 1):
            response = requests.post(
                f'{self.api_base_url}/browse',
                json=payload,
                headers=headers,
                timeout=request_timeout,
                verify=self.verify_ssl,
            )

            if response.status_code in MICROSOFT_BROWSE_RETRY_STATUS_CODES and attempt < MICROSOFT_BROWSE_MAX_RETRIES:
                try:
                    body = response.json()
                except Exception:
                    body = {}
                retry_after = body.get('retryAfter') if isinstance(body, dict) else None
                retry_after = retry_after or response.headers.get('Retry-After')
                try:
                    delay = min(10.0, max(0.0, float(str(retry_after).rstrip('s'))))
                except (TypeError, ValueError):
                    delay = min(8.0, float(2**attempt))
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

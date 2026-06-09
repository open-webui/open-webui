from __future__ import annotations

import logging
from typing import Iterator, List, Union

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from open_webui.retrieval.web.iflow_client import (
    IFLOW_REQUEST_TIMEOUT,
    first_str,
    iflow_post,
    normalize_iflow_base_url,
    unwrap_iflow_data,
)

log = logging.getLogger(__name__)


def _extract_fetch_content(data: object) -> tuple[str, str, str]:
    if not isinstance(data, dict):
        return '', '', ''

    url = first_str(data, 'url', 'link', 'source')
    title = first_str(data, 'title')
    content = first_str(data, 'content', 'text', 'markdown')
    return url, title, content


class IFlowLoader(BaseLoader):
    """Fetch web page content from URLs using the iFlow webFetch API."""

    def __init__(
        self,
        urls: Union[str, List[str]],
        api_key: str,
        base_url: str | None = None,
        continue_on_failure: bool = True,
        timeout: int = IFLOW_REQUEST_TIMEOUT,
    ) -> None:
        if not urls:
            raise ValueError('At least one URL must be provided.')

        self.api_key = api_key
        self.base_url = normalize_iflow_base_url(base_url)
        self.urls = urls if isinstance(urls, list) else [urls]
        self.continue_on_failure = continue_on_failure
        self.timeout = timeout

    def _fetch_url(self, url: str) -> Document | None:
        body = iflow_post(
            self.api_key,
            self.base_url,
            '/api/search/webFetch',
            {'url': url},
            timeout=self.timeout,
        )
        data = unwrap_iflow_data(body)
        fetched_url, title, content = _extract_fetch_content(data if isinstance(data, dict) else body)
        source = fetched_url or url
        if not content:
            log.warning('No content fetched from %s', source)
            return None

        metadata = {'source': source}
        if title:
            metadata['title'] = title
        return Document(page_content=content, metadata=metadata)

    def lazy_load(self) -> Iterator[Document]:
        for url in self.urls:
            try:
                document = self._fetch_url(url)
                if document:
                    yield document
            except Exception as e:
                if self.continue_on_failure:
                    log.error('Failed to fetch content from %s: %s', url, e)
                else:
                    raise

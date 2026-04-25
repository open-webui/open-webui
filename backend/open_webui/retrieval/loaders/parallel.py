import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import requests
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

log = logging.getLogger(__name__)

PARALLEL_API_BASE = 'https://api.parallel.ai'
PARALLEL_REQUEST_TIMEOUT = (5, 15)  # (connect, read) seconds
PARALLEL_EXTRACT_BATCH_SIZE = 10  # number of extracts so we dont hit timeout


class ParallelLoader(BaseLoader):
    """Extract web page content from URLs using Parallel's /v1/extract API.

    Docs: https://docs.parallel.ai/api-reference/extract/extract

    Parallel accepts up to 20 URLs per request and returns full-page markdown.
    URLs are batched in groups of 10 for better parallelism

    To increase performance, if more than extract batch size urls are requested, we use a thread pool
    to fetch them in parallel.
    """

    def __init__(
        self,
        urls: list[str],
        api_key: str,
        max_chars_per_result: int | None = None,
        continue_on_failure: bool = True,
    ):
        self.urls = urls
        self.api_key = api_key
        self.max_chars_per_result = max_chars_per_result
        self.continue_on_failure = continue_on_failure

    def lazy_load(self) -> Iterator[Document]:
        if not self.urls:
            return

        batches = [
            self.urls[i : i + PARALLEL_EXTRACT_BATCH_SIZE]
            for i in range(0, len(self.urls), PARALLEL_EXTRACT_BATCH_SIZE)
        ]

        if len(batches) == 1:
            yield from self._extract_batch(batches[0])
            return

        with ThreadPoolExecutor(max_workers=len(batches)) as pool:
            for batch_docs in pool.map(self._extract_batch, batches):
                yield from batch_docs

    def _extract_batch(self, batch: list[str]) -> list[Document]:
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'open-webui',
        }

        full_content_settings: dict | bool = True
        if self.max_chars_per_result is not None:
            full_content_settings = {'max_chars_per_result': self.max_chars_per_result}

        payload = {
            'urls': batch,
            'advanced_settings': {'full_content': full_content_settings},
        }

        log.info(f'Running Parallel extract for {len(batch)} urls')
        try:
            response = requests.post(
                f'{PARALLEL_API_BASE}/v1/extract',
                headers=headers,
                json=payload,
                timeout=PARALLEL_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as e:
            body = getattr(e.response, 'text', '')
            log.error(f'Parallel extract HTTP error: {e}; body={body[:500]}')
            if self.continue_on_failure:
                return []
            raise
        except Exception as e:
            log.error(f'Error extracting via Parallel: {e}')
            if self.continue_on_failure:
                return []
            raise

        docs: list[Document] = []
        for result in data.get('results', []) or []:
            url = result.get('url')
            if not url:
                continue
            content = result.get('full_content')
            if not content:
                excerpts = result.get('excerpts') or []
                content = '\n\n'.join(excerpts)
            if not content:
                continue
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        'source': url,
                        'title': result.get('title') or url,
                    },
                )
            )
        return docs

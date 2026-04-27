"""Tests for `SafeFireCrawlLoader` in `open_webui.retrieval.web.utils`.

The loader is expected to:

- Yield a `Document` for every URL that `scrape_firecrawl_url` returns successfully;
- Skip URLs for which `scrape_firecrawl_url` returns `None` (the helper signals "no markdown content" by returning
  `None`) without raising;
- When `continue_on_failure` is `True` (the default), continue with the rest of the batch after a per-URL exception,
  log a warning that identifies which URL failed, and not let earlier or later URLs in the batch be lost;
- When `continue_on_failure` is `False`, propagate the first per-URL exception.

Tests mock `scrape_firecrawl_url` so they need no HTTP server, no Firecrawl SDK and no network access.
"""

from unittest.mock import patch

import pytest
import requests
from langchain_core.documents import Document

from open_webui.retrieval.web.utils import SafeFireCrawlLoader


URLS = [
    'https://example.com/page-1',
    'https://example.com/page-2',
    'https://example.com/page-3',
    'https://example.com/page-4',
    'https://example.com/page-5',
]


def _make_doc(url: str) -> Document:
    return Document(page_content=f'# content for {url}', metadata={'source': url})


def _http_error(url: str, status: int = 403) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    response.url = 'https://api.firecrawl.dev/v2/scrape'
    response.reason = 'Forbidden' if status == 403 else 'Error'
    return requests.HTTPError(f'{status} Client Error: {response.reason} for url: {response.url}', response=response)


def _build_loader(**kwargs) -> SafeFireCrawlLoader:
    defaults = {
        'web_paths': URLS,
        'api_key': 'fc-test',
        'api_url': 'https://api.firecrawl.dev',
        'verify_ssl': True,
        'continue_on_failure': True,
    }
    defaults.update(kwargs)
    return SafeFireCrawlLoader(**defaults)


async def _collect(async_iter) -> list:
    return [item async for item in async_iter]


class TestLazyLoad:
    """Synchronous `SafeFireCrawlLoader.lazy_load`"""

    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    def test_yields_all_documents_when_all_urls_succeed(self, mock_scrape):
        mock_scrape.side_effect = [_make_doc(url) for url in URLS]
        loader = _build_loader()
        docs = list(loader.lazy_load())
        assert [doc.metadata['source'] for doc in docs] == URLS
        assert mock_scrape.call_count == len(URLS)

    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    def test_skips_urls_that_return_none(self, mock_scrape):
        """`scrape_firecrawl_url` returns None for empty markdown; loader must silently skip those without raising."""
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            None,
            _make_doc(URLS[2]),
            None,
            _make_doc(URLS[4]),
        ]
        loader = _build_loader()
        docs = list(loader.lazy_load())
        assert [doc.metadata['source'] for doc in docs] == [URLS[0], URLS[2], URLS[4]]

    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    def test_continues_after_per_url_error_when_continue_on_failure_true(self, mock_scrape):
        """Regression: with continue_on_failure=True, a per-URL HTTP error must not abort the rest of the batch."""
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            _make_doc(URLS[1]),
            _http_error(URLS[2], status=403),
            _make_doc(URLS[3]),
            _make_doc(URLS[4]),
        ]
        loader = _build_loader(continue_on_failure=True)
        docs = list(loader.lazy_load())
        assert [doc.metadata['source'] for doc in docs] == [URLS[0], URLS[1], URLS[3], URLS[4]]
        assert mock_scrape.call_count == len(URLS)

    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    def test_warning_message_includes_failing_url(self, mock_scrape, caplog):
        """The warning emitted on a per-URL failure must identify which URL failed"""
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            _http_error(URLS[1], status=403),
            _make_doc(URLS[2]),
        ]
        loader = _build_loader(web_paths=URLS[:3], continue_on_failure=True)
        with caplog.at_level('WARNING', logger='open_webui.retrieval.web.utils'):
            list(loader.lazy_load())
        warning_messages = [record.getMessage() for record in caplog.records if record.levelname == 'WARNING']
        warnings_found = [URLS[1] in message for message in warning_messages]
        assert len(warnings_found) == 1, (
            f'Expected the failing URL {URLS[1]!r} in a WARNING log line, got: {warning_messages!r}'
        )

    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    def test_raises_when_continue_on_failure_is_false(self, mock_scrape):
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            _http_error(URLS[1], status=403),
            _make_doc(URLS[2]),
        ]
        loader = _build_loader(web_paths=URLS[:3], continue_on_failure=False)
        with pytest.raises(requests.HTTPError):
            list(loader.lazy_load())

    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    def test_waits_for_rate_limit_before_each_scrape(self, mock_scrape):
        """Each URL must trigger the rate limiter before the scrape, mirroring SafePlaywrightURLLoader"""
        events = []

        def wait_side_effect():
            events.append('wait')

        def scrape_side_effect(api_url, api_key, url, **kwargs):
            events.append('scrape')
            return _make_doc(url)

        mock_scrape.side_effect = scrape_side_effect
        loader = _build_loader(web_paths=URLS[:3])
        with patch.object(loader, '_sync_wait_for_rate_limit', side_effect=wait_side_effect):
            list(loader.lazy_load())
        assert events == ['wait', 'scrape'] * 3, f'Expected wait-then-scrape per URL; got {events!r}'


class TestAlazyLoad:
    """Async `SafeFireCrawlLoader.alazy_load` -- same contract as the sync version."""

    @pytest.mark.asyncio
    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    async def test_yields_all_documents_when_all_urls_succeed(self, mock_scrape):
        mock_scrape.side_effect = [_make_doc(url) for url in URLS]
        loader = _build_loader()
        docs = await _collect(loader.alazy_load())
        assert [doc.metadata['source'] for doc in docs] == URLS

    @pytest.mark.asyncio
    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    async def test_continues_after_per_url_error_when_continue_on_failure_true(self, mock_scrape):
        """Async equivalent of the sync regression: a per-URL HTTP error must not abort the rest of the batch"""
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            _make_doc(URLS[1]),
            _http_error(URLS[2], status=403),
            _make_doc(URLS[3]),
            _make_doc(URLS[4]),
        ]
        loader = _build_loader(continue_on_failure=True)
        docs = await _collect(loader.alazy_load())
        assert [doc.metadata['source'] for doc in docs] == [URLS[0], URLS[1], URLS[3], URLS[4]]

    @pytest.mark.asyncio
    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    async def test_warning_message_includes_failing_url(self, mock_scrape, caplog):
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            _http_error(URLS[1], status=403),
            _make_doc(URLS[2]),
        ]
        loader = _build_loader(web_paths=URLS[:3], continue_on_failure=True)
        with caplog.at_level('WARNING', logger='open_webui.retrieval.web.utils'):
            await _collect(loader.alazy_load())
        warning_messages = [record.getMessage() for record in caplog.records if record.levelname == 'WARNING']
        warnings_found = [URLS[1] in message for message in warning_messages]
        assert warnings_found, f'Expected the failing URL {URLS[1]!r} in a WARNING log line, got: {warning_messages!r}'

    @pytest.mark.asyncio
    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    async def test_raises_when_continue_on_failure_is_false(self, mock_scrape):
        mock_scrape.side_effect = [
            _make_doc(URLS[0]),
            _http_error(URLS[1], status=403),
            _make_doc(URLS[2]),
        ]
        loader = _build_loader(web_paths=URLS[:3], continue_on_failure=False)
        with pytest.raises(requests.HTTPError):
            await _collect(loader.alazy_load())

    @pytest.mark.asyncio
    @patch('open_webui.retrieval.web.utils.scrape_firecrawl_url')
    async def test_waits_for_rate_limit_before_each_scrape(self, mock_scrape):
        """Async equivalent: each URL must await the rate limiter before scraping."""
        events = []

        async def wait_side_effect():
            events.append('wait')

        def scrape_side_effect(api_url, api_key, url, **kwargs):
            events.append('scrape')
            return _make_doc(url)

        mock_scrape.side_effect = scrape_side_effect
        loader = _build_loader(web_paths=URLS[:3])
        with patch.object(loader, '_wait_for_rate_limit', side_effect=wait_side_effect):
            await _collect(loader.alazy_load())
        assert events == ['wait', 'scrape'] * 3, f'Expected wait-then-scrape per URL; got {events!r}'

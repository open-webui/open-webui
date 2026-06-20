from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

# Import the fastCRW module directly by file path. This keeps the unit test
# self-contained: it avoids executing open_webui's CLI-heavy package __init__
# (typer/uvicorn/...) just to exercise a pure-HTTP helper. When the full
# open_webui environment IS installed, `import open_webui.retrieval.web.crw`
# works identically; this loader is only a lightweight fallback.
_CRW_PATH = Path(__file__).resolve().parents[3] / 'retrieval' / 'web' / 'crw.py'


def _load_crw():
    try:
        from open_webui.retrieval.web import crw as _crw

        return _crw
    except Exception:
        pass

    # Stub the deferred `open_webui.retrieval.web.main` dependency so search_crw
    # can resolve SearchResult / get_filtered_results without the heavy package.
    main_mod = types.ModuleType('open_webui.retrieval.web.main')

    class SearchResult:
        def __init__(self, link=None, title=None, snippet=None):
            self.link = link
            self.title = title
            self.snippet = snippet

    def get_filtered_results(results, filter_list):
        return results

    main_mod.SearchResult = SearchResult
    main_mod.get_filtered_results = get_filtered_results
    sys.modules.setdefault('open_webui', types.ModuleType('open_webui'))
    sys.modules.setdefault('open_webui.retrieval', types.ModuleType('open_webui.retrieval'))
    sys.modules.setdefault('open_webui.retrieval.web', types.ModuleType('open_webui.retrieval.web'))
    sys.modules['open_webui.retrieval.web.main'] = main_mod

    spec = importlib.util.spec_from_file_location('open_webui.retrieval.web.crw', _CRW_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


crw = _load_crw()


class FakeResponse:
    """Minimal stand-in for a requests.Response."""

    def __init__(self, json_data, status_code=200, headers=None):
        self._json = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def json(self):
        return self._json


def _capture_request(monkeypatch, json_data):
    """Patch requests.request and record the call kwargs."""
    captured = {}

    def fake_request(method, url, **kwargs):
        captured['method'] = method
        captured['url'] = url
        captured.update(kwargs)
        return FakeResponse(json_data)

    monkeypatch.setattr(crw.requests, 'request', fake_request)
    return captured


def test_keyless_headers_omit_authorization():
    # Self-hosted fastCRW runs keyless; no Authorization header without a key.
    headers = crw.build_crw_headers(None)
    assert 'Authorization' not in headers
    assert headers['Content-Type'] == 'application/json'

    headers_empty = crw.build_crw_headers('')
    assert 'Authorization' not in headers_empty


def test_headers_include_bearer_when_key_set():
    headers = crw.build_crw_headers('secret-key')
    assert headers['Authorization'] == 'Bearer secret-key'


def test_search_omits_authorization_when_keyless(monkeypatch):
    captured = _capture_request(monkeypatch, {'data': []})

    crw.search_crw('https://fastcrw.com/api', '', 'hello world', count=3)

    assert 'Authorization' not in captured['headers']


def test_search_posts_categories_when_configured(monkeypatch):
    captured = _capture_request(monkeypatch, {'data': []})

    crw.search_crw(
        'https://fastcrw.com/api',
        'k',
        'transformers',
        count=5,
        categories='research, github , pdf',
    )

    body = captured['json']
    assert body['query'] == 'transformers'
    assert body['limit'] == 5
    # Comma-separated categories are parsed into a clean list (the fastCRW
    # differentiator that the generic Firecrawl path cannot send).
    assert body['categories'] == ['research', 'github', 'pdf']


def test_search_omits_categories_when_not_configured(monkeypatch):
    captured = _capture_request(monkeypatch, {'data': []})

    crw.search_crw('https://fastcrw.com/api', '', 'q', count=2)

    body = captured['json']
    assert 'categories' not in body
    assert 'sources' not in body


def test_search_posts_sources_when_configured(monkeypatch):
    captured = _capture_request(monkeypatch, {'data': []})

    crw.search_crw(
        'https://fastcrw.com/api',
        '',
        'q',
        count=2,
        sources=['web', 'news'],
    )

    assert captured['json']['sources'] == ['web', 'news']


def test_search_parses_flat_results(monkeypatch):
    _capture_request(
        monkeypatch,
        {
            'data': [
                {
                    'url': 'https://example.com/a',
                    'title': 'A title',
                    'description': 'A snippet',
                }
            ]
        },
    )

    results = crw.search_crw('https://fastcrw.com/api', '', 'q', count=3)

    assert len(results) == 1
    assert results[0].link == 'https://example.com/a'
    assert results[0].title == 'A title'
    assert results[0].snippet == 'A snippet'


def test_scrape_unwraps_success_data_markdown(monkeypatch):
    captured = _capture_request(
        monkeypatch,
        {
            'success': True,
            'data': {
                'markdown': '# Hello\n\nworld',
                'metadata': {
                    'title': 'Hello',
                    'description': 'A page',
                    'sourceURL': 'https://example.com/page',
                },
            },
        },
    )

    doc = crw.scrape_crw_url('https://fastcrw.com/api', '', 'https://example.com/page')

    assert doc is not None
    assert doc.page_content == '# Hello\n\nworld'
    assert doc.metadata['source'] == 'https://example.com/page'
    assert doc.metadata['title'] == 'Hello'
    assert doc.metadata['description'] == 'A page'
    # Firecrawl-shaped scrape body.
    assert captured['json']['formats'] == ['markdown']
    assert captured['json']['onlyMainContent'] is True


def test_scrape_returns_none_on_empty_markdown(monkeypatch):
    _capture_request(monkeypatch, {'success': True, 'data': {'markdown': '   '}})

    doc = crw.scrape_crw_url('https://fastcrw.com/api', '', 'https://example.com/x')

    assert doc is None


def test_scrape_keyless_headers(monkeypatch):
    captured = _capture_request(
        monkeypatch,
        {'success': True, 'data': {'markdown': 'content'}},
    )

    crw.scrape_crw_url('https://fastcrw.com/api', '', 'https://example.com/x')

    assert 'Authorization' not in captured['headers']


def test_build_url_appends_v1():
    assert (
        crw.build_crw_url('https://fastcrw.com/api', 'search')
        == 'https://fastcrw.com/api/v1/search'
    )
    # Does not double up when /v1 already present.
    assert (
        crw.build_crw_url('https://fastcrw.com/api/v1', 'scrape')
        == 'https://fastcrw.com/api/v1/scrape'
    )


def test_parse_categories_handles_string_and_list():
    assert crw.parse_crw_categories('a, b ,c') == ['a', 'b', 'c']
    assert crw.parse_crw_categories(['x', ' y ']) == ['x', 'y']
    assert crw.parse_crw_categories('') == []
    assert crw.parse_crw_categories(None) == []


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(pytest.main([__file__, '-q']))

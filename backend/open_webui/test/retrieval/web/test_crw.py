from __future__ import annotations

from unittest.mock import MagicMock, patch

from open_webui.retrieval.web.crw import build_crw_url, scrape_crw_url, search_crw
from open_webui.retrieval.web.main import SearchResult


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_build_crw_url_defaults_to_cloud_v1() -> None:
    assert build_crw_url(None, 'search') == 'https://fastcrw.com/api/v1/search'


def test_build_crw_url_allows_self_host_override() -> None:
    assert build_crw_url('http://localhost:3000', 'scrape') == 'http://localhost:3000/v1/scrape'


def test_build_crw_url_does_not_double_version() -> None:
    assert build_crw_url('http://localhost:3000/v1', 'map') == 'http://localhost:3000/v1/map'


def test_search_crw_returns_search_results() -> None:
    payload = {
        'success': True,
        'data': [
            {
                'title': 'Example',
                'url': 'https://example.com',
                'description': 'An example result',
            }
        ],
    }

    with patch('open_webui.retrieval.web.crw.requests.request', return_value=_mock_response(payload)) as mock_request:
        results = search_crw('https://fastcrw.com/api', 'test-key', 'example', count=5)

    assert mock_request.called
    method, url = mock_request.call_args.args
    assert method == 'POST'
    assert url == 'https://fastcrw.com/api/v1/search'

    kwargs = mock_request.call_args.kwargs
    assert kwargs['headers']['Authorization'] == 'Bearer test-key'
    assert kwargs['json'] == {'query': 'example', 'limit': 5}

    assert results == [
        SearchResult(
            link='https://example.com',
            title='Example',
            snippet='An example result',
        )
    ]


def test_search_crw_respects_count_limit() -> None:
    payload = {
        'success': True,
        'data': [{'title': f't{i}', 'url': f'https://example.com/{i}', 'description': ''} for i in range(10)],
    }

    with patch('open_webui.retrieval.web.crw.requests.request', return_value=_mock_response(payload)):
        results = search_crw('https://fastcrw.com/api', 'test-key', 'example', count=3)

    assert len(results) == 3


def test_search_crw_returns_empty_list_on_error() -> None:
    with patch('open_webui.retrieval.web.crw.requests.request', side_effect=Exception('boom')):
        results = search_crw('https://fastcrw.com/api', 'test-key', 'example', count=5)

    assert results == []


def test_scrape_crw_url_builds_document() -> None:
    payload = {
        'success': True,
        'data': {
            'markdown': '# Hello',
            'metadata': {'title': 'Hello', 'description': 'A page', 'sourceURL': 'https://example.com'},
        },
    }

    with patch('open_webui.retrieval.web.crw.requests.request', return_value=_mock_response(payload)) as mock_request:
        doc = scrape_crw_url('https://fastcrw.com/api', 'test-key', 'https://example.com')

    method, url = mock_request.call_args.args
    assert method == 'POST'
    assert url == 'https://fastcrw.com/api/v1/scrape'

    assert doc is not None
    assert doc.page_content == '# Hello'
    assert doc.metadata['source'] == 'https://example.com'
    assert doc.metadata['title'] == 'Hello'
    assert doc.metadata['description'] == 'A page'


def test_scrape_crw_url_returns_none_for_empty_content() -> None:
    payload = {'success': True, 'data': {'markdown': '   '}}

    with patch('open_webui.retrieval.web.crw.requests.request', return_value=_mock_response(payload)):
        doc = scrape_crw_url('https://fastcrw.com/api', 'test-key', 'https://example.com')

    assert doc is None

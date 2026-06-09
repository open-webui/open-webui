from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

# Minimal stubs so tests do not require the full Open WebUI backend environment.
for _mod in (
    'redis',
    'langchain_community',
    'langchain_community.document_loaders',
    'langchain_community.document_loaders.base',
    'aiohttp',
    'aiohttp.resolver',
    'open_webui.config',
):
    sys.modules.setdefault(_mod, MagicMock())


def _is_string_allowed(hostnames, filter_list):
    if not filter_list:
        return True
    for hostname in hostnames:
        for entry in filter_list:
            if entry and entry in hostname:
                return True
    return False


_misc_mock = MagicMock()
_misc_mock.is_string_allowed = _is_string_allowed
sys.modules.setdefault('open_webui.utils', MagicMock())
sys.modules.setdefault('open_webui.utils.misc', _misc_mock)

_utils_mock = MagicMock()
_utils_mock.resolve_hostname = lambda _domain: ([], [])
sys.modules.setdefault('open_webui.retrieval.web.utils', _utils_mock)

from open_webui.retrieval.loaders.iflow import IFlowLoader
from open_webui.retrieval.web.iflow import search_iflow

WEB_SEARCH_RESPONSE = {
    'data': {
        'organic': [
            {
                'title': 'Great Wall of China - Wikipedia',
                'link': 'https://en.wikipedia.org/wiki/Great_Wall_of_China',
                'snippet': (
                    'The Great Wall of China is a series of fortifications built across '
                    'the historical northern borders of ancient Chinese states and Imperial China.'
                ),
            }
        ]
    }
}

WEB_FETCH_RESPONSE = {
    'data': {
        'title': 'Golf - Wikipedia',
        'url': 'https://en.wikipedia.org/wiki/Golf',
        'content': (
            'Golf is a club-and-ball sport in which players use various clubs to hit balls '
            'into a series of holes on a course in as few strokes as possible.'
        ),
    }
}


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.raise_for_status.side_effect = None
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


@patch('open_webui.retrieval.web.iflow_client.requests.post')
def test_search_iflow_normalizes_results(mock_post):
    mock_post.return_value = _mock_response(WEB_SEARCH_RESPONSE)

    results = search_iflow('test-key', 'https://platform.iflow.cn', 'great wall', 3)

    assert len(results) == 1
    assert results[0].link == 'https://en.wikipedia.org/wiki/Great_Wall_of_China'
    assert 'Great Wall' in (results[0].title or '')
    assert results[0].snippet
    mock_post.assert_called_once()
    headers = mock_post.call_args.kwargs['headers']
    assert headers['Authorization'].startswith('Bearer ')
    assert headers['Content-Type'] == 'application/json'


@patch('open_webui.retrieval.web.iflow_client.requests.post')
def test_search_iflow_respects_count(mock_post):
    payload = {
        'data': {
            'organic': [
                {'title': f'Result {i}', 'link': f'https://example.com/{i}', 'snippet': f'snippet {i}'}
                for i in range(5)
            ]
        }
    }
    mock_post.return_value = _mock_response(payload)

    results = search_iflow('test-key', 'https://platform.iflow.cn', 'query', 2)
    assert len(results) == 2


@patch('open_webui.retrieval.web.iflow_client.requests.post')
def test_search_iflow_domain_filter(mock_post):
    payload = {
        'data': {
            'organic': [
                {'title': 'Allowed', 'link': 'https://wikipedia.org/wiki/Test', 'snippet': 'ok'},
                {'title': 'Blocked', 'link': 'https://blocked.example.com/page', 'snippet': 'no'},
            ]
        }
    }
    mock_post.return_value = _mock_response(payload)

    results = search_iflow(
        'test-key',
        'https://platform.iflow.cn',
        'query',
        5,
        filter_list=['wikipedia.org'],
    )
    assert len(results) == 1
    assert 'wikipedia.org' in results[0].link


@patch('open_webui.retrieval.web.iflow_client.requests.post')
def test_search_iflow_http_error_does_not_leak_key(mock_post):
    mock_post.return_value = _mock_response({'error': 'unauthorized'}, status_code=401)

    with pytest.raises(Exception) as exc:
        search_iflow('super-secret-key', 'https://platform.iflow.cn', 'query', 3)

    assert 'super-secret-key' not in str(exc.value)


@patch('open_webui.retrieval.web.iflow_client.requests.post')
def test_iflow_loader_returns_document(mock_post):
    mock_post.return_value = _mock_response(WEB_FETCH_RESPONSE)

    loader = IFlowLoader(
        urls=['https://en.wikipedia.org/wiki/Golf'],
        api_key='test-key',
        base_url='https://platform.iflow.cn',
    )
    docs = list(loader.lazy_load())

    assert len(docs) == 1
    assert 'Golf is a club-and-ball sport' in docs[0].page_content
    assert docs[0].metadata['source'] == 'https://en.wikipedia.org/wiki/Golf'
    assert docs[0].metadata['title'] == 'Golf - Wikipedia'


@patch('open_webui.retrieval.web.iflow_client.requests.post')
def test_iflow_loader_continues_on_failure(mock_post):
    mock_post.side_effect = requests.RequestException('network error')

    loader = IFlowLoader(
        urls=['https://example.com/broken'],
        api_key='test-key',
        base_url='https://platform.iflow.cn',
        continue_on_failure=True,
    )
    docs = list(loader.lazy_load())
    assert docs == []


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('IFLOW_API_KEY'), reason='IFLOW_API_KEY not set')
def test_search_iflow_live():
    api_key = os.environ['IFLOW_API_KEY']
    results = search_iflow(api_key, 'https://platform.iflow.cn', 'Open WebUI', 3)
    assert len(results) > 0
    assert all(r.link for r in results)


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('IFLOW_API_KEY'), reason='IFLOW_API_KEY not set')
def test_iflow_loader_live():
    api_key = os.environ['IFLOW_API_KEY']
    loader = IFlowLoader(
        urls=['https://en.wikipedia.org/wiki/Golf'],
        api_key=api_key,
        base_url='https://platform.iflow.cn',
    )
    docs = list(loader.lazy_load())
    assert len(docs) >= 1
    assert len(docs[0].page_content) > 0

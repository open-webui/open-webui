import pytest

from open_webui.retrieval.web import utils as web_utils


class FakeResponse:
    def __init__(self, url, status_code=200, headers=None):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self.text = 'ok'
        self.content = b'ok'
        self.closed = False

    @property
    def is_redirect(self):
        return self.status_code in {301, 302, 303, 307, 308}

    @property
    def is_permanent_redirect(self):
        return self.status_code in {301, 308}

    def close(self):
        self.closed = True

    def raise_for_status(self):
        pass


def _mock_public_dns(monkeypatch):
    def fake_resolve_hostname(hostname):
        addresses = {
            'example.com': (['93.184.216.34'], []),
            'example.org': (['93.184.216.34'], []),
            '127.0.0.1': (['127.0.0.1'], []),
            'localhost': (['127.0.0.1'], []),
        }
        return addresses[hostname]

    monkeypatch.setattr(web_utils, 'ENABLE_RAG_LOCAL_WEB_FETCH', False)
    monkeypatch.setattr(web_utils, 'WEB_FETCH_FILTER_LIST', [])
    monkeypatch.setattr(web_utils, 'resolve_hostname', fake_resolve_hostname)


def test_safe_requests_get_blocks_redirect_to_private_network(monkeypatch):
    _mock_public_dns(monkeypatch)
    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        if url == 'https://example.com/start':
            return FakeResponse(url, 302, {'Location': 'http://127.0.0.1/admin'})
        raise AssertionError(f'private redirect target was requested: {url}')

    monkeypatch.setattr(web_utils.requests, 'get', fake_get)

    with pytest.raises(ValueError):
        web_utils.safe_requests_get('https://example.com/start')

    assert requested_urls == ['https://example.com/start']


def test_safe_requests_get_allows_public_redirect(monkeypatch):
    _mock_public_dns(monkeypatch)

    def fake_get(url, **kwargs):
        if url == 'https://example.com/start':
            return FakeResponse(url, 302, {'Location': 'https://example.org/final'})
        if url == 'https://example.org/final':
            return FakeResponse(url, 200)
        raise AssertionError(f'unexpected URL requested: {url}')

    monkeypatch.setattr(web_utils.requests, 'get', fake_get)

    response = web_utils.safe_requests_get('https://example.com/start')

    assert response.url == 'https://example.org/final'
    assert response.status_code == 200

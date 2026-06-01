from types import SimpleNamespace

import pytest
from open_webui.env import AIOHTTP_CLIENT_ALLOW_REDIRECTS
from open_webui.retrieval.web.utils import SafeWebBaseLoader


class _FakeResponse:
    def __init__(self, text: str = 'ok'):
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def text(self):
        return self._text


class _FakeClientSession:
    last_request = None

    def __init__(self, trust_env=False):
        self.trust_env = trust_env

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, **kwargs):
        type(self).last_request = {'url': url, 'kwargs': kwargs}
        return _FakeResponse()


@pytest.mark.asyncio
async def test_safe_web_base_loader_fetch_merges_redirect_kwargs(monkeypatch):
    loader = SafeWebBaseLoader.__new__(SafeWebBaseLoader)
    loader.trust_env = False
    loader.raise_for_status = True
    loader.session = SimpleNamespace(
        headers={'x-test': '1'},
        cookies=SimpleNamespace(get_dict=lambda: {'cookie': 'value'}),
        verify=True,
    )
    loader.requests_kwargs = {'allow_redirects': AIOHTTP_CLIENT_ALLOW_REDIRECTS}

    monkeypatch.setattr('open_webui.retrieval.web.utils.aiohttp.ClientSession', _FakeClientSession)

    text = await SafeWebBaseLoader._fetch(loader, 'https://example.com')

    assert text == 'ok'
    assert _FakeClientSession.last_request is not None
    assert _FakeClientSession.last_request['url'] == 'https://example.com'
    assert _FakeClientSession.last_request['kwargs']['allow_redirects'] is AIOHTTP_CLIENT_ALLOW_REDIRECTS
    assert _FakeClientSession.last_request['kwargs']['headers'] == {'x-test': '1'}
    assert _FakeClientSession.last_request['kwargs']['cookies'] == {'cookie': 'value'}
    assert 'ssl' in _FakeClientSession.last_request['kwargs']

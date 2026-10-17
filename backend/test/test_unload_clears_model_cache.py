"""
Regression test for https://github.com/open-webui/open-webui/issues/31831

After a successful model unload, the provider model-list cache must be
invalidated. Otherwise the next GET /api/models still reports the model as
loaded (stale ``expires_at``) until the cache TTL expires, and the model
picker keeps showing the loaded indicator and Eject control.
"""

import types

import pytest
from open_webui.internal.db import get_async_db
from open_webui.main import ModelUnloadForm, unload_model
from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.routers import ollama

ADMIN_ID = 'admin-1'
MODEL_ID = 'test-model:latest'


def _fake_request():
    return types.SimpleNamespace(
        scope={},
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(
                redis=None,
                OLLAMA_MODELS={MODEL_ID: {'model': MODEL_ID, 'urls': [0]}},
                OPENAI_MODELS={},
                MODELS={},
                BASE_MODELS=[],
            )
        ),
    )


@pytest.fixture
def ollama_http(monkeypatch):
    """Stand-in for the Ollama provider: /api/tags always lists the model,
    /api/ps reports it loaded until the test unloads it."""
    state = {'loaded': True}

    async def fake_send_get(request, url, key=None, user=None, config=None):
        if url.endswith('/api/tags'):
            return {'models': [{'model': MODEL_ID, 'name': 'test-model'}]}
        if url.endswith('/api/ps'):
            if state['loaded']:
                return {'models': [{'model': MODEL_ID, 'expires_at': '2030-01-01T00:00:00Z'}]}
            return {'models': []}
        return {}

    monkeypatch.setattr(ollama, 'send_get_request', fake_send_get)
    return state


class _FakeOllamaResponse:
    ok = True

    async def text(self):
        return ''

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeAiohttpSession:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def post(self, url, **kwargs):
        return _FakeOllamaResponse()


async def _set_config(**values):
    async with get_async_db() as session:
        for key, value in values.items():
            session.add(Config(key=key, value=value, updated_at=0))
        await session.commit()


async def test_unload_invalidates_provider_model_cache(monkeypatch, ollama_http):
    monkeypatch.setattr('aiohttp.ClientSession', lambda *args, **kwargs: _FakeAiohttpSession())

    await _set_config(
        **{
            'ollama.enable': True,
            'ollama.base_urls': ['http://ollama.test'],
            'ollama.api_configs': {},
        }
    )
    admin = await Users.insert_new_user(ADMIN_ID, 'Admin', 'admin@example.com', role='admin')

    request = _fake_request()

    # Prime the provider cache while the model is loaded.
    await ollama.get_all_models.cache.clear()
    result = await ollama.get_all_models(request)
    model = next(m for m in result['models'] if m['model'] == MODEL_ID)
    assert 'expires_at' in model, 'sanity: provider reports the model as loaded'

    # The unload actually happens on the provider side...
    ollama_http['loaded'] = False

    # ...and the endpoint responds with success.
    response = await unload_model(request, ModelUnloadForm(model=MODEL_ID), user=admin)
    assert response == {'status': True}

    # The next read must see the fresh unloaded state, not the pre-unload
    # cache entry.
    result = await ollama.get_all_models(request)
    model = next(m for m in result['models'] if m['model'] == MODEL_ID)
    assert 'expires_at' not in model, 'provider cache still returned the stale loaded state'

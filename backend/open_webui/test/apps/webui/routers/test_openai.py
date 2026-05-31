from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_get_models_treats_provider_azure_config_as_azure(monkeypatch):
    from open_webui.routers import openai

    async def fake_get_headers_and_cookies(*args, **kwargs):
        return {}, None

    class FailingClientSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, **kwargs):
            raise AssertionError(f'provider-shaped Azure config used generic models endpoint: {url}')

    monkeypatch.setattr(openai, 'get_headers_and_cookies', fake_get_headers_and_cookies)
    monkeypatch.setattr(openai.aiohttp, 'ClientSession', FailingClientSession)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    ENABLE_OPENAI_API=True,
                    OPENAI_API_BASE_URLS=['https://example.openai.azure.com'],
                    OPENAI_API_KEYS=['secret'],
                    OPENAI_API_CONFIGS={
                        '0': {
                            'provider': 'azure',
                            'model_ids': ['gpt-4o-deployment'],
                            'api_version': '2025-04-01-preview',
                            'auth_type': 'bearer',
                        }
                    },
                )
            )
        )
    )
    user = SimpleNamespace(id='admin-user', role='admin', email='admin@example.com')

    models = await openai.get_models(request, url_idx=0, user=user)

    assert models == {'data': ['gpt-4o-deployment'], 'object': 'list'}

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from open_webui.routers import configs as configs_module
from open_webui.utils.auth import get_admin_user


def _admin_user():
    return SimpleNamespace(id='admin-id', role='admin')


def _regular_user():
    return SimpleNamespace(id='user-id', role='user')


def test_get_admin_user_rejects_non_admin():
    with pytest.raises(HTTPException) as exc:
        get_admin_user(_regular_user())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_langfuse_config_redacts_secrets():
    request = MagicMock()
    stored_connections = [
        {
            'id': 'conn-1',
            'name': 'Prod',
            'url': 'https://lf.example',
            'public_key': 'pk-live',
            'secret_key': 'sk-live',
        }
    ]

    async def fake_config_get(key):
        if key == 'langfuse.connections':
            return stored_connections
        if key == 'langfuse.prompt_cache_ttl':
            return 600
        return None

    with patch.object(configs_module.Config, 'get', side_effect=fake_config_get):
        result = await configs_module.get_langfuse_config(request, user=_admin_user())

    assert result['LANGFUSE_PROMPT_CACHE_TTL'] == 600
    assert result['LANGFUSE_CONNECTIONS'][0]['secret_key'] == ''
    assert result['LANGFUSE_CONNECTIONS'][0]['secret_key_set'] is True
    assert result['LANGFUSE_CONNECTIONS'][0]['public_key'] == 'pk-live'


@pytest.mark.asyncio
async def test_get_langfuse_config_defaults_ttl_when_missing():
    request = MagicMock()

    async def fake_config_get(key):
        if key == 'langfuse.connections':
            return []
        if key == 'langfuse.prompt_cache_ttl':
            return None
        return None

    with patch.object(configs_module.Config, 'get', side_effect=fake_config_get):
        result = await configs_module.get_langfuse_config(request, user=_admin_user())

    assert result['LANGFUSE_PROMPT_CACHE_TTL'] == 300
    assert result['LANGFUSE_CONNECTIONS'] == []


@pytest.mark.asyncio
async def test_set_langfuse_config_persists_and_redacts():
    request = MagicMock()
    existing = [{'id': 'conn-1', 'secret_key': 'stored-secret'}]
    upsert_mock = AsyncMock()

    async def fake_config_get(key):
        if key == 'langfuse.connections':
            return existing
        if key == 'langfuse.prompt_cache_ttl':
            return 300
        return None

    with (
        patch.object(configs_module.Config, 'get', side_effect=fake_config_get),
        patch.object(configs_module.Config, 'upsert', upsert_mock),
        patch.object(configs_module, 'publish_event', new_callable=AsyncMock),
    ):
        result = await configs_module.set_langfuse_config(
            request,
            configs_module.LangfuseConfigForm(
                LANGFUSE_CONNECTIONS=[
                    configs_module.LangfuseConnection(
                        id='conn-1',
                        name='Prod',
                        url='https://lf.example',
                        public_key='pk-live',
                        secret_key='',
                    )
                ],
                LANGFUSE_PROMPT_CACHE_TTL=900,
            ),
            user=_admin_user(),
        )

    upsert_mock.assert_awaited_once()
    updates = upsert_mock.await_args.args[0]
    assert updates['langfuse.prompt_cache_ttl'] == 900
    assert updates['langfuse.connections'][0]['secret_key'] == 'stored-secret'
    assert result['LANGFUSE_PROMPT_CACHE_TTL'] == 900
    assert result['LANGFUSE_CONNECTIONS'][0]['secret_key'] == ''
    assert result['LANGFUSE_CONNECTIONS'][0]['secret_key_set'] is True


@pytest.mark.asyncio
async def test_set_langfuse_config_rejects_negative_ttl():
    request = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await configs_module.set_langfuse_config(
            request,
            configs_module.LangfuseConfigForm(
                LANGFUSE_CONNECTIONS=[],
                LANGFUSE_PROMPT_CACHE_TTL=-1,
            ),
            user=_admin_user(),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_set_langfuse_config_blocks_orphaned_connection_removal():
    request = MagicMock()
    existing = [
        {
            'id': 'conn-bound',
            'name': 'Bound',
            'url': 'https://lf.example',
            'public_key': 'pk',
            'secret_key': 'sk',
            'enabled': True,
        }
    ]

    async def fake_config_get(key):
        if key == 'langfuse.connections':
            return existing
        return None

    with (
        patch.object(configs_module.Config, 'get', side_effect=fake_config_get),
        patch.object(
            configs_module.ModelSystemPromptBindings,
            'count_by_connection_id',
            new_callable=AsyncMock,
            return_value=2,
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await configs_module.set_langfuse_config(
                request,
                configs_module.LangfuseConfigForm(
                    LANGFUSE_CONNECTIONS=[],
                    LANGFUSE_PROMPT_CACHE_TTL=300,
                ),
                user=_admin_user(),
            )

    assert exc.value.status_code == 400
    assert exc.value.detail['blocked_connections'][0]['connection_id'] == 'conn-bound'
    assert exc.value.detail['blocked_connections'][0]['bound_models'] == 2


@pytest.mark.asyncio
async def test_set_langfuse_config_blocks_orphaned_connection_disable():
    request = MagicMock()
    existing = [
        {
            'id': 'conn-bound',
            'name': 'Bound',
            'url': 'https://lf.example',
            'public_key': 'pk',
            'secret_key': 'sk',
            'enabled': True,
        }
    ]

    async def fake_config_get(key):
        if key == 'langfuse.connections':
            return existing
        return None

    with (
        patch.object(configs_module.Config, 'get', side_effect=fake_config_get),
        patch.object(
            configs_module.ModelSystemPromptBindings,
            'count_by_connection_id',
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await configs_module.set_langfuse_config(
                request,
                configs_module.LangfuseConfigForm(
                    LANGFUSE_CONNECTIONS=[
                        configs_module.LangfuseConnection(
                            id='conn-bound',
                            name='Bound',
                            url='https://lf.example',
                            public_key='pk',
                            secret_key='sk',
                            enabled=False,
                        )
                    ],
                    LANGFUSE_PROMPT_CACHE_TTL=300,
                ),
                user=_admin_user(),
            )

    assert exc.value.status_code == 400
    assert exc.value.detail['blocked_connections'][0]['action'] == 'disabled'


@pytest.mark.asyncio
async def test_verify_langfuse_connection_requires_url():
    request = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await configs_module.verify_langfuse_connection(
            request,
            configs_module.LangfuseConnection(url=''),
            user=_admin_user(),
        )

    assert exc.value.status_code == 400
    assert 'URL is required' in exc.value.detail

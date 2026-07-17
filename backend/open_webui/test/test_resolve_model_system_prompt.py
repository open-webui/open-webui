from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.utils.system_prompt import resolve_model_system_prompt


def _make_model(system: str | None = None, model_id: str = 'model-1'):
    params_data = {'system': system} if system is not None else {}
    return SimpleNamespace(
        id=model_id,
        params=SimpleNamespace(model_dump=lambda: params_data),
    )


def _make_binding(**kwargs):
    defaults = {
        'model_id': 'model-1',
        'source': 'local',
        'active_version_id': None,
        'connection_id': None,
        'external_name': None,
        'external_label': None,
        'external_version': None,
        'cached_content': None,
        'cached_version': None,
        'cached_at': None,
        'cache_ttl_seconds': None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_version(**kwargs):
    defaults = {
        'id': 'ver-1',
        'model_id': 'model-1',
        'content': '',
        'user_id': 'user-1',
        'created_at': 1,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_bypass_returns_empty():
    model = _make_model('You are helpful.')

    result = await resolve_model_system_prompt(model, {}, None, bypass=True)

    assert result == ''


@pytest.mark.asyncio
async def test_model_info_none_returns_empty():
    result = await resolve_model_system_prompt(None, {}, None, bypass=False)

    assert result == ''


@pytest.mark.asyncio
async def test_legacy_no_binding_uses_params_system():
    model = _make_model('Legacy prompt {{name}}')
    metadata = {'variables': {'{{name}}': 'User'}}

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_get_binding:
        result = await resolve_model_system_prompt(model, metadata, None, bypass=False)

    assert result == 'Legacy prompt User'
    mock_get_binding.assert_awaited_once_with('model-1')


@pytest.mark.asyncio
async def test_local_active_version_wins_over_stale_mirror():
    model = _make_model('Stale mirror {{role}}')
    binding = _make_binding(source='local', active_version_id='ver-1')
    version = _make_version(content='Active version {{role}}')

    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
            return_value=version,
        ),
    ):
        result = await resolve_model_system_prompt(
            model,
            {'variables': {'{{role}}': 'an expert'}},
            None,
            bypass=False,
        )

    assert result == 'Active version an expert'


@pytest.mark.asyncio
async def test_local_without_active_version_falls_back_to_mirror():
    model = _make_model('Mirror only')
    binding = _make_binding(source='local', active_version_id=None)

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=binding,
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert result == 'Mirror only'


@pytest.mark.asyncio
async def test_langfuse_uses_cached_content():
    model = _make_model('Ignored mirror')
    binding = _make_binding(
        source='langfuse',
        cached_content='Langfuse prompt {{name}}',
        cached_at=999_999_999_999,
    )

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=binding,
    ):
        result = await resolve_model_system_prompt(
            model,
            {'variables': {'{{name}}': 'World'}},
            None,
            bypass=False,
        )

    assert result == 'Langfuse prompt World'


@pytest.mark.asyncio
async def test_langfuse_empty_cache_falls_back_to_mirror():
    model = _make_model('Mirror fallback')
    binding = _make_binding(source='langfuse', cached_content=None)

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=binding,
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert result == 'Mirror fallback'


@pytest.mark.asyncio
async def test_params_system_resolves_templated_string():
    model = _make_model('Hello {{name}}')
    metadata = {'variables': {'{{name}}': 'World'}}

    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            'open_webui.utils.system_prompt.resolve_system_prompt',
            new_callable=AsyncMock,
            return_value='Hello World',
        ) as mock_resolve,
    ):
        result = await resolve_model_system_prompt(model, metadata, None, bypass=False)

    assert result == 'Hello World'
    mock_resolve.assert_awaited_once_with('Hello {{name}}', metadata, None)


@pytest.mark.asyncio
async def test_params_system_end_to_end_with_metadata_variables():
    model = _make_model('Answer as {{role}}')

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await resolve_model_system_prompt(
            model,
            {'variables': {'{{role}}': 'an expert'}},
            None,
            bypass=False,
        )

    assert result == 'Answer as an expert'


@pytest.mark.asyncio
async def test_binding_lookup_error_falls_back_to_mirror():
    model = _make_model('Safe mirror')

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        side_effect=RuntimeError('db unavailable'),
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert result == 'Safe mirror'

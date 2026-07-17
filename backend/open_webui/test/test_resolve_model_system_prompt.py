from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from open_webui.utils.payload import apply_system_prompt_to_body
from open_webui.utils.system_prompt import resolve_model_system_prompt
from open_webui.utils.system_prompt_cache import (
    SYSTEM_PROMPT_CACHE,
    set_cached_system_prompt,
)


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


def setup_function():
    SYSTEM_PROMPT_CACHE.clear()


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
async def test_warm_lru_skips_binding_lookup():
    model = _make_model('Ignored mirror')
    set_cached_system_prompt(
        'model-1',
        'Warm LRU content',
        ttl_seconds=300,
        prompt_name='movie-critic',
        prompt_version='3',
    )
    metadata: dict = {}

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
    ) as mock_get_binding:
        result = await resolve_model_system_prompt(model, metadata, None, bypass=False)

    assert result == 'Warm LRU content'
    assert metadata['langfuse_prompt_name'] == 'movie-critic'
    assert metadata['langfuse_prompt_version'] == '3'
    mock_get_binding.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_no_binding_uses_params_system():
    model = _make_model('Legacy prompt {{name}}')

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_get_binding:
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert result == 'Legacy prompt {{name}}'
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
            'open_webui.integrations.system_prompt.local.ModelSystemPromptVersions.get_version_by_id',
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

    assert result == 'Active version {{role}}'


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
async def test_langfuse_uses_warm_db_cache():
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

    assert result == 'Langfuse prompt {{name}}'


@pytest.mark.asyncio
async def test_langfuse_missing_cached_at_is_cold():
    model = _make_model('Mirror fallback')
    binding = _make_binding(
        source='langfuse',
        connection_id='conn-1',
        external_name='movie-critic',
        cached_content='Orphan cache',
        cached_at=None,
    )

    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.integrations.langfuse.provider.LangfusePromptProvider.fetch_prompt_for_binding',
            new_callable=AsyncMock,
            side_effect=RuntimeError('langfuse down'),
        ),
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert result == 'Orphan cache'


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
async def test_resolve_then_apply_templates_once():
    model = _make_model('Hello {{name}}')
    metadata = {'variables': {'{{name}}': 'World'}}

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ):
        raw = await resolve_model_system_prompt(model, metadata, None, bypass=False)
        body = await apply_system_prompt_to_body(raw, {'messages': []}, metadata, None)

    assert raw == 'Hello {{name}}'
    assert body['messages'][0]['content'] == 'Hello World'


@pytest.mark.asyncio
async def test_params_system_end_to_end_with_metadata_variables():
    model = _make_model('Answer as {{role}}')
    metadata = {'variables': {'{{role}}': 'an expert'}}

    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ):
        raw = await resolve_model_system_prompt(model, metadata, None, bypass=False)
        body = await apply_system_prompt_to_body(raw, {'messages': []}, metadata, None)

    assert body['messages'][0]['content'] == 'Answer as an expert'


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


@pytest.mark.asyncio
async def test_langfuse_live_fetch_updates_cache_and_metadata():
    model = _make_model('Mirror fallback')
    binding = _make_binding(
        source='langfuse',
        connection_id='conn-1',
        external_name='movie-critic',
        external_label='production',
        cached_content='stale cache',
        cached_at=1,
        cache_ttl_seconds=300,
    )
    metadata: dict = {}

    with (
        patch(
            'open_webui.utils.system_prompt._get_default_cache_ttl_seconds',
            new_callable=AsyncMock,
            return_value=300,
        ),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.integrations.langfuse.provider.LangfusePromptProvider.fetch_prompt_for_binding',
            new_callable=AsyncMock,
            return_value=('Fresh prompt {{name}}', '7'),
        ),
        patch(
            'open_webui.utils.system_prompt._persist_langfuse_cache',
            new_callable=AsyncMock,
        ) as mock_persist,
    ):
        result = await resolve_model_system_prompt(
            model,
            metadata,
            None,
            bypass=False,
        )

    assert result == 'Fresh prompt {{name}}'
    assert metadata['langfuse_prompt_name'] == 'movie-critic'
    assert metadata['langfuse_prompt_version'] == '7'
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_langfuse_fetch_fail_uses_stale_cache():
    model = _make_model('Mirror fallback')
    binding = _make_binding(
        source='langfuse',
        connection_id='conn-1',
        external_name='movie-critic',
        cached_content='Stale but usable',
        cached_at=1,
        cache_ttl_seconds=300,
    )

    with (
        patch(
            'open_webui.utils.system_prompt._get_default_cache_ttl_seconds',
            new_callable=AsyncMock,
            return_value=300,
        ),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.utils.system_prompt._fetch_langfuse_prompt_content',
            new_callable=AsyncMock,
            side_effect=RuntimeError('langfuse down'),
        ),
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert result == 'Stale but usable'

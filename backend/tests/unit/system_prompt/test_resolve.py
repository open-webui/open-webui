from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from open_webui.utils.payload import apply_system_prompt_to_body
from open_webui.utils.system_prompt import resolve_model_system_prompt
from open_webui.utils.system_prompt_cache import (
    SYSTEM_PROMPT_CACHE,
    get_cached_system_prompt_async,
    invalidate_system_prompt_cache,
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
    # Arrange
    model = _make_model('You are helpful.')

    # Act
    result = await resolve_model_system_prompt(model, {}, None, bypass=True)

    # Assert
    assert result == ''


@pytest.mark.asyncio
async def test_model_info_none_returns_empty():
    # Act
    result = await resolve_model_system_prompt(None, {}, None, bypass=False)

    # Assert
    assert result == ''


@pytest.mark.asyncio
async def test_warm_lru_revalidates_binding_once_when_no_binding_row():
    # Arrange
    model = _make_model('Ignored mirror')
    set_cached_system_prompt(
        'model-1',
        'Warm LRU content',
        ttl_seconds=300,
        prompt_name='movie-critic',
        prompt_version='3',
    )
    metadata: dict = {}

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_get_binding:
        result = await resolve_model_system_prompt(model, metadata, None, bypass=False)

    # Assert
    assert result == 'Warm LRU content'
    assert metadata['langfuse_prompt_name'] == 'movie-critic'
    assert metadata['langfuse_prompt_version'] == '3'
    mock_get_binding.assert_awaited_once_with('model-1')


@pytest.mark.asyncio
async def test_legacy_no_binding_uses_params_system():
    # Arrange
    model = _make_model('Legacy prompt {{name}}')

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_get_binding:
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert result == 'Legacy prompt {{name}}'
    mock_get_binding.assert_awaited_once_with('model-1')


@pytest.mark.asyncio
async def test_local_active_version_wins_over_stale_mirror():
    # Arrange
    model = _make_model('Stale mirror {{role}}')
    binding = _make_binding(source='local', active_version_id='ver-1')
    version = _make_version(content='Active version {{role}}')

    # Act
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

    # Assert
    assert result == 'Active version {{role}}'


@pytest.mark.asyncio
async def test_local_warm_cache_skips_db_on_second_resolve():
    # Arrange
    model = _make_model('Stale mirror')
    binding = _make_binding(source='local', active_version_id='ver-1')
    version = _make_version(content='Cached local prompt')

    # Act — first resolve populates LRU
    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ) as mock_get_binding,
        patch(
            'open_webui.integrations.system_prompt.local.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
            return_value=version,
        ) as mock_get_version,
    ):
        first = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Act — second resolve must hit warm LRU and only revalidate binding TTL
    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ) as mock_get_binding_2,
        patch(
            'open_webui.integrations.system_prompt.local.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
        ) as mock_get_version_2,
    ):
        second = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert first == 'Cached local prompt'
    assert second == 'Cached local prompt'
    mock_get_binding.assert_awaited_once()
    mock_get_version.assert_awaited_once()
    mock_get_binding_2.assert_awaited_once_with('model-1')
    mock_get_version_2.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_after_set_active_clears_local_cache():
    # Arrange
    model = _make_model('Mirror')
    binding = _make_binding(source='local', active_version_id='ver-1')
    version_v1 = _make_version(id='ver-1', content='Version one')
    version_v2 = _make_version(id='ver-2', content='Version two')

    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.integrations.system_prompt.local.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
            return_value=version_v1,
        ),
    ):
        await resolve_model_system_prompt(model, {}, None, bypass=False)

    assert (await get_cached_system_prompt_async('model-1')) is not None

    # Act — simulate set-active mutation invalidating cache
    invalidate_system_prompt_cache('model-1')
    binding_v2 = _make_binding(source='local', active_version_id='ver-2')

    with (
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding_v2,
        ) as mock_get_binding,
        patch(
            'open_webui.integrations.system_prompt.local.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
            return_value=version_v2,
        ) as mock_get_version,
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert result == 'Version two'
    mock_get_binding.assert_awaited_once()
    mock_get_version.assert_awaited_once()


@pytest.mark.asyncio
async def test_local_empty_active_version_beats_stale_mirror():
    # Arrange
    model = _make_model('Stale mirror {{role}}')
    binding = _make_binding(source='local', active_version_id='ver-1')
    version = _make_version(content='')

    # Act
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

    # Assert
    assert result == ''


@pytest.mark.asyncio
async def test_local_without_active_version_falls_back_to_mirror():
    # Arrange
    model = _make_model('Mirror only')
    binding = _make_binding(source='local', active_version_id=None)

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=binding,
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert result == 'Mirror only'


@pytest.mark.asyncio
async def test_langfuse_uses_warm_db_cache():
    # Arrange
    model = _make_model('Ignored mirror')
    binding = _make_binding(
        source='langfuse',
        cached_content='Langfuse prompt {{name}}',
        cached_at=999_999_999_999,
    )

    # Act
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

    # Assert
    assert result == 'Langfuse prompt {{name}}'


@pytest.mark.asyncio
async def test_langfuse_missing_cached_at_is_cold():
    # Arrange
    model = _make_model('Mirror fallback')
    binding = _make_binding(
        source='langfuse',
        connection_id='conn-1',
        external_name='movie-critic',
        cached_content='Orphan cache',
        cached_at=None,
    )

    # Act
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

    # Assert
    assert result == 'Orphan cache'


@pytest.mark.asyncio
async def test_langfuse_empty_cache_falls_back_to_mirror():
    # Arrange
    model = _make_model('Mirror fallback')
    binding = _make_binding(source='langfuse', cached_content=None)

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=binding,
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert result == 'Mirror fallback'


@pytest.mark.asyncio
async def test_resolve_then_apply_templates_once():
    # Arrange
    model = _make_model('Hello {{name}}')
    metadata = {'variables': {'{{name}}': 'World'}}

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ):
        raw = await resolve_model_system_prompt(model, metadata, None, bypass=False)
        body = await apply_system_prompt_to_body(raw, {'messages': []}, metadata, None)

    # Assert
    assert raw == 'Hello {{name}}'
    assert body['messages'][0]['content'] == 'Hello World'


@pytest.mark.asyncio
async def test_params_system_end_to_end_with_metadata_variables():
    # Arrange
    model = _make_model('Answer as {{role}}')
    metadata = {'variables': {'{{role}}': 'an expert'}}

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        return_value=None,
    ):
        raw = await resolve_model_system_prompt(model, metadata, None, bypass=False)
        body = await apply_system_prompt_to_body(raw, {'messages': []}, metadata, None)

    # Assert
    assert body['messages'][0]['content'] == 'Answer as an expert'


@pytest.mark.asyncio
async def test_binding_lookup_error_falls_back_to_mirror():
    # Arrange
    model = _make_model('Safe mirror')

    # Act
    with patch(
        'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
        side_effect=RuntimeError('db unavailable'),
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert result == 'Safe mirror'


@pytest.mark.asyncio
async def test_langfuse_live_fetch_updates_cache_and_metadata():
    # Arrange
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

    # Act
    with (
        patch(
            'open_webui.integrations.langfuse.provider._get_default_cache_ttl_seconds',
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

    # Assert
    assert result == 'Fresh prompt {{name}}'
    assert metadata['langfuse_prompt_name'] == 'movie-critic'
    assert metadata['langfuse_prompt_version'] == '7'
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_langfuse_fetch_fail_uses_stale_cache():
    # Arrange
    model = _make_model('Mirror fallback')
    binding = _make_binding(
        source='langfuse',
        connection_id='conn-1',
        external_name='movie-critic',
        cached_content='Stale but usable',
        cached_at=1,
        cache_ttl_seconds=300,
    )

    # Act
    with (
        patch(
            'open_webui.integrations.langfuse.provider._get_default_cache_ttl_seconds',
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
            side_effect=RuntimeError('langfuse down'),
        ) as mock_fetch,
    ):
        result = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert result == 'Stale but usable'
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_langfuse_fetch_fail_without_stale_uses_backoff():
    # Arrange
    model = _make_model('Mirror fallback')
    binding = _make_binding(
        source='langfuse',
        connection_id='conn-1',
        external_name='movie-critic',
        cached_content=None,
    )

    # Act
    with (
        patch(
            'open_webui.integrations.langfuse.provider._get_default_cache_ttl_seconds',
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
            side_effect=RuntimeError('langfuse down'),
        ) as mock_fetch,
    ):
        first = await resolve_model_system_prompt(model, {}, None, bypass=False)
        second = await resolve_model_system_prompt(model, {}, None, bypass=False)

    # Assert
    assert first == 'Mirror fallback'
    assert second == 'Mirror fallback'
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_langfuse_cache_skips_older_write():
    # Arrange
    from open_webui.utils.system_prompt import _persist_langfuse_cache

    binding = _make_binding(
        source='langfuse',
        external_name='movie-critic',
        cache_ttl_seconds=300,
    )

    # Act
    with (
        patch('open_webui.utils.system_prompt.time.time', return_value=100),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_binding(
                cached_content='newer content',
                cached_version='5',
                cached_at=200,
            ),
        ),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.update_cache_fields',
            new_callable=AsyncMock,
        ) as mock_update,
        patch(
            'open_webui.utils.system_prompt.set_cached_system_prompt',
        ) as mock_set_cache,
    ):
        await _persist_langfuse_cache(
            'model-1',
            binding,
            'older content',
            prompt_version='4',
            default_ttl=300,
        )

    # Assert
    mock_update.assert_not_awaited()
    mock_set_cache.assert_called_once()

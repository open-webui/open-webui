import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from open_webui.utils.system_prompt_cache import (
    SYSTEM_PROMPT_CACHE,
    STALE_SERVE_POLICY,
    binding_cache_ttl_seconds,
    get_cached_system_prompt,
    invalidate_system_prompt_cache,
    is_binding_db_cache_warm,
    is_newer_cache_write,
    is_system_prompt_fetch_backoff_active,
    record_system_prompt_fetch_failure,
    serve_stale_system_prompt_from_binding,
    set_cached_system_prompt,
)


def setup_function():
    SYSTEM_PROMPT_CACHE.clear()


def test_cache_returns_warm_entry():
    set_cached_system_prompt(
        'model-1',
        'warm content',
        ttl_seconds=300,
        prompt_name='prompt-a',
        prompt_version='2',
    )

    cached = get_cached_system_prompt('model-1')

    assert cached is not None
    assert cached.content == 'warm content'
    assert cached.prompt_name == 'prompt-a'
    assert cached.prompt_version == '2'


def test_cache_expires_stale_entry():
    stale_at = time.time() - 400
    set_cached_system_prompt(
        'model-1',
        'stale content',
        ttl_seconds=300,
        cached_at=stale_at,
    )

    assert get_cached_system_prompt('model-1') is None


def test_invalidate_removes_entry():
    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)

    invalidate_system_prompt_cache('model-1')

    assert get_cached_system_prompt('model-1') is None


def test_binding_cache_ttl_zero_is_not_replaced_by_default():
    binding = SimpleNamespace(cache_ttl_seconds=0)
    assert binding_cache_ttl_seconds(binding, default_ttl=300) == 0


def test_binding_cache_ttl_none_uses_default():
    binding = SimpleNamespace(cache_ttl_seconds=None)
    assert binding_cache_ttl_seconds(binding, default_ttl=300) == 300


def test_cache_ttl_zero_is_always_cold():
    set_cached_system_prompt(
        'model-1',
        'zero ttl content',
        ttl_seconds=0,
    )
    assert get_cached_system_prompt('model-1') is None


def test_binding_db_cache_cold_when_ttl_zero():
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=time.time(),
        cache_ttl_seconds=0,
    )
    assert is_binding_db_cache_warm(binding, default_ttl=300) is False


def test_binding_db_cache_warm_with_clock_skew():
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=time.time() + 3,
        cache_ttl_seconds=300,
    )
    assert is_binding_db_cache_warm(binding, default_ttl=300) is True


def test_is_newer_cache_write_rejects_older_timestamp():
    assert is_newer_cache_write(100, '2', 99, '3') is False


def test_is_newer_cache_write_accepts_newer_timestamp():
    assert is_newer_cache_write(100, '2', 101, '1') is True


def test_is_newer_cache_write_uses_version_on_equal_timestamp():
    assert is_newer_cache_write(100, '2', 100, '3') is True
    assert is_newer_cache_write(100, '3', 100, '2') is False


def test_fetch_failure_backoff_blocks_repeated_fetches():
    record_system_prompt_fetch_failure('model-1')
    assert is_system_prompt_fetch_backoff_active('model-1') is True


def test_serve_stale_extends_effective_ttl():
    binding = SimpleNamespace(
        cached_content='stale prompt',
        cached_at=1,
        cache_ttl_seconds=10,
        external_name='movie-critic',
        cached_version='4',
    )
    entry = serve_stale_system_prompt_from_binding('model-1', binding, default_ttl=300)
    assert entry is not None
    assert entry.content == 'stale prompt'
    assert entry.ttl_seconds >= STALE_SERVE_POLICY.failure_backoff_seconds
    assert get_cached_system_prompt('model-1') is not None


def test_redis_get_refills_lru_when_warm():
    from open_webui.utils.system_prompt_cache import CachedSystemPrompt, _redis_get

    redis_entry = CachedSystemPrompt(
        content='redis warm',
        cached_at=time.time(),
        ttl_seconds=300,
        prompt_name='prompt-a',
        prompt_version='1',
    )
    with patch(
        'open_webui.utils.system_prompt_cache._redis_get',
        return_value=redis_entry,
    ):
        cached = get_cached_system_prompt('model-redis')

    assert cached is not None
    assert cached.content == 'redis warm'
    assert get_cached_system_prompt('model-redis') is not None


def test_redis_set_called_on_lru_write():
    mock_client = MagicMock()
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        set_cached_system_prompt('model-1', 'content', ttl_seconds=300)

    mock_client.set.assert_called_once()


def test_binding_db_cache_cold_when_cached_at_missing():
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=None,
        cache_ttl_seconds=300,
    )

    assert is_binding_db_cache_warm(binding, default_ttl=300) is False


def test_binding_db_cache_warm_when_fresh():
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=time.time(),
        cache_ttl_seconds=300,
    )

    assert is_binding_db_cache_warm(binding, default_ttl=300) is True


@pytest.mark.asyncio
async def test_delete_model_by_id_invalidates_cache():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from open_webui.routers import models as models_module

    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)
    model = SimpleNamespace(id='model-1', name='Model 1', user_id='owner-id')
    request = MagicMock()

    with (
        patch.object(
            models_module.Models,
            'get_model_by_id',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch.object(
            models_module.Models,
            'delete_model_by_id',
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch.object(models_module, 'publish_event', new_callable=AsyncMock),
    ):
        result = await models_module.delete_model_by_id(
            request,
            models_module.ModelIdForm(id='model-1'),
            user=SimpleNamespace(id='owner-id', role='user'),
            db=AsyncMock(),
        )

    assert result is True
    assert get_cached_system_prompt('model-1') is None


@pytest.mark.asyncio
async def test_delete_all_models_clears_cache():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from open_webui.routers import models as models_module

    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)
    set_cached_system_prompt('model-2', 'content', ttl_seconds=300)
    request = MagicMock()

    with (
        patch.object(
            models_module.Models,
            'delete_all_models',
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch.object(models_module, 'publish_event', new_callable=AsyncMock),
    ):
        result = await models_module.delete_all_models(
            request,
            user=SimpleNamespace(id='admin-id', role='admin'),
            db=AsyncMock(),
        )

    assert result is True
    assert get_cached_system_prompt('model-1') is None
    assert get_cached_system_prompt('model-2') is None

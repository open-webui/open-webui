import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from open_webui.utils.system_prompt_cache import (
    _REDIS_KEY_PREFIX,
    STALE_SERVE_POLICY,
    SYSTEM_PROMPT_CACHE,
    CachedSystemPrompt,
    _serialize_entry,
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
    # Arrange
    set_cached_system_prompt(
        'model-1',
        'warm content',
        ttl_seconds=300,
        prompt_name='prompt-a',
        prompt_version='2',
    )

    # Act
    cached = get_cached_system_prompt('model-1')

    # Assert
    assert cached is not None
    assert cached.content == 'warm content'
    assert cached.prompt_name == 'prompt-a'
    assert cached.prompt_version == '2'


def test_cache_expires_stale_entry():
    # Arrange
    stale_at = time.time() - 400
    set_cached_system_prompt(
        'model-1',
        'stale content',
        ttl_seconds=300,
        cached_at=stale_at,
    )

    # Act
    cached = get_cached_system_prompt('model-1')

    # Assert
    assert cached is None


def test_invalidate_removes_entry():
    # Arrange
    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)

    # Act
    invalidate_system_prompt_cache('model-1')

    # Assert
    assert get_cached_system_prompt('model-1') is None


def test_binding_cache_ttl_zero_is_not_replaced_by_default():
    # Arrange
    binding = SimpleNamespace(cache_ttl_seconds=0)

    # Act
    ttl = binding_cache_ttl_seconds(binding, default_ttl=300)

    # Assert
    assert ttl == 0


def test_binding_cache_ttl_none_uses_default():
    # Arrange
    binding = SimpleNamespace(cache_ttl_seconds=None)

    # Act
    ttl = binding_cache_ttl_seconds(binding, default_ttl=300)

    # Assert
    assert ttl == 300


def test_cache_ttl_zero_is_always_cold():
    # Arrange
    set_cached_system_prompt(
        'model-1',
        'zero ttl content',
        ttl_seconds=0,
    )

    # Act
    cached = get_cached_system_prompt('model-1')

    # Assert
    assert cached is None


def test_binding_db_cache_cold_when_ttl_zero():
    # Arrange
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=time.time(),
        cache_ttl_seconds=0,
    )

    # Act
    warm = is_binding_db_cache_warm(binding, default_ttl=300)

    # Assert
    assert warm is False


def test_binding_db_cache_warm_with_clock_skew():
    # Act
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=time.time() + 3,
        cache_ttl_seconds=300,
    )
    # Assert
    assert is_binding_db_cache_warm(binding, default_ttl=300) is True


def test_is_newer_cache_write_rejects_older_timestamp():
    # Arrange / Act
    newer = is_newer_cache_write(100, '2', 99, '3')

    # Assert
    assert newer is False


def test_is_newer_cache_write_accepts_newer_timestamp():
    # Arrange / Act
    newer = is_newer_cache_write(100, '2', 101, '1')

    # Assert
    assert newer is True


def test_is_newer_cache_write_uses_version_on_equal_timestamp():
    # Arrange / Act / Assert
    assert is_newer_cache_write(100, '2', 100, '3') is True
    assert is_newer_cache_write(100, '3', 100, '2') is False


def test_fetch_failure_backoff_blocks_repeated_fetches():
    # Arrange
    record_system_prompt_fetch_failure('model-1')

    # Act
    active = is_system_prompt_fetch_backoff_active('model-1')

    # Assert
    assert active is True


def test_serve_stale_extends_effective_ttl():
    # Arrange
    binding = SimpleNamespace(
        cached_content='stale prompt',
        cached_at=1,
        cache_ttl_seconds=10,
        external_name='movie-critic',
        cached_version='4',
    )
    # Act
    entry = serve_stale_system_prompt_from_binding('model-1', binding, default_ttl=300)
    # Assert
    assert entry is not None
    assert entry.content == 'stale prompt'
    assert entry.ttl_seconds >= STALE_SERVE_POLICY.failure_backoff_seconds
    assert get_cached_system_prompt('model-1') is not None


def test_redis_get_refills_lru_when_warm():
    # Arrange
    redis_entry = CachedSystemPrompt(
        content='redis warm',
        cached_at=time.time(),
        ttl_seconds=300,
        prompt_name='prompt-a',
        prompt_version='1',
    )
    mock_client = MagicMock()
    mock_client.get.return_value = _serialize_entry(redis_entry)

    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        cached = get_cached_system_prompt('model-redis')

    # Assert
    assert cached is not None
    assert cached.content == 'redis warm'
    assert get_cached_system_prompt('model-redis') is not None


def test_clear_removes_all_redis_keys_with_prefix():
    # Arrange
    mock_client = MagicMock()
    key_one = f'{_REDIS_KEY_PREFIX}:model-1'
    key_two = f'{_REDIS_KEY_PREFIX}:model-2'
    mock_client.scan.side_effect = [
        (1, [key_one, key_two]),
        (0, []),
    ]

    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        SYSTEM_PROMPT_CACHE.clear()

    # Assert
    mock_client.scan.assert_any_call(
        cursor=0,
        match=f'{_REDIS_KEY_PREFIX}:*',
        count=500,
    )
    mock_client.delete.assert_called_once_with(key_one, key_two)


def test_redis_miss_keeps_warm_l1():
    # Arrange
    set_cached_system_prompt('model-1', 'warm l1 content', ttl_seconds=300)
    mock_client = MagicMock()
    mock_client.get.return_value = None

    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        cached = get_cached_system_prompt('model-1')

    # Assert
    assert cached is not None
    assert cached.content == 'warm l1 content'
    mock_client.get.assert_not_called()


def test_l1_miss_redis_refills_l1():
    # Arrange
    redis_entry = CachedSystemPrompt(
        content='redis warm',
        cached_at=time.time(),
        ttl_seconds=300,
        prompt_name='prompt-a',
        prompt_version='1',
    )
    mock_client = MagicMock()
    mock_client.get.return_value = _serialize_entry(redis_entry)

    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        cached = get_cached_system_prompt('model-redis-cold-l1')

    # Assert
    assert cached is not None
    assert cached.content == 'redis warm'
    assert SYSTEM_PROMPT_CACHE.get('model-redis-cold-l1') is not None


def test_l1_hit_returns_without_redis_lookup():
    # Arrange
    set_cached_system_prompt('model-1', 'warm l1 content', ttl_seconds=300)
    redis_entry = CachedSystemPrompt(
        content='authoritative redis content',
        cached_at=time.time(),
        ttl_seconds=300,
        prompt_name='prompt-b',
        prompt_version='3',
    )
    mock_client = MagicMock()
    mock_client.get.return_value = _serialize_entry(redis_entry)

    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        cached = get_cached_system_prompt('model-1')

    # Assert
    assert cached is not None
    assert cached.content == 'warm l1 content'
    mock_client.get.assert_not_called()


def test_l1_only_when_redis_unavailable():
    # Arrange
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=None,
    ):
        set_cached_system_prompt('model-1', 'l1 content', ttl_seconds=300)

        # Act
        cached = get_cached_system_prompt('model-1')

    # Assert
    assert cached is not None
    assert cached.content == 'l1 content'


def test_redis_set_called_on_lru_write():
    # Arrange
    mock_client = MagicMock()
    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        set_cached_system_prompt('model-1', 'content', ttl_seconds=300)

    # Assert
    mock_client.set.assert_called_once()


def test_binding_db_cache_cold_when_cached_at_missing():
    # Act
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=None,
        cache_ttl_seconds=300,
    )

    # Assert
    assert is_binding_db_cache_warm(binding, default_ttl=300) is False


def test_binding_db_cache_warm_when_fresh():
    # Act
    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=time.time(),
        cache_ttl_seconds=300,
    )

    # Assert
    assert is_binding_db_cache_warm(binding, default_ttl=300) is True


@pytest.mark.asyncio
async def test_delete_model_by_id_invalidates_cache():
    # Arrange
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from open_webui.routers import models as models_module

    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)
    model = SimpleNamespace(id='model-1', name='Model 1', user_id='owner-id')
    request = MagicMock()

    # Act
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

    # Assert
    assert result is True
    assert get_cached_system_prompt('model-1') is None


@pytest.mark.asyncio
async def test_get_cached_system_prompt_async_l1_hit_skips_redis():
    # Arrange
    from unittest.mock import MagicMock, patch

    from open_webui.utils.system_prompt_cache import get_cached_system_prompt_async

    set_cached_system_prompt('model-1', 'async l1', ttl_seconds=300)
    mock_client = MagicMock()

    # Act
    with patch(
        'open_webui.utils.system_prompt_cache.get_redis_client',
        return_value=mock_client,
    ):
        cached = await get_cached_system_prompt_async('model-1')

    # Assert
    assert cached is not None
    assert cached.content == 'async l1'
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_delete_all_models_clears_cache():
    # Arrange
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from open_webui.routers import models as models_module

    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)
    set_cached_system_prompt('model-2', 'content', ttl_seconds=300)
    request = MagicMock()

    # Act
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

    # Assert
    assert result is True
    assert get_cached_system_prompt('model-1') is None
    assert get_cached_system_prompt('model-2') is None

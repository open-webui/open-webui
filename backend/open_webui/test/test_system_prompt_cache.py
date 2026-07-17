import time
from types import SimpleNamespace

import pytest
from open_webui.utils.system_prompt_cache import (
    SYSTEM_PROMPT_CACHE,
    get_cached_system_prompt,
    invalidate_system_prompt_cache,
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


def test_binding_db_cache_cold_when_cached_at_missing():
    from open_webui.utils.system_prompt_cache import is_binding_db_cache_warm

    binding = SimpleNamespace(
        cached_content='prompt text',
        cached_at=None,
        cache_ttl_seconds=300,
    )

    assert is_binding_db_cache_warm(binding, default_ttl=300) is False


def test_binding_db_cache_warm_when_fresh():
    from open_webui.utils.system_prompt_cache import is_binding_db_cache_warm

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

"""Tests for ModelSystemPromptBindings cache vs identity write semantics."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.models.model_system_prompt_binding import (
    BindingVersionConflictError,
    ModelSystemPromptBindings,
)


def _make_binding(**kwargs):
    defaults = {
        'model_id': 'model-1',
        'source': 'langfuse',
        'active_version_id': None,
        'connection_id': 'conn-1',
        'external_name': 'prompt-a',
        'external_label': None,
        'external_version': None,
        'cached_content': None,
        'cached_version': None,
        'cached_at': None,
        'cache_ttl_seconds': 300,
        'updated_at': 100,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@asynccontextmanager
async def _mock_db_context(db):
    yield db


@pytest.mark.asyncio
async def test_update_cache_fields_preserves_updated_at():
    binding = _make_binding(updated_at=100)
    db = AsyncMock()
    db.get = AsyncMock(return_value=binding)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch(
        'open_webui.models.model_system_prompt_binding.get_async_db_context',
        side_effect=_mock_db_context,
    ):
        result = await ModelSystemPromptBindings.update_cache_fields(
            'model-1',
            cached_content='fresh content',
            cached_version='2',
            cached_at=200,
            cache_ttl_seconds=300,
            db=db,
        )

    assert binding.updated_at == 100
    assert binding.cached_content == 'fresh content'
    assert binding.cached_version == '2'
    assert binding.cached_at == 200
    assert result is not None
    assert result.updated_at == 100


@pytest.mark.asyncio
async def test_upsert_still_bumps_updated_at():
    binding = _make_binding(updated_at=100)
    db = AsyncMock()
    db.get = AsyncMock(return_value=binding)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with (
        patch(
            'open_webui.models.model_system_prompt_binding.get_async_db_context',
            side_effect=_mock_db_context,
        ),
        patch(
            'open_webui.models.model_system_prompt_binding.time.time',
            return_value=500,
        ),
    ):
        result = await ModelSystemPromptBindings.upsert(
            'model-1',
            source='langfuse',
            connection_id='conn-1',
            external_name='prompt-a',
            db=db,
        )

    assert binding.updated_at == 500
    assert result.updated_at == 500


@pytest.mark.asyncio
async def test_cache_persist_then_upsert_with_same_expected_updated_at():
    """Chat-path cache persist must not invalidate PATCH optimistic locking."""
    from open_webui.utils.system_prompt import _persist_langfuse_cache

    binding = _make_binding(
        source='langfuse',
        external_name='prompt-a',
        cache_ttl_seconds=300,
        updated_at=100,
    )
    stored = _make_binding(
        source='langfuse',
        external_name='prompt-a',
        cache_ttl_seconds=300,
        updated_at=100,
    )

    db = AsyncMock()
    db.get = AsyncMock(return_value=stored)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with (
        patch(
            'open_webui.models.model_system_prompt_binding.get_async_db_context',
            side_effect=_mock_db_context,
        ),
        patch('open_webui.utils.system_prompt.time.time', return_value=200),
        patch('open_webui.utils.system_prompt.set_cached_system_prompt'),
    ):
        await _persist_langfuse_cache(
            'model-1',
            binding,
            'chat-fetched content',
            prompt_version='3',
            default_ttl=300,
            db=db,
        )

        assert stored.updated_at == 100
        assert stored.cached_content == 'chat-fetched content'

        result = await ModelSystemPromptBindings.upsert(
            'model-1',
            source='langfuse',
            connection_id='conn-1',
            external_name='prompt-a',
            external_label='production',
            expected_updated_at=100,
            db=db,
        )

    assert result is not None
    assert stored.updated_at != 100


@pytest.mark.asyncio
async def test_upsert_raises_conflict_when_expected_updated_at_stale():
    binding = _make_binding(updated_at=200)
    db = AsyncMock()
    db.get = AsyncMock(return_value=binding)

    with patch(
        'open_webui.models.model_system_prompt_binding.get_async_db_context',
        side_effect=_mock_db_context,
    ):
        with pytest.raises(BindingVersionConflictError) as exc:
            await ModelSystemPromptBindings.upsert(
                'model-1',
                source='langfuse',
                connection_id='conn-1',
                external_name='prompt-a',
                expected_updated_at=100,
                db=db,
            )

    assert exc.value.current_updated_at == 200

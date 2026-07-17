from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from open_webui.integrations.system_prompt.local import LocalSystemPromptProvider
from open_webui.models.model_system_prompt_version import ModelSystemPromptVersions


@pytest.fixture
def provider() -> LocalSystemPromptProvider:
    return LocalSystemPromptProvider()


@pytest.fixture
def connection() -> dict:
    return {'id': 'conn-1', 'url': 'https://example.test', 'enabled': True}


@pytest.mark.asyncio
async def test_list_prompts_not_implemented(provider, connection):
    with pytest.raises(NotImplementedError, match='does not support list_prompts'):
        await provider.list_prompts(connection)


@pytest.mark.asyncio
async def test_get_prompt_not_implemented(provider, connection):
    with pytest.raises(NotImplementedError, match='does not support get_prompt'):
        await provider.get_prompt(connection, 'movie-critic')


@pytest.mark.asyncio
async def test_missing_version_mirror_fallback_not_cached(provider):
    # Arrange
    binding = SimpleNamespace(
        model_id='model-1',
        active_version_id='missing-ver',
        cache_ttl_seconds=3600,
    )
    mirror = 'mirror prompt text'

    with (
        patch.object(
            ModelSystemPromptVersions,
            'get_version_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            'open_webui.integrations.system_prompt.local.set_cached_system_prompt',
        ) as mock_set_cache,
    ):
        # Act
        result = await provider.resolve_content(
            binding,
            mirror=mirror,
            model_id='model-1',
        )

    # Assert
    assert result == mirror
    mock_set_cache.assert_not_called()

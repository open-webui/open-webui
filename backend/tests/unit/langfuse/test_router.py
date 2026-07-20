from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from open_webui.routers import langfuse as langfuse_router
from open_webui.utils.auth import get_admin_user


def _admin_user():
    return SimpleNamespace(id='admin-id', role='admin')


def _regular_user():
    return SimpleNamespace(id='user-id', role='user')


@pytest.mark.asyncio
async def test_list_langfuse_connections_redacts_secrets_for_admin():
    # Arrange
    connections = [{'id': 'conn-1', 'enabled': True, 'secret_key': 'sk'}]

    # Act
    with patch(
        'open_webui.routers.langfuse.list_enabled_connections',
        new_callable=AsyncMock,
        return_value=connections,
    ):
        result = await langfuse_router.list_langfuse_connections(user=_admin_user())

    # Assert
    assert len(result['connections']) == 1
    assert result['connections'][0]['secret_key'] == ''
    assert result['connections'][0]['id'] == 'conn-1'


@pytest.mark.asyncio
async def test_list_langfuse_connections_rejects_non_admin():
    # Act
    with pytest.raises(HTTPException) as exc:
        get_admin_user(_regular_user())

    # Assert
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_list_langfuse_prompts_requires_admin():
    # Arrange
    connection = {'id': 'conn-1', 'enabled': True}
    provider_result = {'data': [{'name': 'movie-critic'}]}

    # Act
    with (
        patch(
            'open_webui.routers.langfuse._get_enabled_connection_or_404',
            new_callable=AsyncMock,
            return_value=connection,
        ),
        patch(
            'open_webui.routers.langfuse.LangfusePromptProvider.list_prompts',
            new_callable=AsyncMock,
            return_value=provider_result,
        ) as mock_list,
    ):
        result = await langfuse_router.list_langfuse_prompts(
            connection_id='conn-1',
            user=_admin_user(),
        )

    # Assert
    assert result == provider_result
    mock_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_langfuse_prompt_requires_admin():
    # Arrange
    connection = {'id': 'conn-1', 'enabled': True}
    provider_result = {'name': 'movie-critic', 'content': 'You are a critic.'}

    # Act
    with (
        patch(
            'open_webui.routers.langfuse._get_enabled_connection_or_404',
            new_callable=AsyncMock,
            return_value=connection,
        ),
        patch(
            'open_webui.routers.langfuse.LangfusePromptProvider.get_prompt',
            new_callable=AsyncMock,
            return_value=provider_result,
        ),
    ):
        result = await langfuse_router.get_langfuse_prompt(
            connection_id='conn-1',
            prompt_name='movie-critic',
            user=_admin_user(),
        )

    # Assert
    assert result == provider_result

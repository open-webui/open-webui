from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from open_webui.utils.auth import get_analytics_user


def _user(role: str = 'user', user_id: str = 'u1'):
    return SimpleNamespace(id=user_id, role=role, email=f'{user_id}@test.com', name='Test')


@pytest.mark.asyncio
async def test_get_analytics_user_allows_admin():
    request = MagicMock()
    request.app.state.config.USER_PERMISSIONS = {}

    user = await get_analytics_user(request=request, user=_user(role='admin'), db=AsyncMock())

    assert user.role == 'admin'


@pytest.mark.asyncio
async def test_get_analytics_user_allows_permission_holder():
    request = MagicMock()
    request.app.state.config.USER_PERMISSIONS = {}

    with patch(
        'open_webui.utils.auth.has_permission',
        new_callable=AsyncMock,
        return_value=True,
    ):
        user = await get_analytics_user(request=request, user=_user(role='user'), db=AsyncMock())

    assert user.role == 'user'


@pytest.mark.asyncio
async def test_get_analytics_user_denies_without_permission():
    request = MagicMock()
    request.app.state.config.USER_PERMISSIONS = {}

    with patch(
        'open_webui.utils.auth.has_permission',
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_analytics_user(request=request, user=_user(role='user'), db=AsyncMock())

    assert exc.value.status_code == 401

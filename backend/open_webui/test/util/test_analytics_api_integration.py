"""Lightweight API integration tests for analytics access control."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_webui.internal.db import get_async_session
from open_webui.routers import analytics
from open_webui.utils.auth import get_current_user


def _build_client(user):
    app = FastAPI()
    app.include_router(analytics.router, prefix='/api/v1/analytics')
    app.state.config = SimpleNamespace(USER_PERMISSIONS={})

    async def _override_current_user():
        return user

    async def _override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_async_session] = _override_db

    return TestClient(app)


def test_analytics_summary_allowed_for_admin():
    user = SimpleNamespace(id='admin-1', role='admin', email='a@test.com', name='Admin')

    with patch(
        'open_webui.routers.analytics.ChatMessages.get_message_count_by_model',
        new_callable=AsyncMock,
        return_value={'m1': 1},
    ), patch(
        'open_webui.routers.analytics.ChatMessages.get_message_count_by_user',
        new_callable=AsyncMock,
        return_value={'u1': 1},
    ), patch(
        'open_webui.routers.analytics.ChatMessages.get_message_count_by_chat',
        new_callable=AsyncMock,
        return_value={'c1': 1},
    ):
        client = _build_client(user)
        response = client.get('/api/v1/analytics/summary')

    assert response.status_code == 200
    body = response.json()
    assert body['total_messages'] == 1
    assert body['total_users'] == 1


def test_analytics_summary_allowed_for_analytics_user():
    user = SimpleNamespace(id='user-1', role='user', email='u@test.com', name='User')

    with (
        patch(
            'open_webui.utils.auth.has_permission',
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            'open_webui.routers.analytics.ChatMessages.get_message_count_by_model',
            new_callable=AsyncMock,
            return_value={'m1': 2},
        ),
        patch(
            'open_webui.routers.analytics.ChatMessages.get_message_count_by_user',
            new_callable=AsyncMock,
            return_value={'u1': 1, 'u2': 1},
        ),
        patch(
            'open_webui.routers.analytics.ChatMessages.get_message_count_by_chat',
            new_callable=AsyncMock,
            return_value={'c1': 1, 'c2': 1},
        ),
    ):
        client = _build_client(user)
        response = client.get('/api/v1/analytics/summary')

    assert response.status_code == 200


def test_analytics_summary_denied_for_regular_user():
    user = SimpleNamespace(id='user-2', role='user', email='u2@test.com', name='User')

    with patch(
        'open_webui.utils.auth.has_permission',
        new_callable=AsyncMock,
        return_value=False,
    ):
        client = _build_client(user)
        response = client.get('/api/v1/analytics/summary')

    assert response.status_code == 401

import json
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure required env var is set for open_webui imports
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret-key-for-unit-tests-12345')

import pytest
from open_webui.env import REDIS_KEY_PREFIX
from open_webui.utils.tools import get_terminal_servers, get_tool_servers


class DummyAppState:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.TOOL_SERVERS = None
        self.TERMINAL_SERVERS = None


class DummyApp:
    def __init__(self, state):
        self.state = state


class DummyRequest:
    def __init__(self, app_state):
        self.app = DummyApp(app_state)


@pytest.mark.asyncio
async def test_get_tool_servers_cache_miss_no_type_error(caplog):
    """Test Redis cache miss returns None, fetches via set_tool_servers without logging TypeError."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()

    app_state = DummyAppState(redis_client=mock_redis)
    request = DummyRequest(app_state)

    fetched_servers = [{'id': 'server-1', 'url': 'http://localhost:8000'}]
    with patch('open_webui.utils.tools.set_tool_servers', new=AsyncMock(return_value=fetched_servers)) as mock_set:
        with caplog.at_level(logging.ERROR):
            result = await get_tool_servers(request)

        mock_redis.get.assert_awaited_once_with(f'{REDIS_KEY_PREFIX}:tool_servers')
        mock_set.assert_awaited_once_with(request)
        assert result == fetched_servers
        # Assert no JSON TypeError was logged during cache miss
        for record in caplog.records:
            assert 'the JSON object must be str' not in record.message
            assert 'Error fetching tool_servers from Redis' not in record.message


@pytest.mark.asyncio
async def test_get_tool_servers_cache_hit_empty_list():
    """Test Redis cache hit with empty list does NOT call set_tool_servers."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps([]))

    app_state = DummyAppState(redis_client=mock_redis)
    request = DummyRequest(app_state)

    with patch('open_webui.utils.tools.set_tool_servers', new=AsyncMock()) as mock_set:
        result = await get_tool_servers(request)

        mock_redis.get.assert_awaited_once_with(f'{REDIS_KEY_PREFIX}:tool_servers')
        mock_set.assert_not_awaited()
        assert result == []
        assert app_state.TOOL_SERVERS == []


@pytest.mark.asyncio
async def test_get_tool_servers_cache_hit_populated():
    """Test Redis cache hit with populated server list."""
    cached_servers = [{'id': 'srv1', 'url': 'https://api.tools.com'}]
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_servers))

    app_state = DummyAppState(redis_client=mock_redis)
    request = DummyRequest(app_state)

    with patch('open_webui.utils.tools.set_tool_servers', new=AsyncMock()) as mock_set:
        result = await get_tool_servers(request)

        mock_redis.get.assert_awaited_once_with(f'{REDIS_KEY_PREFIX}:tool_servers')
        mock_set.assert_not_awaited()
        assert result == cached_servers
        assert app_state.TOOL_SERVERS == cached_servers


@pytest.mark.asyncio
async def test_get_terminal_servers_cache_miss_no_type_error(caplog):
    """Test Redis cache miss for terminal_servers fetches via set_terminal_servers without TypeError."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()

    app_state = DummyAppState(redis_client=mock_redis)
    request = DummyRequest(app_state)

    fetched_terminals = [{'id': 'term-1', 'url': 'http://localhost:9000'}]
    with patch(
        'open_webui.utils.tools.set_terminal_servers', new=AsyncMock(return_value=fetched_terminals)
    ) as mock_set:
        with caplog.at_level(logging.ERROR):
            result = await get_terminal_servers(request)

        mock_redis.get.assert_awaited_once_with(f'{REDIS_KEY_PREFIX}:terminal_servers')
        mock_set.assert_awaited_once_with(request)
        assert result == fetched_terminals
        for record in caplog.records:
            assert 'the JSON object must be str' not in record.message
            assert 'Error fetching terminal_servers from Redis' not in record.message


@pytest.mark.asyncio
async def test_get_terminal_servers_cache_hit_empty_list():
    """Test Redis cache hit with empty list for terminal_servers does NOT call set_terminal_servers."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps([]))

    app_state = DummyAppState(redis_client=mock_redis)
    request = DummyRequest(app_state)

    with patch('open_webui.utils.tools.set_terminal_servers', new=AsyncMock()) as mock_set:
        result = await get_terminal_servers(request)

        mock_redis.get.assert_awaited_once_with(f'{REDIS_KEY_PREFIX}:terminal_servers')
        mock_set.assert_not_awaited()
        assert result == []
        assert app_state.TERMINAL_SERVERS == []


@pytest.mark.asyncio
async def test_get_terminal_servers_cache_hit_populated():
    """Test Redis cache hit with populated terminal server list."""
    cached_terminals = [{'id': 'term1', 'url': 'https://terminal.tools.com'}]
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_terminals))

    app_state = DummyAppState(redis_client=mock_redis)
    request = DummyRequest(app_state)

    with patch('open_webui.utils.tools.set_terminal_servers', new=AsyncMock()) as mock_set:
        result = await get_terminal_servers(request)

        mock_redis.get.assert_awaited_once_with(f'{REDIS_KEY_PREFIX}:terminal_servers')
        mock_set.assert_not_awaited()
        assert result == cached_terminals
        assert app_state.TERMINAL_SERVERS == cached_terminals

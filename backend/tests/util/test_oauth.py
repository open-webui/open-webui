"""Tests for OAuth resource_metadata parsing in WWW-Authenticate headers.

Tests get_authorization_server_discovery_urls() which extracts the
resource_metadata URL from WWW-Authenticate: Bearer headers returned by MCP
servers during OAuth protected resource discovery.
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from open_webui.utils.oauth import get_authorization_server_discovery_urls


class _AsyncContextManager:
    """Minimal async context manager that yields a fixed value."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *args):
        pass


def _make_response(status, headers=None):
    """Create a mock aiohttp response with the given status and headers."""
    resp = MagicMock()
    resp.status = status
    resp.headers = headers or {}
    return resp


def _make_resource_metadata_response(authorization_servers):
    """Create a mock 200 response for the resource metadata endpoint."""
    resp = MagicMock()
    resp.status = 200
    resp.json = AsyncMock(
        return_value={"authorization_servers": authorization_servers}
    )
    return resp


def _build_mock_session(post_response, get_response=None):
    """Build a mock aiohttp.ClientSession with canned post/get responses.

    session.post(...) and session.get(...) are regular calls (not awaited)
    that return async context managers, matching the real aiohttp API.
    """
    session = MagicMock()
    session.post = MagicMock(return_value=_AsyncContextManager(post_response))
    if get_response is not None:
        session.get = MagicMock(return_value=_AsyncContextManager(get_response))
    return session


def _patch_aiohttp_session(session):
    """Return a patch context that makes aiohttp.ClientSession() yield `session`."""
    mock_cs = MagicMock()
    mock_cs.return_value = _AsyncContextManager(session)
    return patch("open_webui.utils.oauth.aiohttp.ClientSession", mock_cs)


class TestGetAuthorizationServerDiscoveryUrls:
    """Tests for get_authorization_server_discovery_urls()."""

    @pytest.mark.asyncio
    async def test_quoted_resource_metadata(self):
        """Quoted resource_metadata value (the common form) should be extracted."""
        resource_metadata_url = "https://auth.example.com/.well-known/oauth-protected-resource"
        auth_server = "https://auth.example.com"

        init_resp = _make_response(
            401,
            {"WWW-Authenticate": f'Bearer resource_metadata="{resource_metadata_url}"'},
        )
        meta_resp = _make_resource_metadata_response([auth_server])
        session = _build_mock_session(init_resp, meta_resp)

        with _patch_aiohttp_session(session):
            urls = await get_authorization_server_discovery_urls(
                "https://mcp.example.com/v1"
            )

        assert f"{auth_server}/.well-known/oauth-authorization-server" in urls
        assert f"{auth_server}/.well-known/openid-configuration" in urls

    @pytest.mark.asyncio
    async def test_unquoted_resource_metadata(self):
        """Unquoted resource_metadata value should also be extracted.

        Some MCP servers return the header without quotes, e.g.:
            Bearer resource_metadata=https://auth.example.com/...
        """
        resource_metadata_url = "https://auth.example.com/.well-known/oauth-protected-resource"
        auth_server = "https://auth.example.com"

        init_resp = _make_response(
            401,
            {"WWW-Authenticate": f"Bearer resource_metadata={resource_metadata_url}"},
        )
        meta_resp = _make_resource_metadata_response([auth_server])
        session = _build_mock_session(init_resp, meta_resp)

        with _patch_aiohttp_session(session):
            urls = await get_authorization_server_discovery_urls(
                "https://mcp.example.com/v1"
            )

        assert f"{auth_server}/.well-known/oauth-authorization-server" in urls
        assert f"{auth_server}/.well-known/openid-configuration" in urls

    @pytest.mark.asyncio
    async def test_unquoted_resource_metadata_with_additional_params(self):
        """Unquoted value followed by other Bearer params should parse correctly."""
        resource_metadata_url = "https://auth.example.com/.well-known/oauth-protected-resource"
        auth_server = "https://auth.example.com"

        init_resp = _make_response(
            401,
            {
                "WWW-Authenticate": (
                    f"Bearer resource_metadata={resource_metadata_url},"
                    f' realm="example"'
                )
            },
        )
        meta_resp = _make_resource_metadata_response([auth_server])
        session = _build_mock_session(init_resp, meta_resp)

        with _patch_aiohttp_session(session):
            urls = await get_authorization_server_discovery_urls(
                "https://mcp.example.com/v1"
            )

        assert f"{auth_server}/.well-known/oauth-authorization-server" in urls
        assert f"{auth_server}/.well-known/openid-configuration" in urls

    @pytest.mark.asyncio
    async def test_no_resource_metadata_returns_empty(self):
        """When WWW-Authenticate has no resource_metadata, return empty list."""
        init_resp = _make_response(401, {"WWW-Authenticate": "Bearer"})
        session = _build_mock_session(init_resp)

        with _patch_aiohttp_session(session):
            urls = await get_authorization_server_discovery_urls(
                "https://mcp.example.com/v1"
            )

        assert urls == []

    @pytest.mark.asyncio
    async def test_non_401_response_returns_empty(self):
        """When MCP server does not return 401, return empty list."""
        init_resp = _make_response(200)
        session = _build_mock_session(init_resp)

        with _patch_aiohttp_session(session):
            urls = await get_authorization_server_discovery_urls(
                "https://mcp.example.com/v1"
            )

        assert urls == []

    @pytest.mark.asyncio
    async def test_multiple_authorization_servers(self):
        """Multiple authorization_servers in metadata produce discovery URLs for each."""
        resource_metadata_url = "https://auth.example.com/.well-known/oauth-protected-resource"
        servers = ["https://auth1.example.com", "https://auth2.example.com"]

        init_resp = _make_response(
            401,
            {"WWW-Authenticate": f'Bearer resource_metadata="{resource_metadata_url}"'},
        )
        meta_resp = _make_resource_metadata_response(servers)
        session = _build_mock_session(init_resp, meta_resp)

        with _patch_aiohttp_session(session):
            urls = await get_authorization_server_discovery_urls(
                "https://mcp.example.com/v1"
            )

        assert len(urls) == 4
        for server in servers:
            assert f"{server}/.well-known/oauth-authorization-server" in urls
            assert f"{server}/.well-known/openid-configuration" in urls

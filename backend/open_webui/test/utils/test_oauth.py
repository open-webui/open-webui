import pytest
from open_webui.utils.oauth import get_discovery_urls


@pytest.mark.asyncio
async def test_get_discovery_urls_prefers_authorization_server_url():
    urls = await get_discovery_urls(
        'https://gmailmcp.googleapis.com/mcp/v1',
        'https://accounts.google.com',
    )

    assert urls == [
        'https://accounts.google.com/.well-known/oauth-authorization-server',
        'https://accounts.google.com/.well-known/openid-configuration',
    ]


@pytest.mark.asyncio
async def test_get_discovery_urls_accepts_explicit_discovery_url():
    urls = await get_discovery_urls(
        'https://gmailmcp.googleapis.com/mcp/v1',
        'https://accounts.google.com/.well-known/openid-configuration',
    )

    assert urls == ['https://accounts.google.com/.well-known/openid-configuration']


@pytest.mark.asyncio
async def test_get_discovery_urls_preserves_current_fallback_without_override(monkeypatch):
    async def mock_authorization_server_discovery(server_url: str) -> list[str]:
        assert server_url == 'https://gmailmcp.googleapis.com/mcp/v1'
        return []

    monkeypatch.setattr(
        'open_webui.utils.oauth.get_authorization_server_discovery_urls',
        mock_authorization_server_discovery,
    )

    urls = await get_discovery_urls('https://gmailmcp.googleapis.com/mcp/v1')

    assert urls == [
        'https://gmailmcp.googleapis.com/.well-known/oauth-authorization-server/mcp/v1',
        'https://gmailmcp.googleapis.com/.well-known/openid-configuration/mcp/v1',
        'https://gmailmcp.googleapis.com/mcp/v1/.well-known/openid-configuration',
        'https://gmailmcp.googleapis.com/.well-known/oauth-authorization-server',
        'https://gmailmcp.googleapis.com/.well-known/openid-configuration',
    ]

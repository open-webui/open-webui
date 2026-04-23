from open_webui.utils.oauth import (
    get_protected_resource_well_known_metadata_urls,
    get_well_known_authorization_endpoints,
)


def test_get_protected_resource_well_known_metadata_urls():
    base_url = 'https://example.com/public/mcp'
    metadata_urls = get_protected_resource_well_known_metadata_urls(base_url)
    assert metadata_urls == [
        'https://example.com/.well-known/oauth-protected-resource/public/mcp',
        'https://example.com/.well-known/oauth-protected-resource',
    ]


def test_get_well_known_authorization_endpoints_no_tenant():
    authorization_servers = [
        'https://auth.example.com',
    ]
    authorization_metadata_urls = get_well_known_authorization_endpoints(authorization_servers)
    assert authorization_metadata_urls == [
        'https://auth.example.com/.well-known/oauth-authorization-server',
        'https://auth.example.com/.well-known/openid-configuration',
    ]


def test_get_well_known_authorization_endpoints_with_tenant():
    authorization_servers = [
        'https://auth.example.com/tenant1',
    ]
    authorization_metadata_urls = get_well_known_authorization_endpoints(authorization_servers)
    assert authorization_metadata_urls == [
        'https://auth.example.com/.well-known/oauth-authorization-server/tenant1',
        'https://auth.example.com/.well-known/openid-configuration/tenant1',
        'https://auth.example.com/tenant1/.well-known/openid-configuration',
    ]

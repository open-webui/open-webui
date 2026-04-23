from open_webui.utils.oauth import get_protected_resource_well_known_metadata_urls

def test_get_protected_resource_well_known_metadata_urls():
    base_url = "https://example.com/public/mcp"
    metadata_urls = get_protected_resource_well_known_metadata_urls(base_url)
    assert metadata_urls == [
        "https://example.com/.well-known/oauth-protected-resource/public/mcp",
        "https://example.com/.well-known/oauth-protected-resource",
    ]

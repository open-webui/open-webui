import pytest

from open_webui.utils.tools import get_tool_server_url


class TestGetToolServerUrl:
    """Test get_tool_server_url which normalizes URLs for both spec
    fetching (verify) and is the basis for execution URL construction.

    The same rstrip('/') normalization pattern is applied in
    get_tool_servers_data and execute_tool_server to prevent
    double-slash issues.
    """

    # --- Basic path joining ---

    def test_basic_url_and_path(self):
        result = get_tool_server_url("http://localhost:8080", "openapi.json")
        assert result == "http://localhost:8080/openapi.json"

    def test_path_starting_with_slash(self):
        result = get_tool_server_url("http://localhost:8080", "/openapi.json")
        assert result == "http://localhost:8080/openapi.json"

    def test_nested_path(self):
        result = get_tool_server_url("http://localhost:8080", "api/v1/openapi.json")
        assert result == "http://localhost:8080/api/v1/openapi.json"

    def test_full_url_in_path(self):
        result = get_tool_server_url(
            "http://localhost:8080", "https://other-host/spec.json"
        )
        assert result == "https://other-host/spec.json"

    def test_none_url_with_full_path(self):
        result = get_tool_server_url(None, "https://other-host/spec.json")
        assert result == "https://other-host/spec.json"

    # --- Trailing slash normalization (core fix) ---

    def test_url_trailing_slash_stripped(self):
        result = get_tool_server_url("http://localhost:8080/", "openapi.json")
        assert result == "http://localhost:8080/openapi.json"

    def test_url_with_path_trailing_slash_stripped(self):
        result = get_tool_server_url("http://localhost:8080/v1/", "openapi.json")
        assert result == "http://localhost:8080/v1/openapi.json"

    def test_slash_url_and_slash_path_no_double(self):
        result = get_tool_server_url("http://localhost:8080/", "/openapi.json")
        assert result == "http://localhost:8080/openapi.json"
        assert "//" not in result.split("://", 1)[1]

    def test_multiple_trailing_slashes_stripped(self):
        result = get_tool_server_url("http://localhost:8080///", "openapi.json")
        assert result == "http://localhost:8080/openapi.json"

    # --- Subpath / reverse proxy preservation ---

    def test_subpath_preserved(self):
        result = get_tool_server_url("http://localhost:8080/api/v1", "openapi.json")
        assert result == "http://localhost:8080/api/v1/openapi.json"

    def test_proxy_prefix_preserved(self):
        result = get_tool_server_url("http://proxy:8080/gateway/tools", "openapi.json")
        assert result == "http://proxy:8080/gateway/tools/openapi.json"

    def test_proxy_prefix_trailing_slash_stripped(self):
        result = get_tool_server_url("http://proxy:8080/gateway/tools/", "openapi.json")
        assert result == "http://proxy:8080/gateway/tools/openapi.json"
        assert "//" not in result.split("://", 1)[1]

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestToolsSocketEmit(AbstractPostgresTest):
    """Ensure `tools:update` socket event is broadcast after a tool update."""

    BASE_PATH = "/api/v1/tools"

    def _make_dummy_tool(self, tool_id: str, name: str = "Dummy Tool"):
        """Return a minimal object that mimics ToolModel attributes used by the route."""
        return SimpleNamespace(id=tool_id, name=name)

    def test_tools_update_emits_socket_event(self):
        tool_id = "mytool"
        updated_name = "My Updated Tool"

        dummy_tool = self._make_dummy_tool(tool_id, updated_name)

        with (
            mock_webui_user(role="admin"),
            patch("open_webui.routers.tools.sio.emit", new_callable=AsyncMock) as mock_emit,
            patch("open_webui.routers.tools.load_tool_module_by_id", return_value=(Mock(), {})),
            patch("open_webui.routers.tools.replace_imports", side_effect=lambda x: x),
            patch("open_webui.routers.tools.get_tool_specs", return_value=[]),
            patch("open_webui.routers.tools.Tools.get_tool_by_id", return_value=dummy_tool),
            patch("open_webui.routers.tools.Tools.update_tool_by_id", return_value=dummy_tool),
        ):
            response = self.fast_api_client.post(
                self.create_url(f"/id/{tool_id}/update"),
                json={
                    "id": tool_id,
                    "name": updated_name,
                    "content": "# dummy content\nclass Tools:\n    pass",
                    "meta": {},
                },
            )

        assert response.status_code == 200
        assert response.json()["name"] == updated_name

        mock_emit.assert_awaited_once_with(
            "tools:update",
            {"id": tool_id, "name": updated_name},
            namespace="/",
            broadcast=True,
        )

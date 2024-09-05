from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestPrompts(AbstractPostgresTest):
    BASE_PATH = "/api/v1/prompts"

    def test_prompts(self):
        # Get all prompts
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Create a two new prompts
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "command": "/my-command",
                    "title": "Hello World",
                    "content": "description",
                },
            )
        assert response.status_code == 200
        with mock_webui_user(id="3"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "command": "/my-command2",
                    "title": "Hello World 2",
                    "content": "description 2",
                },
            )
        assert response.status_code == 200

        # Get all prompts
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Get prompt by command
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/command/my-command"))
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "/my-command"
        assert data["title"] == "Hello World"
        assert data["content"] == "description"
        assert data["user_id"] == "2"

        # Update prompt
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/command/my-command2/update"),
                json={
                    "command": "irrelevant for request",
                    "title": "Hello World Updated",
                    "content": "description Updated",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "/my-command2"
        assert data["title"] == "Hello World Updated"
        assert data["content"] == "description Updated"
        assert data["user_id"] == "3"

        # Get prompt by command
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/command/my-command2"))
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "/my-command2"
        assert data["title"] == "Hello World Updated"
        assert data["content"] == "description Updated"
        assert data["user_id"] == "3"

        # Delete prompt
        with mock_webui_user(id="2"):
            response = self.fast_api_client.delete(
                self.create_url("/command/my-command/delete")
            )
        assert response.status_code == 200

        # Get all prompts
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 1

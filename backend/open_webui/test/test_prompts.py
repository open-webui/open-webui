from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestPrompts(AbstractPostgresTest):
    """
    Integration tests for the core Prompts API operations in prompts.py.

    Covers the full lifecycle of a prompt record:
      1. Create  — POST /api/v1/prompts/create
      2. Read    — GET  /api/v1/prompts/id/{id}
      3. List    — GET  /api/v1/prompts/
      4. Update  — POST /api/v1/prompts/id/{id}/update
      5. Delete  — DELETE /api/v1/prompts/id/{id}/delete
    """

    BASE_PATH = "/api/v1/prompts"

    @classmethod
    def setup_class(cls):
        super().setup_class()
        from open_webui.models.prompts import Prompts
        cls.Prompts = Prompts

    # ------------------------------------------------------------------
    # Test 1: create a new prompt and read it back
    # ------------------------------------------------------------------
    def test_create_and_get_prompt(self):
        """
        POST /create should persist a prompt that can be retrieved
        immediately afterwards with GET /id/{id}, with all fields intact.
        """
        with mock_webui_user(id="user-1"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "command": "/greet",
                    "name": "Greeting Prompt",
                    "content": "Say hello to {{name}}.",
                },
            )

        assert response.status_code == 200
        data = response.json()
        prompt_id = data["id"]

        assert data["command"] == "/greet"
        assert data["name"] == "Greeting Prompt"
        assert data["content"] == "Say hello to {{name}}."
        assert data["user_id"] == "user-1"

        # Read it back by ID
        with mock_webui_user(id="user-1"):
            get_response = self.fast_api_client.get(self.create_url(f"/id/{prompt_id}"))

        assert get_response.status_code == 200
        assert get_response.json()["id"] == prompt_id
        assert get_response.json()["command"] == "/greet"

    # ------------------------------------------------------------------
    # Test 2: prompt appears in list after creation
    # ------------------------------------------------------------------
    def test_prompt_appears_in_list(self):
        """
        A newly created prompt should appear in GET / so the frontend
        can populate the slash-command menu correctly.
        """
        # List is empty before creation
        with mock_webui_user(id="user-2"):
            list_before = self.fast_api_client.get(self.create_url("/"))
        assert list_before.status_code == 200
        assert list_before.json() == []

        # Create a prompt
        with mock_webui_user(id="user-2"):
            create_resp = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "command": "/summarize",
                    "name": "Summarizer",
                    "content": "Summarize this: {{text}}",
                },
            )
        assert create_resp.status_code == 200
        prompt_id = create_resp.json()["id"]

        # It should now appear in the list
        with mock_webui_user(id="user-2"):
            list_after = self.fast_api_client.get(self.create_url("/"))
        assert list_after.status_code == 200
        ids = [p["id"] for p in list_after.json()]
        assert prompt_id in ids

    # ------------------------------------------------------------------
    # Test 3: duplicate command is rejected
    # ------------------------------------------------------------------
    def test_duplicate_command_rejected(self):
        """
        Creating two prompts with the same /command must return 400 so
        that commands remain unambiguous shortcuts in the chat interface.
        """
        payload = {
            "command": "/translate",
            "name": "Translator",
            "content": "Translate to {{language}}: {{text}}",
        }

        with mock_webui_user(id="user-3"):
            first = self.fast_api_client.post(self.create_url("/create"), json=payload)
        assert first.status_code == 200

        with mock_webui_user(id="user-3"):
            second = self.fast_api_client.post(self.create_url("/create"), json=payload)
        assert second.status_code == 400

    # ------------------------------------------------------------------
    # Test 4: update a prompt's content and name
    # ------------------------------------------------------------------
    def test_update_prompt(self):
        """
        POST /id/{id}/update should persist updated fields and those
        changes should be visible on a subsequent GET, not just in the
        response object.
        """
        with mock_webui_user(id="user-4"):
            create_resp = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "command": "/rephrase",
                    "name": "Rephraser",
                    "content": "Rephrase: {{text}}",
                },
            )
        assert create_resp.status_code == 200
        prompt_id = create_resp.json()["id"]

        # Update name and content
        with mock_webui_user(id="user-4"):
            update_resp = self.fast_api_client.post(
                self.create_url(f"/id/{prompt_id}/update"),
                json={
                    "command": "/rephrase",
                    "name": "Rephraser v2",
                    "content": "Rephrase this text: {{text}}",
                },
            )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Rephraser v2"
        assert update_resp.json()["content"] == "Rephrase this text: {{text}}"

        # Confirm change is durable via a separate GET
        with mock_webui_user(id="user-4"):
            get_resp = self.fast_api_client.get(self.create_url(f"/id/{prompt_id}"))
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Rephraser v2"
        assert get_resp.json()["content"] == "Rephrase this text: {{text}}"

    # ------------------------------------------------------------------
    # Test 5: delete a prompt
    # ------------------------------------------------------------------
    def test_delete_prompt(self):
        """
        DELETE /id/{id}/delete should remove the prompt so that a
        subsequent GET returns 404.
        """
        with mock_webui_user(id="user-5"):
            create_resp = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "command": "/proofread",
                    "name": "Proofreader",
                    "content": "Proofread: {{text}}",
                },
            )
        assert create_resp.status_code == 200
        prompt_id = create_resp.json()["id"]

        # Delete
        with mock_webui_user(id="user-5"):
            delete_resp = self.fast_api_client.delete(
                self.create_url(f"/id/{prompt_id}/delete")
            )
        assert delete_resp.status_code == 200
        assert delete_resp.json() is True

        # Confirm it is gone
        with mock_webui_user(id="user-5"):
            get_resp = self.fast_api_client.get(self.create_url(f"/id/{prompt_id}"))
        assert get_resp.status_code == 404

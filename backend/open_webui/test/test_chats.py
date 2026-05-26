import uuid

from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestChats(AbstractPostgresTest):
    """
    Integration tests for the core ChatTable operations in chats.py.

    Covers the full lifecycle of a chat record:
      1. Create  — insert_new_chat
      2. Read    — get_chat_by_id, get_chat_by_id_and_user_id
      3. Update  — update_chat_by_id, update_chat_title_by_id
      4. Archive — toggle_chat_archive_by_id
      5. Delete  — delete_chat_by_id
    """

    BASE_PATH = "/api/v1/chats"

    @classmethod
    def setup_class(cls):
        super().setup_class()
        from open_webui.models.chats import ChatTable, ChatForm
        cls.Chats = ChatTable()
        cls.ChatForm = ChatForm

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _make_form(self, title: str = "Test Chat") -> object:
        """Return a minimal ChatForm suitable for insert_new_chat."""
        return self.ChatForm(chat={"title": title, "history": {"messages": {}}})

    # ------------------------------------------------------------------
    # Test 1: create a new chat and read it back
    # ------------------------------------------------------------------
    def test_insert_and_get_chat(self):
        """
        insert_new_chat should persist a chat row that can be retrieved
        immediately afterwards with get_chat_by_id.
        """
        with mock_webui_user(id="user-1"):
            response = self.fast_api_client.post(
                self.create_url("/new"),
                json={"chat": {"title": "Hello Chat", "history": {"messages": {}}}},
            )

        assert response.status_code == 200
        data = response.json()
        chat_id = data["id"]

        assert data["title"] == "Hello Chat"
        assert data["user_id"] == "user-1"
        assert data["archived"] is False

        # Read it back
        with mock_webui_user(id="user-1"):
            get_response = self.fast_api_client.get(self.create_url(f"/{chat_id}"))

        assert get_response.status_code == 200
        assert get_response.json()["id"] == chat_id

    # ------------------------------------------------------------------
    # Test 2: update a chat's title
    # ------------------------------------------------------------------
    def test_update_chat_title(self):
        """
        update_chat_title_by_id should change the chat's title and leave
        all other fields intact.
        """
        # Create
        with mock_webui_user(id="user-2"):
            create_resp = self.fast_api_client.post(
                self.create_url("/new"),
                json={"chat": {"title": "Original Title", "history": {"messages": {}}}},
            )
        assert create_resp.status_code == 200
        chat_id = create_resp.json()["id"]

        # Update title
        with mock_webui_user(id="user-2"):
            update_resp = self.fast_api_client.post(
                self.create_url(f"/{chat_id}"),
                json={"chat": {"title": "Updated Title", "history": {"messages": {}}}},
            )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Updated Title"

        # Verify via GET
        with mock_webui_user(id="user-2"):
            get_resp = self.fast_api_client.get(self.create_url(f"/{chat_id}"))
        assert get_resp.json()["title"] == "Updated Title"

    # ------------------------------------------------------------------
    # Test 3: archive and unarchive a chat
    # ------------------------------------------------------------------
    def test_toggle_chat_archive(self):
        """
        Calling the archive toggle endpoint twice should flip archived to
        True then back to False, leaving the chat otherwise unchanged.
        """
        # Create
        with mock_webui_user(id="user-3"):
            create_resp = self.fast_api_client.post(
                self.create_url("/new"),
                json={"chat": {"title": "Archive Me", "history": {"messages": {}}}},
            )
        assert create_resp.status_code == 200
        chat_id = create_resp.json()["id"]
        assert create_resp.json()["archived"] is False

        # Archive (first toggle)
        with mock_webui_user(id="user-3"):
            archive_resp = self.fast_api_client.get(
                self.create_url(f"/{chat_id}/archive/toggle")
            )
        assert archive_resp.status_code == 200
        assert archive_resp.json()["archived"] is True

        # Unarchive (second toggle)
        with mock_webui_user(id="user-3"):
            unarchive_resp = self.fast_api_client.get(
                self.create_url(f"/{chat_id}/archive/toggle")
            )
        assert unarchive_resp.status_code == 200
        assert unarchive_resp.json()["archived"] is False

    # ------------------------------------------------------------------
    # Test 4: delete a chat
    # ------------------------------------------------------------------
    def test_delete_chat(self):
        """
        delete_chat_by_id should remove the chat so that a subsequent
        get_chat_by_id returns 404.
        """
        # Create
        with mock_webui_user(id="user-4"):
            create_resp = self.fast_api_client.post(
                self.create_url("/new"),
                json={"chat": {"title": "Delete Me", "history": {"messages": {}}}},
            )
        assert create_resp.status_code == 200
        chat_id = create_resp.json()["id"]

        # Delete
        with mock_webui_user(id="user-4"):
            delete_resp = self.fast_api_client.delete(self.create_url(f"/{chat_id}"))
        assert delete_resp.status_code == 200

        # Confirm it's gone
        with mock_webui_user(id="user-4"):
            get_resp = self.fast_api_client.get(self.create_url(f"/{chat_id}"))
        assert get_resp.status_code == 404

    # ------------------------------------------------------------------
    # Test 5: user cannot access another user's chat
    # ------------------------------------------------------------------
    def test_user_cannot_access_other_users_chat(self):
        """
        get_chat_by_id_and_user_id should not return a chat that belongs
        to a different user — enforcing basic ownership isolation.
        """
        # Create chat as user-5
        with mock_webui_user(id="user-5"):
            create_resp = self.fast_api_client.post(
                self.create_url("/new"),
                json={"chat": {"title": "Private Chat", "history": {"messages": {}}}},
            )
        assert create_resp.status_code == 200
        chat_id = create_resp.json()["id"]

        # Try to access it as user-6
        with mock_webui_user(id="user-6"):
            get_resp = self.fast_api_client.get(self.create_url(f"/{chat_id}"))

        # Should be forbidden or not found — not 200
        assert get_resp.status_code in (403, 404)

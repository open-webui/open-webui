import pytest
from open_webui.test.util.abstract_integration_test import AbstractIntegrationTest
from open_webui.test.util.mock_user import mock_user

@pytest.fixture
def postgres_client(postgres_client):
    from open_webui.models.users import Users

    users = Users
    users.insert_new_user(
        id="1",
        name="user 1",
        email="user1@openwebui.com",
        profile_image_url="/user1.png",
        role="user",
    )

    yield postgres_client

class TestNotes(AbstractIntegrationTest):
    BASE_PATH = "/api/v1/notes"

    @pytest.mark.asyncio
    async def test_create_note(self, postgres_client):
        with mock_user(id="1"):
            response = await postgres_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0

        with mock_user(id="1"):
            response = await postgres_client.post(
                self.create_url("/create"),
                json={
                    "title": "my-note",
                    "data": {
                        "key": "value"
                    }
                }
            )
        assert response.status_code == 200

        note_id = response.json()["id"]

        with mock_user(id="1"):
            response = await postgres_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 1

        with mock_user(id="1"):
            response = await postgres_client.get(self.create_url("/list"))
        assert response.status_code == 200
        assert len(response.json()) == 1

        assert response.json()[0]["title"] == "my-note"

        with mock_user(id="1"):
            response = await postgres_client.get(
                self.create_url(f"/{note_id}")
            )

        assert response.json()["title"] == "my-note"
        assert response.json()["data"] == {"key": "value"}

        with mock_user(id="1"):
            response = await postgres_client.post(
                self.create_url(f"/{note_id}/update"),
                json={
                    "title": "my-note",
                    "data": {
                        "key": "value2"
                    }
                }
            )
        assert response.status_code == 200

        with mock_user(id="1"):
            response = await postgres_client.get(
                self.create_url(f"/{note_id}")
            )

        assert response.json()["title"] == "my-note"
        assert response.json()["data"] == {"key": "value2"}

        with mock_user(id="1"):
            response = await postgres_client.delete(
                self.create_url(f"/{note_id}/delete")
            )

        with mock_user(id="1"):
            response = await postgres_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0

"""
GetNotes
ListNotes
CreateNewNote
GetNoteById
UpdateNoteById
DeleteNoteById
"""

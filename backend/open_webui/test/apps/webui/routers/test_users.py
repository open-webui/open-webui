import pytest
from open_webui.test.util.abstract_integration_test import AbstractIntegrationTest
from open_webui.test.util.mock_user import mock_user



def _get_user_by_id(data, param):
    return next((item for item in data if item["id"] == param), None)


def _assert_user(data, id, **kwargs):
    user = _get_user_by_id(data, id)
    assert user is not None
    comparison_data = {
        "name": f"user {id}",
        "email": f"user{id}@openwebui.com",
        "profile_image_url": f"/user{id}.png",
        "role": "user",
        **kwargs,
    }
    for key, value in comparison_data.items():
        assert user[key] == value

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
    users.insert_new_user(
        id="2",
        name="user 2",
        email="user2@openwebui.com",
        profile_image_url="/user2.png",
        role="user",
    )

    yield postgres_client


class TestUsers(AbstractIntegrationTest):
    BASE_PATH = "/api/v1/users"


    def test_users(self, postgres_client):
        self.fast_api_client = postgres_client
        app = self.fast_api_client.app
        # Get all users
        with mock_user(app, id="3"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()
        _assert_user(data["users"], "1")
        _assert_user(data["users"], "2")

        # update role
        with mock_user(app, id="3"):
            response = self.fast_api_client.post(
                self.create_url("/2/update"), json={"role": "admin", "name": "user 2", "email": "user2@openwebui.com", "profile_image_url": "/user2.png"}
            )
    
        assert response.status_code == 200
        _assert_user([response.json()], "2", role="admin")

        # Get all users
        with mock_user(app, id="3"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()
        _assert_user(data["users"], "1")
        _assert_user(data["users"], "2", role="admin")

        # Get (empty) user settings
        with mock_user(app, id="2"):
            response = self.fast_api_client.get(self.create_url("/user/settings"))
        assert response.status_code == 200
        assert response.json() is None

        # Update user settings
        with mock_user(app, id="2"):
            response = self.fast_api_client.post(
                self.create_url("/user/settings/update"),
                json={
                    "ui": {"attr1": "value1", "attr2": "value2"},
                    "model_config": {"attr3": "value3", "attr4": "value4"},
                },
            )
        assert response.status_code == 200

        # Get user settings
        with mock_user(app, id="2"):
            response = self.fast_api_client.get(self.create_url("/user/settings"))
        assert response.status_code == 200
        assert response.json() == {
            "ui": {"attr1": "value1", "attr2": "value2"},
            "model_config": {"attr3": "value3", "attr4": "value4"},
        }

        # Get (empty) user info
        with mock_user(app, id="1"):
            response = self.fast_api_client.get(self.create_url("/user/info"))
        assert response.status_code == 200
        assert response.json() is None

        # Update user info
        with mock_user(app, id="1"):
            response = self.fast_api_client.post(
                self.create_url("/user/info/update"),
                json={"attr1": "value1", "attr2": "value2"},
            )
        assert response.status_code == 200

        # Get user info
        with mock_user(app, id="1"):
            response = self.fast_api_client.get(self.create_url("/user/info"))
        assert response.status_code == 200
        assert response.json() == {"attr1": "value1", "attr2": "value2"}

        # Get user by id
        with mock_user(app, id="1"):
            response = self.fast_api_client.get(self.create_url("/2"))
        assert response.status_code == 200
        assert response.json() == {"active": False, "name": "user 2", "profile_image_url": "/user2.png"}

        # Update user by id
        with mock_user(app, id="2"):
            response = self.fast_api_client.post(
                self.create_url("/2/update"),
                json={
                    "role": "admin",
                    "name": "user 2 updated",
                    "email": "user2-updated@openwebui.com",
                    "profile_image_url": "/user2-updated.png",
                },
            )
        assert response.status_code == 200

        # Get all users
        with mock_user(app, id="3"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()
        _assert_user(data["users"], "1")
        _assert_user(
            data["users"],
            "2",
            role="admin",
            name="user 2 updated",
            email="user2-updated@openwebui.com",
            profile_image_url="/user2-updated.png",
        )

        # Delete user by id
        with mock_user(app, id="1"):
            response = self.fast_api_client.delete(self.create_url("/2"))
        assert response.status_code == 200

        # Get all users
        with mock_user(app, id="3"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 1
        _assert_user(data["users"], "1")

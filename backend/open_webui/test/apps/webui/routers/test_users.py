from open_webui.test.util.abstract_integration_test import AbstractPostgresTest
from open_webui.test.util.mock_user import mock_webui_user


class TestUsers(AbstractPostgresTest):
    BASE_PATH = "/api/v1/users/"

    @classmethod
    def setup_class(cls):
        super().setup_class()
        from open_webui.models.users import Users

        cls.users = Users

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id="1",
            name="user 1",
            email="user1@openwebui.com",
            profile_image_url="/user1.png",
            role="user",
        )
        self.users.insert_new_user(
            id="2",
            name="user 2",
            email="user2@openwebui.com",
            profile_image_url="/user2.png",
            role="user",
        )

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id="1",
            name="user 1",
            email="user1@openwebui.com",
            profile_image_url="/user1.png",
            role="user",
        )
        self.users.insert_new_user(
            id="2",
            name="user 2",
            email="user2@openwebui.com",
            profile_image_url="/user2.png",
            role="user",
        )

    def test_users(self):
        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()

        user1 = next((u for u in data if u["id"] == "1"), None)
        assert user1 is not None
        assert user1["name"] == "user 1"
        assert user1["email"] == "user1@openwebui.com"

        user2 = next((u for u in data if u["id"] == "2"), None)
        assert user2 is not None
        assert user2["name"] == "user 2"

        # update role
        with mock_webui_user(id="3"):
            response = self.fast_api_client.post(
                self.create_url("/update/role"), json={"id": "2", "role": "admin"}
            )
        assert response.status_code == 200
        user = response.json()
        assert user["id"] == "2"
        assert user["role"] == "admin"

        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 2
        users = response.json()
        assert len(users) == 2

        user1 = next((u for u in users if u["id"] == "1"), None)
        assert user1["name"] == "user 1"

        user2 = next((u for u in users if u["id"] == "2"), None)
        assert user2["name"] == "user 2"
        assert user2["role"] == "admin"

        # Get (empty) user settings
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/user/settings"))
        assert response.status_code == 200
        assert response.json() is None

        # Update user settings
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/user/settings/update"),
                json={
                    "ui": {"attr1": "value1", "attr2": "value2"},
                    "model_config": {"attr3": "value3", "attr4": "value4"},
                },
            )
        assert response.status_code == 200

        # Get user settings
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/user/settings"))
        assert response.status_code == 200
        data = response.json()
        assert data["ui"] == {"attr1": "value1", "attr2": "value2"}
        assert data["model_config"] == {"attr3": "value3", "attr4": "value4"}

        # Get (empty) user info
        with mock_webui_user(id="1"):
            response = self.fast_api_client.get(self.create_url("/user/info"))
        assert response.status_code == 200
        assert response.json() is None

        # Update user info
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/user/info/update"),
                json={"attr1": "value1", "attr2": "value2"},
            )
        assert response.status_code == 200

        # Get user info
        with mock_webui_user(id="1"):
            response = self.fast_api_client.get(self.create_url("/user/info"))
        assert response.status_code == 200
        assert response.json()["attr1"] == "value1"
        assert response.json()["attr2"] == "value2"

        # Get user by id
        with mock_webui_user(id="1"):
            response = self.fast_api_client.get(self.create_url("/2"))
        assert response.status_code == 200
        assert response.json()["name"] == "user 2"
        assert response.json()["profile_image_url"] == "/user2.png"

        # Update user by id
        with mock_webui_user(id="1", role="admin"):
            response = self.fast_api_client.post(
                self.create_url("/2/update"),
                json={
                    "name": "user 2 updated",
                    "email": "user2-updated@openwebui.com",
                    "profile_image_url": "/user2-updated.png",
                },
            )
        assert response.status_code == 200

        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()

        user1 = next((u for u in data if u["id"] == "1"), None)
        assert user1["name"] == "user 1"

        user2 = next((u for u in data if u["id"] == "2"), None)
        assert user2["name"] == "user 2 updated"
        assert user2["role"] == "admin"

        # Delete user by id
        with mock_webui_user(id="1"):
            response = self.fast_api_client.delete(self.create_url("/2"))
        assert response.status_code == 200

        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 1

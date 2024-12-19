from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


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


class TestUsers(AbstractPostgresTest):
    BASE_PATH = "/api/v1/users"

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

    def test_users(self):
        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()
        _assert_user(data, "1")
        _assert_user(data, "2")

        # update role
        with mock_webui_user(id="3"):
            response = self.fast_api_client.post(
                self.create_url("/update/role"), json={"id": "2", "role": "admin"}
            )
        assert response.status_code == 200
        _assert_user([response.json()], "2", role="admin")

        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 2
        data = response.json()
        _assert_user(data, "1")
        _assert_user(data, "2", role="admin")

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
        assert response.json() == {
            "ui": {"attr1": "value1", "attr2": "value2"},
            "model_config": {"attr3": "value3", "attr4": "value4"},
        }

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
        assert response.json() == {"attr1": "value1", "attr2": "value2"}

        # Get user by id
        with mock_webui_user(id="1"):
            response = self.fast_api_client.get(self.create_url("/2"))
        assert response.status_code == 200
        assert response.json() == {"name": "user 2", "profile_image_url": "/user2.png"}

        # Update user by id
        with mock_webui_user(id="1"):
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
        _assert_user(data, "1")
        _assert_user(
            data,
            "2",
            role="admin",
            name="user 2 updated",
            email="user2-updated@openwebui.com",
            profile_image_url="/user2-updated.png",
        )

        # Delete user by id
        with mock_webui_user(id="1"):
            response = self.fast_api_client.delete(self.create_url("/2"))
        assert response.status_code == 200

        # Get all users
        with mock_webui_user(id="3"):
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert len(response.json()) == 1
        data = response.json()
        _assert_user(data, "1")

from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestAuths(AbstractPostgresTest):
    BASE_PATH = "/api/v1/auths"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.auths import Auths
        from open_webui.models.users import Users

        cls.users = Users
        cls.auths = Auths

    def test_get_session_user(self):
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert response.json() == {
            "id": "1",
            "name": "John Doe",
            "email": "john.doe@openwebui.com",
            "role": "user",
            "profile_image_url": "/user.png",
        }

    def test_update_profile(self):
        from open_webui.utils.auth import get_password_hash

        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=get_password_hash("old_password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )

        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(
                self.create_url("/update/profile"),
                json={"name": "John Doe 2", "profile_image_url": "/user2.png"},
            )
        assert response.status_code == 200
        db_user = self.users.get_user_by_id(user.id)
        assert db_user.name == "John Doe 2"
        assert db_user.profile_image_url == "/user2.png"

    def test_update_password(self):
        from open_webui.utils.auth import get_password_hash

        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=get_password_hash("old_password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )

        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(
                self.create_url("/update/password"),
                json={"password": "old_password", "new_password": "new_password"},
            )
        assert response.status_code == 200

        old_auth = self.auths.authenticate_user(
            "john.doe@openwebui.com", "old_password"
        )
        assert old_auth is None
        new_auth = self.auths.authenticate_user(
            "john.doe@openwebui.com", "new_password"
        )
        assert new_auth is not None

    def test_signin(self):
        from open_webui.utils.auth import get_password_hash

        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        response = self.fast_api_client.post(
            self.create_url("/signin"),
            json={"email": "john.doe@openwebui.com", "password": "password"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["name"] == "John Doe"
        assert data["email"] == "john.doe@openwebui.com"
        assert data["role"] == "user"
        assert data["profile_image_url"] == "/user.png"
        assert data["token"] is not None and len(data["token"]) > 0
        assert data["token_type"] == "Bearer"

    def test_signup(self):
        response = self.fast_api_client.post(
            self.create_url("/signup"),
            json={
                "name": "John Doe",
                "email": "john.doe@openwebui.com",
                "password": "password",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None and len(data["id"]) > 0
        assert data["name"] == "John Doe"
        assert data["email"] == "john.doe@openwebui.com"
        assert data["role"] in ["admin", "user", "pending"]
        assert data["profile_image_url"] == "/user.png"
        assert data["token"] is not None and len(data["token"]) > 0
        assert data["token_type"] == "Bearer"

    def test_add_user(self):
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/add"),
                json={
                    "name": "John Doe 2",
                    "email": "john.doe2@openwebui.com",
                    "password": "password2",
                    "role": "admin",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None and len(data["id"]) > 0
        assert data["name"] == "John Doe 2"
        assert data["email"] == "john.doe2@openwebui.com"
        assert data["role"] == "admin"
        assert data["profile_image_url"] == "/user.png"
        assert data["token"] is not None and len(data["token"]) > 0
        assert data["token_type"] == "Bearer"

    def test_get_admin_details(self):
        self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/admin/details"))

        assert response.status_code == 200
        assert response.json() == {
            "name": "John Doe",
            "email": "john.doe@openwebui.com",
        }

    def test_create_api_key_(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(self.create_url("/api_key"))
        assert response.status_code == 200
        data = response.json()
        assert data["api_key"] is not None
        assert len(data["api_key"]) > 0

    def test_create_api_key_new_endpoint(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com", 
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(
                self.create_url("/api_keys"), 
                json={"name": "Test Key"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["api_key"] is not None
        assert data["name"] == "Test Key"
        assert data["id"] is not None
        assert data["created_at"] is not None

    def test_delete_api_key(self):
        from open_webui.models.api_keys import ApiKeys
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        # Create an API key using the new system
        api_key_record = ApiKeys.create_api_key(user.id, "abc", "Test Key")
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.delete(self.create_url("/api_key"))
        assert response.status_code == 200
        assert response.json() == True
        # Check that the API key was deleted
        remaining_keys = ApiKeys.get_api_keys_by_user_id(user.id)
        assert len(remaining_keys) == 0

    def test_get_api_key(self):
        from open_webui.models.api_keys import ApiKeys
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        # Create an API key using the new system
        api_key_record = ApiKeys.create_api_key(user.id, "abc", "Test Key")
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.get(self.create_url("/api_key"))
        assert response.status_code == 200
        assert response.json() == {"api_key": "abc"}

    def test_get_api_keys_new_endpoint(self):
        from open_webui.models.api_keys import ApiKeys
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        # Create multiple API keys
        ApiKeys.create_api_key(user.id, "key1", "Test Key 1")
        ApiKeys.create_api_key(user.id, "key2", "Test Key 2")
        
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.get(self.create_url("/api_keys"))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["api_key"] in ["key1", "key2"]
        assert data[1]["api_key"] in ["key1", "key2"]
        # Check that expiry fields are included
        assert "expires_at" in data[0]
        assert "is_expired" in data[0]

    def test_api_key_expiry_info(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.get(self.create_url("/api_keys/expires_in"))
        assert response.status_code == 200
        data = response.json()
        assert "expiry" in data
        assert "expiry_enabled" in data
        assert "expiry_formatted" in data

    def test_api_key_expiration_check(self):
        from open_webui.models.api_keys import ApiKeys
        import time
        
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        
        # Create an API key
        api_key_record = ApiKeys.create_api_key(user.id, "test_key", "Test Key")
        
        # Test expiration checking
        assert not ApiKeys.is_api_key_expired(api_key_record, 0)  # No expiry
        assert not ApiKeys.is_api_key_expired(api_key_record, 3600)  # 1 hour expiry, should not be expired
        
        # Test expiration timestamp
        expires_at = ApiKeys.get_expiration_timestamp(api_key_record, 3600)
        assert expires_at == api_key_record.created_at + 3600
        assert ApiKeys.get_expiration_timestamp(api_key_record, 0) is None

    def test_cleanup_expired_api_keys_admin_only(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="user",  # Regular user, not admin
        )
        
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(self.create_url("/api_keys/cleanup"))
        assert response.status_code == 401  # Should be unauthorized for non-admin

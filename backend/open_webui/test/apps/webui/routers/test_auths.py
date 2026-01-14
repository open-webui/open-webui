from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user
from unittest.mock import patch, MagicMock


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

    def test_delete_api_key(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        self.users.update_user_api_key_by_id(user.id, "abc")
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.delete(self.create_url("/api_key"))
        assert response.status_code == 200
        assert response.json() == True
        db_user = self.users.get_user_by_id(user.id)
        assert db_user.api_key is None

    def test_get_api_key(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        self.users.update_user_api_key_by_id(user.id, "abc")
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.get(self.create_url("/api_key"))
        assert response.status_code == 200
        assert response.json() == {"api_key": "abc"}

    def test_signout_basic(self):
        """Test basic signout without OAuth session"""
        response = self.fast_api_client.get(self.create_url("/signout"))
        assert response.status_code == 200
        assert response.json()["status"] == True

    def test_signout_with_redirect_url(self):
        """Test signout with WEBUI_AUTH_SIGNOUT_REDIRECT_URL configured"""
        with patch(
            "open_webui.routers.auths.WEBUI_AUTH_SIGNOUT_REDIRECT_URL",
            "https://example.com/logout-redirect",
        ):
            response = self.fast_api_client.get(self.create_url("/signout"))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == True
        assert data["redirect_url"] == "https://example.com/logout-redirect"

    def test_signout_with_custom_sso_logout_url(self):
        """Test signout with WEBUI_AUTH_SSO_LOGOUT_URL configured (e.g., for AWS Cognito)"""
        # Set a cookie to simulate OAuth session
        self.fast_api_client.cookies.set("oauth_session_id", "test-session-id")

        with patch(
            "open_webui.routers.auths.WEBUI_AUTH_SSO_LOGOUT_URL",
            "https://myapp.auth.us-east-1.amazoncognito.com/logout?client_id=abc123&logout_uri=https://myapp.com",
        ):
            response = self.fast_api_client.get(self.create_url("/signout"))

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == True
        assert (
            data["redirect_url"]
            == "https://myapp.auth.us-east-1.amazoncognito.com/logout?client_id=abc123&logout_uri=https://myapp.com"
        )

        # Clean up
        self.fast_api_client.cookies.clear()

    def test_signout_sso_logout_url_takes_precedence_over_openid(self):
        """Test that WEBUI_AUTH_SSO_LOGOUT_URL takes precedence over OpenID end_session_endpoint"""
        # Set a cookie to simulate OAuth session
        self.fast_api_client.cookies.set("oauth_session_id", "test-session-id")

        # When both SSO_LOGOUT_URL is set, it should be used instead of trying to fetch OpenID config
        with patch(
            "open_webui.routers.auths.WEBUI_AUTH_SSO_LOGOUT_URL",
            "https://custom-sso-logout.com",
        ):
            with patch("open_webui.routers.auths.OAuthSessions") as mock_oauth_sessions:
                # Even with a valid session, SSO_LOGOUT_URL should be used
                mock_session = MagicMock()
                mock_session.provider = "cognito"
                mock_session.token = {"id_token": "test-token"}
                mock_oauth_sessions.get_session_by_id.return_value = mock_session

                response = self.fast_api_client.get(self.create_url("/signout"))

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == True
        assert data["redirect_url"] == "https://custom-sso-logout.com"

        # Clean up
        self.fast_api_client.cookies.clear()

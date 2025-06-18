import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from open_webui.models.users import User
from open_webui.routers.auths import (
    get_session_user,
)
import open_webui.env

def get_mock_user(**kwargs) -> User:
    user_parameters = {
        "id": "47",
        "name": "John Doe",
        "email": "john.doe@openwebui.com",
        "role": "user",
        "profile_image_url": "/user.png",
        "last_active_at": 1627351200,
        "updated_at": 1627351200,
        "created_at": 162735120,
        **kwargs,
    }

    return User(**user_parameters)

class TestAuths:
    @pytest.fixture
    def mock_request(self):
        mock_request = MagicMock()
        mock_request.app.state.config.JWT_EXPIRES_IN = "1h"
        mock_request.app.state.config.USER_PERMISSIONS = ["permission1", "permission2"]
        return mock_request

    @pytest.fixture
    def mock_response(self):
        mock_response = MagicMock()
        return mock_response

    @pytest.fixture
    def mock_user(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "email@example.com"
        mock_user.name = "John Doe"
        mock_user.role = "admin"
        mock_user.created_at = "2022-01-01"
        mock_user.profile_image_url = "https://example.com/image.jpg"
        return mock_user

    @pytest.mark.asyncio
    async def test_get_session_user(self, monkeypatch, mock_request, mock_response, mock_user):
        monkeypatch.setattr("open_webui.routers.auths.WEBUI_SESSION_COOKIE_SAME_SITE", 'Strict', raising = True)
        monkeypatch.setattr("open_webui.routers.auths.WEBUI_SESSION_COOKIE_SECURE", True, raising = True)

        # Patch the function where it was imported _to_
        # (not where it is defined and exported from)
        monkeypatch.setattr("open_webui.routers.auths.pseudonymized_user_id", lambda _user: "pseudonymized-user-id")
        monkeypatch.setattr("open_webui.routers.auths.get_permissions", lambda _id, _default_perms: { "read": True, "write": False })

        mock_get_current_user = MagicMock(return_value=mock_user)
        result = await get_session_user(mock_request, mock_response, user=mock_get_current_user())
        mock_response.set_cookie.assert_called_once()

        args, kwargs = mock_response.set_cookie.call_args

        assert kwargs["key"] == "token"
        assert kwargs["httponly"] is True
        assert kwargs["samesite"] == "Strict"
        assert kwargs["secure"] is True

        assert result["token"] is not None
        assert result["token_type"] == "Bearer"
        assert result["expires_at"] is not None
        assert result["id"] == mock_user.id
        assert result["email"] == mock_user.email
        assert result["name"] == mock_user.name
        assert result["role"] == mock_user.role
        assert result["created_at"] == mock_user.created_at
        assert result["pseudonymized_user_id"] == "pseudonymized-user-id"
        assert result["profile_image_url"] == mock_user.profile_image_url
        assert result["permissions"] == { "read": True, "write": False }


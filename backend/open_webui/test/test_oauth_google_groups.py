import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from open_webui.utils.oauth import OAuthManager
from open_webui.config import AppConfig


class TestOAuthGoogleGroups:
    """Basic tests for Google OAuth Groups functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.oauth_manager = OAuthManager(app=MagicMock())
        
    @pytest.mark.asyncio
    async def test_fetch_google_groups_success(self):
        """Test successful Google groups fetching with proper aiohttp mocking"""
        # Mock response data from Google Cloud Identity API
        mock_response_data = {
            "memberships": [
                {
                    "groupKey": {"id": "admin@company.com"},
                    "group": "groups/123",
                    "displayName": "Admin Group"
                },
                {
                    "groupKey": {"id": "users@company.com"},
                    "group": "groups/456", 
                    "displayName": "Users Group"
                }
            ]
        }
        
        # Create properly structured async mocks
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        # Mock the async context manager for session.get()
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_context)
        
        # Mock the async context manager for ClientSession
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session_context):
            groups = await self.oauth_manager._fetch_google_groups_via_cloud_identity(
                access_token="test_token",
                user_email="user@company.com"
            )
        
        # Verify the results
        assert groups == ["admin@company.com", "users@company.com"]
        
        # Verify the HTTP call was made correctly
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        
        # Check the URL contains the user email (URL encoded)
        url_arg = call_args[0][0]  # First positional argument
        assert "user%40company.com" in url_arg  # @ is encoded as %40
        assert "searchTransitiveGroups" in url_arg
        
        # Check headers contain the bearer token
        headers_arg = call_args[1]["headers"]  # headers keyword argument
        assert headers_arg["Authorization"] == "Bearer test_token"
        assert headers_arg["Content-Type"] == "application/json"
        
    @pytest.mark.asyncio
    async def test_fetch_google_groups_api_error(self):
        """Test handling of API errors when fetching groups"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="Permission denied")
        
        # Mock the async context manager for session.get()
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_context)
        
        # Mock the async context manager for ClientSession
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session_context):
            groups = await self.oauth_manager._fetch_google_groups_via_cloud_identity(
                access_token="test_token",
                user_email="user@company.com"
            )
        
        # Should return empty list on error
        assert groups == []
        
    @pytest.mark.asyncio
    async def test_fetch_google_groups_network_error(self):
        """Test handling of network errors when fetching groups"""
        # Mock the session that raises an exception when get() is called
        mock_session = MagicMock()
        mock_session.get.side_effect = aiohttp.ClientError("Network error")
        
        # Mock the async context manager for ClientSession
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session_context):
            groups = await self.oauth_manager._fetch_google_groups_via_cloud_identity(
                access_token="test_token", 
                user_email="user@company.com"
            )
        
        # Should return empty list on network error
        assert groups == []
        
    @pytest.mark.asyncio
    async def test_get_user_role_with_google_groups(self):
        """Test role assignment using Google groups"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = True
        mock_config.OAUTH_ROLES_CLAIM = "groups"
        mock_config.OAUTH_ALLOWED_ROLES = ["users@company.com"]
        mock_config.OAUTH_ADMIN_ROLES = ["admin@company.com"]
        mock_config.DEFAULT_USER_ROLE = "pending"
        mock_config.OAUTH_EMAIL_CLAIM = "email"
        
        user_data = {"email": "user@company.com"}
        
        # Mock Google OAuth scope check and Users class
        with patch("open_webui.utils.oauth.auth_manager_config", mock_config), \
             patch("open_webui.utils.oauth.GOOGLE_OAUTH_SCOPE") as mock_scope, \
             patch("open_webui.utils.oauth.Users") as mock_users, \
             patch.object(self.oauth_manager, "_fetch_google_groups_via_cloud_identity") as mock_fetch:
            
            mock_scope.value = "openid email profile https://www.googleapis.com/auth/cloud-identity.groups.readonly"
            mock_fetch.return_value = ["admin@company.com", "users@company.com"]
            mock_users.get_num_users.return_value = 5  # Not first user
            
            role = await self.oauth_manager.get_user_role(
                user=None,
                user_data=user_data,
                provider="google",
                access_token="test_token"
            )
            
            # Should assign admin role since user is in admin group
            assert role == "admin"
            mock_fetch.assert_called_once_with("test_token", "user@company.com")
            
    @pytest.mark.asyncio
    async def test_get_user_role_fallback_to_claims(self):
        """Test fallback to traditional claims when Google groups fail"""
        mock_config = MagicMock()
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = True
        mock_config.OAUTH_ROLES_CLAIM = "groups"
        mock_config.OAUTH_ALLOWED_ROLES = ["users"]
        mock_config.OAUTH_ADMIN_ROLES = ["admin"]
        mock_config.DEFAULT_USER_ROLE = "pending"
        mock_config.OAUTH_EMAIL_CLAIM = "email"
        
        user_data = {
            "email": "user@company.com",
            "groups": ["users"]
        }
        
        with patch("open_webui.utils.oauth.auth_manager_config", mock_config), \
             patch("open_webui.utils.oauth.GOOGLE_OAUTH_SCOPE") as mock_scope, \
             patch("open_webui.utils.oauth.Users") as mock_users, \
             patch.object(self.oauth_manager, "_fetch_google_groups_via_cloud_identity") as mock_fetch:
            
            # Mock scope without Cloud Identity
            mock_scope.value = "openid email profile"
            mock_users.get_num_users.return_value = 5  # Not first user
            
            role = await self.oauth_manager.get_user_role(
                user=None,
                user_data=user_data,
                provider="google",
                access_token="test_token"
            )
            
            # Should use traditional claims since Cloud Identity scope not present
            assert role == "user"
            mock_fetch.assert_not_called()
            
    @pytest.mark.asyncio 
    async def test_get_user_role_non_google_provider(self):
        """Test that non-Google providers use traditional claims"""
        mock_config = MagicMock()
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = True
        mock_config.OAUTH_ROLES_CLAIM = "roles"
        mock_config.OAUTH_ALLOWED_ROLES = ["user"]
        mock_config.OAUTH_ADMIN_ROLES = ["admin"]
        mock_config.DEFAULT_USER_ROLE = "pending"
        
        user_data = {"roles": ["user"]}
        
        with patch("open_webui.utils.oauth.auth_manager_config", mock_config), \
             patch("open_webui.utils.oauth.Users") as mock_users, \
             patch.object(self.oauth_manager, "_fetch_google_groups_via_cloud_identity") as mock_fetch:
            
            mock_users.get_num_users.return_value = 5  # Not first user
            
            role = await self.oauth_manager.get_user_role(
                user=None,
                user_data=user_data,
                provider="microsoft",
                access_token="test_token"
            )
            
            # Should use traditional claims for non-Google providers
            assert role == "user"
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_groups_with_google_groups(self):
        """Test group management using Google groups from user_data"""
        mock_config = MagicMock()
        mock_config.OAUTH_GROUPS_CLAIM = "groups"
        mock_config.OAUTH_BLOCKED_GROUPS = "[]"
        mock_config.ENABLE_OAUTH_GROUP_CREATION = False
        
        # Mock user with Google groups data
        mock_user = MagicMock()
        mock_user.id = "user123"
        
        user_data = {
            "google_groups": ["developers@company.com", "employees@company.com"]
        }
        
        # Mock existing groups and user groups
        mock_existing_group = MagicMock()
        mock_existing_group.name = "developers@company.com"
        mock_existing_group.id = "group1"
        mock_existing_group.user_ids = []
        mock_existing_group.permissions = {"read": True}
        mock_existing_group.description = "Developers group"
        
        with patch("open_webui.utils.oauth.auth_manager_config", mock_config), \
             patch("open_webui.utils.oauth.Groups") as mock_groups:
            
            mock_groups.get_groups_by_member_id.return_value = []
            mock_groups.get_groups.return_value = [mock_existing_group]
            
            await self.oauth_manager.update_user_groups(
                user=mock_user,
                user_data=user_data,
                default_permissions={"read": True}
            )
            
            # Should use Google groups instead of traditional claims
            mock_groups.get_groups_by_member_id.assert_called_once_with("user123")
            mock_groups.update_group_by_id.assert_called()

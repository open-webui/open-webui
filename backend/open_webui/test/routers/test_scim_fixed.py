"""
Fixed tests for SCIM 2.0 endpoints with proper authentication mocking
"""

import json
import pytest
from unittest.mock import patch, MagicMock, Mock
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import time

from open_webui.main import app
from open_webui.models.users import UserModel
from open_webui.models.groups import GroupModel


class TestSCIMEndpointsFixed:
    """Test SCIM 2.0 endpoints with proper auth mocking"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def admin_token(self):
        """Mock admin token for authentication"""
        return "mock-admin-token"
    
    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user"""
        return UserModel(
            id="admin-123",
            name="Admin User",
            email="admin@example.com",
            role="admin",
            profile_image_url="/user.png",
            created_at=1234567890,
            updated_at=1234567890,
            last_active_at=1234567890
        )
    
    @pytest.fixture
    def mock_user(self):
        """Mock regular user"""
        return UserModel(
            id="user-456",
            name="Test User",
            email="test@example.com",
            role="user",
            profile_image_url="/user.png",
            created_at=1234567890,
            updated_at=1234567890,
            last_active_at=1234567890
        )
    
    @pytest.fixture
    def mock_group(self):
        """Mock group"""
        return GroupModel(
            id="group-789",
            user_id="admin-123",
            name="Test Group",
            description="Test group description",
            user_ids=["user-456"],
            created_at=1234567890,
            updated_at=1234567890
        )
    
    @pytest.fixture
    def auth_headers(self, admin_token):
        """Authorization headers for requests"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    @pytest.fixture
    def valid_token_data(self):
        """Valid token data"""
        return {
            "id": "admin-123",
            "email": "admin@example.com",
            "name": "Admin User",
            "role": "admin",
            "exp": int(time.time()) + 3600  # Valid for 1 hour
        }
    
    # Service Provider Config Tests (No auth required)
    def test_get_service_provider_config(self, client):
        """Test getting SCIM Service Provider Configuration"""
        response = client.get("/api/v1/scim/v2/ServiceProviderConfig")
        assert response.status_code == 200
        
        data = response.json()
        assert "schemas" in data
        assert data["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]
        assert "patch" in data
        assert data["patch"]["supported"] == True
        assert "filter" in data
        assert data["filter"]["supported"] == True
    
    # Mock the entire authentication dependency
    @patch('open_webui.routers.scim.get_scim_auth')
    @patch('open_webui.models.users.Users.get_users')
    @patch('open_webui.models.groups.Groups.get_groups_by_member_id')
    def test_get_users_with_mocked_auth(self, mock_get_groups, mock_get_users, mock_get_scim_auth, client, auth_headers, mock_user):
        """Test listing SCIM users with mocked authentication"""
        # Mock the authentication to always return True
        mock_get_scim_auth.return_value = True
        
        # Mock the database calls
        mock_get_users.return_value = {
            "users": [mock_user],
            "total": 1
        }
        mock_get_groups.return_value = []
        
        response = client.get("/api/v1/scim/v2/Users", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
        assert data["totalResults"] == 1
        assert data["itemsPerPage"] == 1
        assert data["startIndex"] == 1
        assert len(data["Resources"]) == 1
        
        user = data["Resources"][0]
        assert user["id"] == "user-456"
        assert user["userName"] == "test@example.com"
        assert user["displayName"] == "Test User"
        assert user["active"] == True
    
    # Alternative approach: Mock at the decode_token level
    def test_get_users_with_token_mock(self, client, auth_headers, mock_admin_user, mock_user, valid_token_data):
        """Test listing SCIM users with token decoding mocked"""
        with patch('open_webui.routers.scim.decode_token') as mock_decode_token, \
             patch('open_webui.models.users.Users.get_user_by_id') as mock_get_user_by_id, \
             patch('open_webui.models.users.Users.get_users') as mock_get_users, \
             patch('open_webui.models.groups.Groups.get_groups_by_member_id') as mock_get_groups:
            
            # Setup mocks
            mock_decode_token.return_value = valid_token_data
            mock_get_user_by_id.return_value = mock_admin_user
            mock_get_users.return_value = {
                "users": [mock_user],
                "total": 1
            }
            mock_get_groups.return_value = []
            
            response = client.get("/api/v1/scim/v2/Users", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["totalResults"] == 1
    
    # Test authentication failures
    def test_unauthorized_access_no_header(self, client):
        """Test accessing SCIM endpoints without authentication header"""
        response = client.get("/api/v1/scim/v2/Users")
        assert response.status_code == 401
    
    def test_unauthorized_access_invalid_token(self, client):
        """Test accessing SCIM endpoints with invalid token"""
        with patch('open_webui.routers.scim.decode_token') as mock_decode_token:
            mock_decode_token.return_value = None  # Invalid token
            
            response = client.get("/api/v1/scim/v2/Users", headers={"Authorization": "Bearer invalid-token"})
            assert response.status_code == 401
    
    def test_non_admin_access(self, client, mock_user):
        """Test accessing SCIM endpoints as non-admin user"""
        with patch('open_webui.routers.scim.decode_token') as mock_decode_token, \
             patch('open_webui.models.users.Users.get_user_by_id') as mock_get_user_by_id:
            
            # Mock token for non-admin user
            mock_decode_token.return_value = {"id": "user-456"}
            mock_get_user_by_id.return_value = mock_user  # Non-admin user
            
            response = client.get("/api/v1/scim/v2/Users", headers={"Authorization": "Bearer user-token"})
            assert response.status_code == 403
    
    # Create user test with proper mocking
    @patch('open_webui.routers.scim.get_scim_auth')
    @patch('open_webui.models.users.Users.get_user_by_email')
    @patch('open_webui.models.users.Users.insert_new_user')
    def test_create_user(self, mock_insert_user, mock_get_user_by_email, mock_get_scim_auth, client, auth_headers):
        """Test creating a SCIM user"""
        mock_get_scim_auth.return_value = True
        mock_get_user_by_email.return_value = None  # User doesn't exist
        
        new_user = UserModel(
            id="new-user-123",
            name="New User",
            email="newuser@example.com",
            role="user",
            profile_image_url="/user.png",
            created_at=1234567890,
            updated_at=1234567890,
            last_active_at=1234567890
        )
        mock_insert_user.return_value = new_user
        
        create_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "newuser@example.com",
            "displayName": "New User",
            "emails": [{"value": "newuser@example.com", "primary": True}],
            "active": True
        }
        
        response = client.post("/api/v1/scim/v2/Users", headers=auth_headers, json=create_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["userName"] == "newuser@example.com"
        assert data["displayName"] == "New User"
    
    # Group tests
    @patch('open_webui.routers.scim.get_scim_auth')
    @patch('open_webui.models.groups.Groups.get_groups')
    @patch('open_webui.models.users.Users.get_user_by_id')
    def test_get_groups(self, mock_get_user_by_id, mock_get_groups, mock_get_scim_auth, client, auth_headers, mock_group, mock_user):
        """Test listing SCIM groups"""
        mock_get_scim_auth.return_value = True
        mock_get_groups.return_value = [mock_group]
        mock_get_user_by_id.return_value = mock_user
        
        response = client.get("/api/v1/scim/v2/Groups", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
        assert data["totalResults"] == 1
        assert len(data["Resources"]) == 1
        
        group = data["Resources"][0]
        assert group["id"] == "group-789"
        assert group["displayName"] == "Test Group"
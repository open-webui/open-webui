"""
SCIM tests with dependency override approach
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import Depends

from open_webui.main import app
from open_webui.routers.scim import get_scim_auth
from open_webui.models.users import UserModel
from open_webui.models.groups import GroupModel


# Override the authentication dependency
async def override_get_scim_auth():
    """Override SCIM auth to always return True for tests"""
    return True


class TestSCIMWithOverride:
    """Test SCIM endpoints by overriding dependencies"""
    
    @pytest.fixture
    def client(self):
        # Override the dependency before creating the test client
        app.dependency_overrides[get_scim_auth] = override_get_scim_auth
        client = TestClient(app)
        yield client
        # Clean up
        app.dependency_overrides.clear()
    
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
    
    # Now test without worrying about auth
    @patch('open_webui.models.users.Users.get_users')
    @patch('open_webui.models.groups.Groups.get_groups_by_member_id')
    def test_get_users(self, mock_get_groups, mock_get_users, client, mock_user):
        """Test listing SCIM users"""
        mock_get_users.return_value = {
            "users": [mock_user],
            "total": 1
        }
        mock_get_groups.return_value = []
        
        # No need for auth headers since we overrode the dependency
        response = client.get("/api/v1/scim/v2/Users")
        assert response.status_code == 200
        
        data = response.json()
        assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
        assert data["totalResults"] == 1
        assert data["itemsPerPage"] == 1
        assert len(data["Resources"]) == 1
        
        user = data["Resources"][0]
        assert user["id"] == "user-456"
        assert user["userName"] == "test@example.com"
        assert user["displayName"] == "Test User"
        assert user["active"] == True
    
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.groups.Groups.get_groups_by_member_id')
    def test_get_user_by_id(self, mock_get_groups, mock_get_user_by_id, client, mock_user):
        """Test getting a specific SCIM user"""
        mock_get_user_by_id.return_value = mock_user
        mock_get_groups.return_value = []
        
        response = client.get(f"/api/v1/scim/v2/Users/{mock_user.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "user-456"
        assert data["userName"] == "test@example.com"
    
    @patch('open_webui.models.users.Users.get_user_by_email')
    @patch('open_webui.models.users.Users.insert_new_user')
    def test_create_user(self, mock_insert_user, mock_get_user_by_email, client):
        """Test creating a SCIM user"""
        mock_get_user_by_email.return_value = None
        
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
        
        response = client.post("/api/v1/scim/v2/Users", json=create_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["userName"] == "newuser@example.com"
        assert data["displayName"] == "New User"
    
    @patch('open_webui.models.groups.Groups.get_groups')
    @patch('open_webui.models.users.Users.get_user_by_id')
    def test_get_groups(self, mock_get_user_by_id, mock_get_groups, client, mock_group, mock_user):
        """Test listing SCIM groups"""
        mock_get_groups.return_value = [mock_group]
        mock_get_user_by_id.return_value = mock_user
        
        response = client.get("/api/v1/scim/v2/Groups")
        assert response.status_code == 200
        
        data = response.json()
        assert data["totalResults"] == 1
        assert len(data["Resources"]) == 1
        
        group = data["Resources"][0]
        assert group["id"] == "group-789"
        assert group["displayName"] == "Test Group"
    
    def test_service_provider_config(self, client):
        """Test service provider config (no auth needed)"""
        # Remove the override for this test since it doesn't need auth
        app.dependency_overrides.clear()
        
        response = client.get("/api/v1/scim/v2/ServiceProviderConfig")
        assert response.status_code == 200
        
        data = response.json()
        assert data["patch"]["supported"] == True
        assert data["filter"]["supported"] == True
"""
Tests for SCIM 2.0 endpoints
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from open_webui.main import app
from open_webui.models.users import UserModel
from open_webui.models.groups import GroupModel


class TestSCIMEndpoints:
    """Test SCIM 2.0 endpoints"""
    
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
    
    # Service Provider Config Tests
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
    
    # Resource Types Tests
    def test_get_resource_types(self, client):
        """Test getting SCIM Resource Types"""
        response = client.get("/api/v1/scim/v2/ResourceTypes")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check User resource type
        user_type = next(r for r in data if r["id"] == "User")
        assert user_type["name"] == "User"
        assert user_type["endpoint"] == "/Users"
        assert user_type["schema"] == "urn:ietf:params:scim:schemas:core:2.0:User"
        
        # Check Group resource type
        group_type = next(r for r in data if r["id"] == "Group")
        assert group_type["name"] == "Group"
        assert group_type["endpoint"] == "/Groups"
        assert group_type["schema"] == "urn:ietf:params:scim:schemas:core:2.0:Group"
    
    # Schemas Tests
    def test_get_schemas(self, client):
        """Test getting SCIM Schemas"""
        response = client.get("/api/v1/scim/v2/Schemas")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check User schema
        user_schema = next(s for s in data if s["id"] == "urn:ietf:params:scim:schemas:core:2.0:User")
        assert user_schema["name"] == "User"
        assert "attributes" in user_schema
        
        # Check Group schema
        group_schema = next(s for s in data if s["id"] == "urn:ietf:params:scim:schemas:core:2.0:Group")
        assert group_schema["name"] == "Group"
        assert "attributes" in group_schema
    
    # User Tests
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.users.Users.get_users')
    @patch('open_webui.models.groups.Groups.get_groups_by_member_id')
    def test_get_users(self, mock_get_groups, mock_get_users, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_user):
        """Test listing SCIM users"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.return_value = mock_admin_user
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
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.groups.Groups.get_groups_by_member_id')
    def test_get_user_by_id(self, mock_get_groups, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_user):
        """Test getting a specific SCIM user"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.side_effect = lambda id: mock_admin_user if id == "admin-123" else mock_user
        mock_get_groups.return_value = []
        
        response = client.get("/api/v1/scim/v2/Users/user-456", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "user-456"
        assert data["userName"] == "test@example.com"
        assert data["displayName"] == "Test User"
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.users.Users.get_user_by_email')
    @patch('open_webui.models.users.Users.insert_new_user')
    def test_create_user(self, mock_insert_user, mock_get_user_by_email, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user):
        """Test creating a SCIM user"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.return_value = mock_admin_user
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
        
        response = client.post("/api/v1/scim/v2/Users", headers=auth_headers, json=create_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["userName"] == "newuser@example.com"
        assert data["displayName"] == "New User"
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.users.Users.update_user_by_id')
    def test_update_user(self, mock_update_user, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_user):
        """Test updating a SCIM user"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.side_effect = lambda id: mock_admin_user if id == "admin-123" else mock_user
        
        updated_user = mock_user.model_copy()
        updated_user.name = "Updated User"
        mock_update_user.return_value = updated_user
        
        update_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "displayName": "Updated User"
        }
        
        response = client.put(f"/api/v1/scim/v2/Users/{mock_user.id}", headers=auth_headers, json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["displayName"] == "Updated User"
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.users.Users.update_user_by_id')
    def test_patch_user(self, mock_update_user, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_user):
        """Test patching a SCIM user"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.side_effect = lambda id: mock_admin_user if id == "admin-123" else mock_user
        
        updated_user = mock_user.model_copy()
        updated_user.role = "pending"
        mock_update_user.return_value = updated_user
        
        patch_data = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "replace",
                    "path": "active",
                    "value": False
                }
            ]
        }
        
        response = client.patch(f"/api/v1/scim/v2/Users/{mock_user.id}", headers=auth_headers, json=patch_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["active"] == False
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.users.Users.delete_user_by_id')
    def test_delete_user(self, mock_delete_user, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_user):
        """Test deleting a SCIM user"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.side_effect = lambda id: mock_admin_user if id == "admin-123" else mock_user
        mock_delete_user.return_value = True
        
        response = client.delete(f"/api/v1/scim/v2/Users/{mock_user.id}", headers=auth_headers)
        assert response.status_code == 204
    
    # Group Tests
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.groups.Groups.get_groups')
    def test_get_groups(self, mock_get_groups, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_group):
        """Test listing SCIM groups"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.return_value = mock_admin_user
        mock_get_groups.return_value = [mock_group]
        
        response = client.get("/api/v1/scim/v2/Groups", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
        assert data["totalResults"] == 1
        assert len(data["Resources"]) == 1
        
        group = data["Resources"][0]
        assert group["id"] == "group-789"
        assert group["displayName"] == "Test Group"
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    @patch('open_webui.models.users.Users.get_super_admin_user')
    @patch('open_webui.models.groups.Groups.insert_new_group')
    def test_create_group(self, mock_insert_group, mock_get_super_admin, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user, mock_group):
        """Test creating a SCIM group"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.return_value = mock_admin_user
        mock_get_super_admin.return_value = mock_admin_user
        mock_insert_group.return_value = mock_group
        
        create_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": "Test Group"
        }
        
        response = client.post("/api/v1/scim/v2/Groups", headers=auth_headers, json=create_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["displayName"] == "Test Group"
    
    # Error Cases
    def test_unauthorized_access(self, client):
        """Test accessing SCIM endpoints without authentication"""
        response = client.get("/api/v1/scim/v2/Users")
        assert response.status_code == 401
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    def test_non_admin_access(self, mock_get_user_by_id, mock_decode_token, client, mock_user):
        """Test accessing SCIM endpoints as non-admin user"""
        mock_decode_token.return_value = {"id": "user-456"}
        mock_get_user_by_id.return_value = mock_user
        
        response = client.get("/api/v1/scim/v2/Users", headers={"Authorization": "Bearer non-admin-token"})
        assert response.status_code == 403
    
    @patch('open_webui.routers.scim.decode_token')
    @patch('open_webui.models.users.Users.get_user_by_id')
    def test_user_not_found(self, mock_get_user_by_id, mock_decode_token, client, auth_headers, mock_admin_user):
        """Test getting non-existent user"""
        mock_decode_token.return_value = {"id": "admin-123"}
        mock_get_user_by_id.side_effect = lambda id: mock_admin_user if id == "admin-123" else None
        
        response = client.get("/api/v1/scim/v2/Users/non-existent", headers=auth_headers)
        assert response.status_code == 404
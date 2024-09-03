import sys
import os
import pytest
import warnings
from fastapi import FastAPI
from fastapi.testclient import TestClient
import logging

# 忽略 passlib 中的 DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib.utils")

# Dynamically add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from backend.apps.web.routers.auths import router
from backend.utils.utils import get_current_user

# Create a FastAPI application instance and include the router
app = FastAPI()
app.include_router(router)

# Mock user data
class MockUser:
    def __init__(self, id, api_key=None, role='user'):
        self.id = id
        self.api_key = api_key
        self.role = role

# Create FastAPI test client
client = TestClient(app)

# Mock get_current_user dependency
def mock_get_current_user():
    return MockUser(id=1, role='admin')

# Replace get_current_user dependency
app.dependency_overrides[get_current_user] = mock_get_current_user

# Add a pytest fixture to set up the app state
@pytest.fixture(autouse=True)
def setup_app_state():
    app.state.ENABLE_SIGNUP = True
    app.state.JWT_EXPIRES_IN = "-1"
    app.state.WEBHOOK_URL = "http://example.com"
    app.state.DEFAULT_USER_ROLE = "admin"

def test_add_user():
    response = client.post("/signup", json={
        "email": "testuser@example.com",
        "password": "testpassword",
        "name": "Test User",
        "profile_image_url": "http://example.com/image.png",
        "role": "admin"
    })
    print(f'response.json(): {response.json()}')
    assert response.status_code == 200
    assert "id" in response.json()

def test_get_sign_up_status():
    response = client.get("/signup/enabled")
    assert response.status_code == 200
    assert isinstance(response.json(), bool)

def test_toggle_sign_up():
    response = client.get("/signup/enabled/toggle")
    assert response.status_code == 200
    assert isinstance(response.json(), bool)

def test_get_default_user_role():
    response = client.get("/signup/user/role")
    assert response.status_code == 200
    assert isinstance(response.json(), str)

def test_update_default_user_role():
    response = client.post("/signup/user/role", json={"role": "user"})
    assert response.status_code == 200
    assert response.json() == "user"

def test_get_token_expires_duration():
    response = client.get("/token/expires")
    assert response.status_code == 200
    assert isinstance(response.json(), str)

def test_update_token_expires_duration():
    response = client.post("/token/expires/update", json={"duration": "1h"})
    assert response.status_code == 200
    assert response.json() == "1h"

if __name__ == "__main__":
    pytest.main()
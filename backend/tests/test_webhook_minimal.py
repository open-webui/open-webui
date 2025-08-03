"""
Minimal webhook test with mocked dependencies
Tests the webhook endpoint without full database setup
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import os
import sys

# Add backend path for imports
backend_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_path)

# Set test environment before any imports
os.environ["DATABASE_URL"] = "sqlite:///test_minimal.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["WEBUI_AUTH"] = "false"


@pytest.fixture
def mock_db_setup():
    """Mock database setup to avoid initialization issues"""
    with patch('open_webui.internal.db.handle_peewee_migration'):
        with patch('open_webui.internal.db.Session'):
            with patch('open_webui.internal.db.get_db'):
                yield


@pytest.fixture
def test_client(mock_db_setup):
    """Create test client with mocked dependencies"""
    # Import app after mocking
    from open_webui.main import app
    return TestClient(app)


@pytest.fixture
def mock_webhook_service():
    """Mock the webhook service"""
    with patch('open_webui.usage_tracking.services.webhook_service.WebhookService') as mock_service:
        instance = AsyncMock()
        instance.process_webhook = AsyncMock(return_value={"status": "success"})
        mock_service.return_value = instance
        yield instance


def test_webhook_endpoint_accepts_requests(test_client, mock_webhook_service):
    """Test that webhook endpoint accepts requests (no signature validation)"""
    
    # Prepare webhook payload
    payload = {
        "api_key": "sk-or-test-123456789",
        "model": "gpt-4-turbo",
        "tokens_used": 1000,
        "cost": 0.01,
        "timestamp": "2025-07-31T12:00:00Z",
        "external_user": "test@example.com",
        "request_id": "test-request-001"
    }
    
    # Send request without signature (should work)
    response = test_client.post(
        "/api/v1/usage-tracking/webhook/openrouter-usage",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data
    
    # Send request with fake signature (should also work - no validation)
    response = test_client.post(
        "/api/v1/usage-tracking/webhook/openrouter-usage",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": "fake-signature-12345"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_webhook_handles_invalid_payload(test_client, mock_webhook_service):
    """Test webhook endpoint with invalid payload"""
    
    # Missing required fields
    invalid_payload = {
        "model": "gpt-4-turbo",
        # missing api_key, tokens_used, cost, timestamp
    }
    
    response = test_client.post(
        "/api/v1/usage-tracking/webhook/openrouter-usage",
        json=invalid_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # Should get validation error
    assert response.status_code == 422  # Unprocessable Entity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
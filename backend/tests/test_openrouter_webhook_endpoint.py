"""
Test suite for the OpenRouter webhook endpoint at /routers/usage_tracking.py

Tests verify signature validation scenarios:
1. Positive: Correct X-OpenRouter-Signature -> 200 OK
2. Negative: Incorrect signature -> 401 Unauthorized  
3. Negative: Missing signature header -> 401/400
"""

import pytest
import json
import hmac
import hashlib
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the backend directory to Python path to import open_webui modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import FastAPI app and related components
from open_webui.main import app
from open_webui.usage_tracking.models.requests import UsageWebhookPayload


class TestOpenRouterWebhookEndpoint:
    """Test suite for OpenRouter webhook endpoint signature verification"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def webhook_secret(self):
        """Test webhook secret for signature generation"""
        return "test-webhook-secret-key"

    @pytest.fixture
    def sample_webhook_payload(self):
        """Sample webhook payload for testing"""
        return {
            "event": "generation.completed",
            "data": {
                "id": "gen_12345",
                "model": "openai/gpt-4",
                "created_at": "2025-01-31T12:00:00Z",
                "finished_at": "2025-01-31T12:00:05Z",
                "usage": 0.002,
                "tokens_prompt": 50,
                "tokens_completion": 100,
                "total_tokens": 150,
                "status": "completed"
            },
            "timestamp": "2025-01-31T12:00:05Z"
        }

    def generate_signature(self, payload: dict, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload
        
        Args:
            payload: Webhook payload dictionary
            secret: Webhook secret key
            
        Returns:
            Hexadecimal signature string
        """
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    @patch('open_webui.usage_tracking.services.webhook_service.WebhookService.process_webhook')
    def test_positive_correct_signature_returns_200(
        self, 
        mock_process_webhook,
        client, 
        webhook_secret, 
        sample_webhook_payload
    ):
        """
        Positive test: Webhook with correct X-OpenRouter-Signature should return 200 OK
        """
        # Setup mock
        mock_process_webhook.return_value = {"status": "success"}
        
        # Generate correct signature
        correct_signature = self.generate_signature(sample_webhook_payload, webhook_secret)
        
        # Prepare headers with correct signature
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": correct_signature,
            "X-OpenRouter-Timestamp": "1738324805"  # Unix timestamp
        }
        
        # Mock environment variable for webhook secret
        with patch.dict(os.environ, {"OPENROUTER_WEBHOOK_SECRET": webhook_secret}):
            # Send request
            response = client.post(
                "/webhook/openrouter-usage",
                json=sample_webhook_payload,
                headers=headers
            )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["message"] == "Usage recorded"
        
        # Verify that webhook processing was called
        mock_process_webhook.assert_called_once()

    @patch('open_webui.usage_tracking.services.webhook_service.WebhookService.process_webhook')
    def test_negative_incorrect_signature_returns_401(
        self, 
        mock_process_webhook,
        client, 
        webhook_secret, 
        sample_webhook_payload
    ):
        """
        Negative test: Webhook with incorrect signature should return 401 Unauthorized
        """
        # Generate incorrect signature using wrong secret
        wrong_secret = "wrong-webhook-secret"
        incorrect_signature = self.generate_signature(sample_webhook_payload, wrong_secret)
        
        # Prepare headers with incorrect signature
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": incorrect_signature,
            "X-OpenRouter-Timestamp": "1738324805"
        }
        
        # Mock environment variable for correct webhook secret
        with patch.dict(os.environ, {"OPENROUTER_WEBHOOK_SECRET": webhook_secret}):
            # Send request
            response = client.post(
                "/webhook/openrouter-usage",
                json=sample_webhook_payload,
                headers=headers
            )
        
        # Assertions
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower() or "unauthorized" in response.json()["detail"].lower()
        
        # Verify that webhook processing was NOT called due to signature validation failure
        mock_process_webhook.assert_not_called()

    @patch('open_webui.usage_tracking.services.webhook_service.WebhookService.process_webhook')
    def test_negative_missing_signature_header_returns_401(
        self, 
        mock_process_webhook,
        client, 
        webhook_secret, 
        sample_webhook_payload
    ):
        """
        Negative test: Webhook without X-OpenRouter-Signature header should return 401 or 400
        """
        # Prepare headers without signature
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Timestamp": "1738324805"
            # Missing X-OpenRouter-Signature header
        }
        
        # Mock environment variable for webhook secret
        with patch.dict(os.environ, {"OPENROUTER_WEBHOOK_SECRET": webhook_secret}):
            # Send request
            response = client.post(
                "/webhook/openrouter-usage",
                json=sample_webhook_payload,
                headers=headers
            )
        
        # Assertions - Accept either 401 or 400 as both are valid for missing signature
        assert response.status_code in [400, 401]
        response_detail = response.json()["detail"].lower()
        assert any(keyword in response_detail for keyword in ["signature", "required", "missing", "unauthorized"])
        
        # Verify that webhook processing was NOT called due to missing signature
        mock_process_webhook.assert_not_called()

    def test_signature_generation_consistency(self, webhook_secret, sample_webhook_payload):
        """
        Test that signature generation is consistent and deterministic
        """
        # Generate signature multiple times
        sig1 = self.generate_signature(sample_webhook_payload, webhook_secret)
        sig2 = self.generate_signature(sample_webhook_payload, webhook_secret)
        sig3 = self.generate_signature(sample_webhook_payload, webhook_secret)
        
        # All signatures should be identical
        assert sig1 == sig2 == sig3
        assert len(sig1) == 64  # SHA256 hex digest is 64 characters
        assert isinstance(sig1, str)

    def test_signature_changes_with_payload_modification(self, webhook_secret, sample_webhook_payload):
        """
        Test that signature changes when payload is modified
        """
        # Generate signature for original payload
        original_signature = self.generate_signature(sample_webhook_payload, webhook_secret)
        
        # Modify payload
        modified_payload = sample_webhook_payload.copy()
        modified_payload["data"]["id"] = "gen_99999"  # Change ID
        
        # Generate signature for modified payload
        modified_signature = self.generate_signature(modified_payload, webhook_secret)
        
        # Signatures should be different
        assert original_signature != modified_signature

    def test_signature_changes_with_secret_modification(self, sample_webhook_payload):
        """
        Test that signature changes when secret is modified
        """
        secret1 = "secret-key-1"
        secret2 = "secret-key-2"
        
        # Generate signatures with different secrets
        sig1 = self.generate_signature(sample_webhook_payload, secret1)
        sig2 = self.generate_signature(sample_webhook_payload, secret2)
        
        # Signatures should be different
        assert sig1 != sig2

    @patch('open_webui.usage_tracking.services.webhook_service.WebhookService.process_webhook')
    def test_empty_signature_header_returns_401(
        self, 
        mock_process_webhook,
        client, 
        webhook_secret, 
        sample_webhook_payload
    ):
        """
        Test that empty signature header is treated as missing signature
        """
        # Prepare headers with empty signature
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": "",  # Empty signature
            "X-OpenRouter-Timestamp": "1738324805"
        }
        
        # Mock environment variable for webhook secret
        with patch.dict(os.environ, {"OPENROUTER_WEBHOOK_SECRET": webhook_secret}):
            # Send request
            response = client.post(
                "/webhook/openrouter-usage",
                json=sample_webhook_payload,
                headers=headers
            )
        
        # Assertions
        assert response.status_code in [400, 401]
        mock_process_webhook.assert_not_called()

    @patch('open_webui.usage_tracking.services.webhook_service.WebhookService.process_webhook')  
    def test_malformed_signature_returns_401(
        self, 
        mock_process_webhook,
        client, 
        webhook_secret, 
        sample_webhook_payload
    ):
        """
        Test that malformed signature (not valid hex) is rejected
        """
        # Prepare headers with malformed signature
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": "not-a-valid-hex-signature!@#$",
            "X-OpenRouter-Timestamp": "1738324805"
        }
        
        # Mock environment variable for webhook secret
        with patch.dict(os.environ, {"OPENROUTER_WEBHOOK_SECRET": webhook_secret}):
            # Send request
            response = client.post(
                "/webhook/openrouter-usage",
                json=sample_webhook_payload,
                headers=headers
            )
        
        # Assertions
        assert response.status_code == 401
        mock_process_webhook.assert_not_called()

    @patch('open_webui.usage_tracking.services.webhook_service.WebhookService.process_webhook')
    def test_signature_case_sensitivity(
        self, 
        mock_process_webhook,
        client, 
        webhook_secret, 
        sample_webhook_payload
    ):
        """
        Test that signature verification is case-sensitive
        """
        # Generate correct signature
        correct_signature = self.generate_signature(sample_webhook_payload, webhook_secret)
        
        # Convert to uppercase (should be invalid)
        uppercase_signature = correct_signature.upper()
        
        # Prepare headers with uppercase signature
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": uppercase_signature,
            "X-OpenRouter-Timestamp": "1738324805"
        }
        
        # Mock environment variable for webhook secret
        with patch.dict(os.environ, {"OPENROUTER_WEBHOOK_SECRET": webhook_secret}):
            # Send request
            response = client.post(
                "/webhook/openrouter-usage",
                json=sample_webhook_payload,
                headers=headers
            )
        
        # Assertions - Should fail if signature verification is case-sensitive
        # Note: HMAC signatures are typically lowercase hex, so uppercase should fail
        assert response.status_code == 401
        mock_process_webhook.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
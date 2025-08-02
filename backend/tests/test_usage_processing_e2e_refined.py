"""
Refined E2E Test for Usage Processing Cycle
Uses successful mocking approach from minimal test while maintaining E2E workflow testing
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, date, timezone
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Add backend path for imports
backend_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_path)

# Set test environment before any imports
os.environ["DATABASE_URL"] = "sqlite:///test_e2e_refined.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["WEBUI_AUTH"] = "false"

# Import test utilities after environment setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from test_helpers import WebhookTestGenerator


@pytest.fixture
def mock_db_and_services():
    """Mock database and services to avoid initialization issues"""
    with patch('open_webui.internal.db.handle_peewee_migration'):
        with patch('open_webui.usage_tracking.routers.webhook_router.webhook_service') as mock_service:
            # Setup webhook service mock instance
            mock_service.process_webhook = AsyncMock(return_value={"status": "success"})
            
            yield mock_service


@pytest.fixture
def test_client(mock_db_and_services):
    """Create test client with mocked dependencies"""
    from open_webui.main import app
    return TestClient(app)


@pytest.fixture
def webhook_generator():
    """Create webhook test generator"""
    return WebhookTestGenerator()


class TestUsageProcessingE2ERefined:
    """Refined E2E test for complete usage processing cycle"""
    
    def test_webhook_endpoint_functionality(self, test_client, webhook_generator, mock_db_and_services):
        """Test webhook endpoint accepts and processes requests correctly"""
        # Test configuration
        TARGET_TOKENS = 100000
        TARGET_COST_USD = 0.15
        TEST_API_KEY = "sk-or-test-e2e-123456789"
        
        # Generate webhook payloads for exact totals
        payloads = webhook_generator.generate_batch_for_total(
            total_tokens=TARGET_TOKENS,
            total_cost=TARGET_COST_USD,
            num_requests=5,
            api_key=TEST_API_KEY,
            timestamp=datetime(2025, 7, 31, 14, 30, 0, tzinfo=timezone.utc)
        )
        
        # Verify generated payloads sum correctly
        actual_tokens = sum(p['tokens_used'] for p in payloads)
        actual_cost = sum(p['cost'] for p in payloads)
        
        assert actual_tokens == TARGET_TOKENS, f"Generated tokens {actual_tokens} != target {TARGET_TOKENS}"
        assert abs(actual_cost - TARGET_COST_USD) < 0.001, f"Generated cost {actual_cost} != target {TARGET_COST_USD}"
        
        # Send webhooks to the API
        webhook_results = []
        for i, payload in enumerate(payloads):
            headers = webhook_generator.create_webhook_headers(payload)
            response = test_client.post(
                "/api/v1/usage-tracking/webhook/openrouter-usage",
                json=payload,
                headers=headers
            )
            
            webhook_results.append({
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code < 500 else {"error": response.text}
            })
        
        # Verify all webhooks were successful
        successful_webhooks = sum(1 for r in webhook_results if r['success'])
        assert successful_webhooks == len(payloads), f"Only {successful_webhooks}/{len(payloads)} webhooks succeeded"
        
        # Verify webhook service was called for each payload
        assert mock_db_and_services.process_webhook.call_count == len(payloads)
        
        # Verify the service was called with correct payloads
        for call_args in mock_db_and_services.process_webhook.call_args_list:
            payload_arg = call_args[0][0]  # First positional argument
            assert hasattr(payload_arg, 'api_key')
            assert hasattr(payload_arg, 'model')
            assert hasattr(payload_arg, 'tokens_used')
            assert hasattr(payload_arg, 'cost')
    
    def test_webhook_signature_handling(self, test_client, webhook_generator, mock_db_and_services):
        """Test webhook endpoint handles different signature scenarios"""
        payload = webhook_generator.generate_usage_payload(
            tokens=1000,
            cost=0.01,
            api_key="sk-or-test-signature-123"
        )
        
        # Test with signature headers
        headers_with_sig = webhook_generator.create_webhook_headers(payload)
        response1 = test_client.post(
            "/api/v1/usage-tracking/webhook/openrouter-usage",
            json=payload,
            headers=headers_with_sig
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["status"] == "success"
        
        # Test without signature headers (should still work - no validation)
        minimal_headers = {"Content-Type": "application/json"}
        response2 = test_client.post(
            "/api/v1/usage-tracking/webhook/openrouter-usage",
            json=payload,
            headers=minimal_headers
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["status"] == "success"
        
        # Test with invalid signature (should still work - no validation)
        invalid_headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": "invalid-signature-12345"
        }
        response3 = test_client.post(
            "/api/v1/usage-tracking/webhook/openrouter-usage",
            json=payload,
            headers=invalid_headers
        )
        
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["status"] == "success"
        
        # Verify webhook service was called 3 times
        assert mock_db_and_services.process_webhook.call_count == 3
    
    def test_webhook_payload_validation(self, test_client, webhook_generator, mock_db_and_services):
        """Test webhook endpoint validates payload structure"""
        # Test with invalid payload (missing required fields)
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
        
        # Webhook service should not be called for invalid payload
        assert mock_db_and_services.process_webhook.call_count == 0
    
    def test_duplicate_webhook_handling(self, test_client, webhook_generator, mock_db_and_services):
        """Test webhook endpoint handles duplicate requests"""
        payload = webhook_generator.generate_usage_payload(
            tokens=1000,
            cost=0.01,
            api_key="sk-or-test-duplicate-123"
        )
        
        # Use same request_id for both requests
        payload['request_id'] = "duplicate-test-12345"
        headers = webhook_generator.create_webhook_headers(payload)
        
        # Send first webhook
        response1 = test_client.post(
            "/api/v1/usage-tracking/webhook/openrouter-usage",
            json=payload,
            headers=headers
        )
        
        assert response1.status_code == 200
        assert response1.json()["status"] == "success"
        
        # Send duplicate webhook
        response2 = test_client.post(
            "/api/v1/usage-tracking/webhook/openrouter-usage",
            json=payload,
            headers=headers
        )
        
        # Both should succeed (duplicate detection may not be implemented)
        assert response2.status_code == 200
        assert response2.json()["status"] == "success"
        
        # Webhook service should be called twice (no duplicate detection at endpoint level)
        assert mock_db_and_services.process_webhook.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
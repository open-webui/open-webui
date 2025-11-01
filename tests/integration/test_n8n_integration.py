"""
Integration tests for N8N Pipeline Integration

Tests N8N configuration, workflow triggering, SSE streaming,
error handling, and execution tracking.
"""

import pytest
import httpx
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from open_webui.models.n8n_config import N8NConfig, N8NWorkflowExecution
from open_webui.routers.n8n_integration import router

@pytest.fixture
def test_user():
    """Mock user for testing"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "role": "user"
    }

@pytest.fixture
def test_n8n_config(test_user):
    """Create test N8N configuration"""
    return {
        "id": "config-123",
        "user_id": test_user["id"],
        "name": "Test Workflow",
        "n8n_url": "http://localhost:5678",
        "webhook_id": "test-webhook-abc",
        "api_key": "test-api-key",
        "is_active": True,
        "is_streaming": True,
        "timeout_seconds": 120,
        "retry_config": {"max_retries": 3, "backoff": 2},
        "metadata": {},
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }

@pytest.fixture
def mock_n8n_server(respx_mock):
    """Mock N8N server responses"""
    webhook_url = "http://localhost:5678/webhook/test-webhook-abc"

    # Success response
    respx_mock.post(webhook_url).mock(
        return_value=httpx.Response(
            200,
            json={"success": True, "data": {"result": "Workflow executed"}}
        )
    )

    return respx_mock

@pytest.fixture
def mock_n8n_streaming_server(respx_mock):
    """Mock N8N server with SSE streaming"""
    webhook_url = "http://localhost:5678/webhook/test-webhook-abc"

    async def stream_response():
        chunks = [
            "data: {\"progress\": 10}\n\n",
            "data: {\"progress\": 50}\n\n",
            "data: {\"progress\": 100, \"result\": \"complete\"}\n\n"
        ]
        for chunk in chunks:
            yield chunk.encode()

    respx_mock.post(webhook_url).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            stream=stream_response()
        )
    )

    return respx_mock


class TestN8NConfigManagement:
    """Test N8N configuration CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_n8n_config(self, test_user, test_n8n_config):
        """Test creating N8N configuration"""
        config = await N8NConfig.create(
            user_id=test_user["id"],
            name=test_n8n_config["name"],
            n8n_url=test_n8n_config["n8n_url"],
            webhook_id=test_n8n_config["webhook_id"],
            api_key=test_n8n_config["api_key"]
        )

        assert config.name == "Test Workflow"
        assert config.n8n_url == "http://localhost:5678"
        assert config.is_active is True
        assert config.user_id == test_user["id"]

    @pytest.mark.asyncio
    async def test_get_n8n_configs_by_user(self, test_user):
        """Test retrieving user's N8N configurations"""
        # Create multiple configs
        for i in range(3):
            await N8NConfig.create(
                user_id=test_user["id"],
                name=f"Workflow {i}",
                n8n_url="http://localhost:5678",
                webhook_id=f"webhook-{i}"
            )

        configs = await N8NConfig.get_by_user_id(test_user["id"])
        assert len(configs) == 3

    @pytest.mark.asyncio
    async def test_update_n8n_config(self, test_n8n_config):
        """Test updating N8N configuration"""
        config = await N8NConfig.create(**test_n8n_config)

        updated = await N8NConfig.update(
            config.id,
            name="Updated Workflow",
            timeout_seconds=300
        )

        assert updated.name == "Updated Workflow"
        assert updated.timeout_seconds == 300

    @pytest.mark.asyncio
    async def test_delete_n8n_config(self, test_n8n_config):
        """Test deleting N8N configuration"""
        config = await N8NConfig.create(**test_n8n_config)
        config_id = config.id

        await N8NConfig.delete(config_id)

        deleted = await N8NConfig.get_by_id(config_id)
        assert deleted is None


class TestN8NWorkflowExecution:
    """Test N8N workflow triggering and execution"""

    @pytest.mark.asyncio
    async def test_trigger_workflow_success(self, test_n8n_config, mock_n8n_server):
        """Test successful workflow execution"""
        config = await N8NConfig.create(**test_n8n_config)

        payload = {
            "prompt": "Test prompt",
            "data": {"key": "value"}
        }

        execution = await trigger_workflow(config.id, payload, test_n8n_config["user_id"])

        assert execution.status == "success"
        assert execution.config_id == config.id
        assert "Workflow executed" in execution.response

    @pytest.mark.asyncio
    async def test_trigger_workflow_timeout(self, test_n8n_config):
        """Test workflow execution timeout"""
        # Set very short timeout
        config = await N8NConfig.create(
            **{**test_n8n_config, "timeout_seconds": 1}
        )

        with patch("httpx.AsyncClient.post", side_effect=asyncio.TimeoutError):
            execution = await trigger_workflow(config.id, {}, test_n8n_config["user_id"])

            assert execution.status == "timeout"
            assert "timeout" in execution.error_message.lower()

    @pytest.mark.asyncio
    async def test_trigger_workflow_error(self, test_n8n_config):
        """Test workflow execution with N8N error"""
        config = await N8NConfig.create(**test_n8n_config)

        with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Connection failed")):
            execution = await trigger_workflow(config.id, {}, test_n8n_config["user_id"])

            assert execution.status == "failed"
            assert execution.error_message is not None

    @pytest.mark.asyncio
    async def test_workflow_retry_logic(self, test_n8n_config):
        """Test automatic retry on failure"""
        config = await N8NConfig.create(**test_n8n_config)

        # Mock first 2 attempts fail, 3rd succeeds
        mock_responses = [
            httpx.HTTPError("Temp failure"),
            httpx.HTTPError("Temp failure"),
            httpx.Response(200, json={"success": True})
        ]

        with patch("httpx.AsyncClient.post", side_effect=mock_responses):
            execution = await trigger_workflow(config.id, {}, test_n8n_config["user_id"])

            assert execution.status == "success"
            # Should have retried 2 times
            assert execution.metadata.get("retry_count") == 2


class TestN8NStreamingExecution:
    """Test Server-Sent Events (SSE) streaming"""

    @pytest.mark.asyncio
    async def test_sse_streaming_success(self, test_n8n_config, mock_n8n_streaming_server):
        """Test SSE streaming workflow execution"""
        config = await N8NConfig.create(**{**test_n8n_config, "is_streaming": True})

        events = []
        async for event in trigger_workflow_stream(config.id, {}, test_n8n_config["user_id"]):
            events.append(event)

        assert len(events) == 3
        assert events[0]["progress"] == 10
        assert events[1]["progress"] == 50
        assert events[2]["progress"] == 100
        assert events[2]["result"] == "complete"

    @pytest.mark.asyncio
    async def test_sse_stream_error_handling(self, test_n8n_config):
        """Test SSE streaming with connection errors"""
        config = await N8NConfig.create(**{**test_n8n_config, "is_streaming": True})

        async def failing_stream():
            yield "data: {\"progress\": 10}\n\n"
            raise httpx.ReadError("Connection lost")

        with patch("httpx.AsyncClient.stream", return_value=failing_stream()):
            events = []
            try:
                async for event in trigger_workflow_stream(config.id, {}, test_n8n_config["user_id"]):
                    events.append(event)
            except httpx.ReadError:
                pass

            # Should have received partial data before error
            assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_sse_client_disconnect(self, test_n8n_config):
        """Test handling client disconnect during SSE stream"""
        config = await N8NConfig.create(**{**test_n8n_config, "is_streaming": True})

        # Simulate client disconnect after 2 events
        events = []
        count = 0
        async for event in trigger_workflow_stream(config.id, {}, test_n8n_config["user_id"]):
            events.append(event)
            count += 1
            if count == 2:
                break  # Client disconnects

        assert len(events) == 2


class TestN8NExecutionTracking:
    """Test execution history and analytics"""

    @pytest.mark.asyncio
    async def test_execution_history_storage(self, test_n8n_config):
        """Test that executions are saved to database"""
        config = await N8NConfig.create(**test_n8n_config)

        # Execute 5 workflows
        for i in range(5):
            await trigger_workflow(
                config.id,
                {"prompt": f"Test {i}"},
                test_n8n_config["user_id"]
            )

        executions = await N8NWorkflowExecution.get_by_config_id(config.id)
        assert len(executions) == 5

    @pytest.mark.asyncio
    async def test_execution_duration_tracking(self, test_n8n_config, mock_n8n_server):
        """Test execution duration is recorded"""
        config = await N8NConfig.create(**test_n8n_config)

        # Add delay to mock response
        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.5)
            return httpx.Response(200, json={"success": True})

        with patch("httpx.AsyncClient.post", side_effect=delayed_response):
            execution = await trigger_workflow(config.id, {}, test_n8n_config["user_id"])

            assert execution.duration_ms >= 500  # At least 500ms

    @pytest.mark.asyncio
    async def test_execution_analytics_query(self, test_n8n_config):
        """Test querying execution analytics"""
        config = await N8NConfig.create(**test_n8n_config)

        # Create mix of successful and failed executions
        for i in range(10):
            status = "success" if i % 2 == 0 else "failed"
            await N8NWorkflowExecution.create(
                config_id=config.id,
                user_id=test_n8n_config["user_id"],
                status=status,
                duration_ms=100 + i * 10
            )

        analytics = await N8NWorkflowExecution.get_analytics(config.id)

        assert analytics["total_executions"] == 10
        assert analytics["success_rate"] == 0.5
        assert analytics["average_duration_ms"] > 100


class TestN8NSecurityAndValidation:
    """Test security and input validation"""

    @pytest.mark.asyncio
    async def test_unauthorized_access_denied(self, test_n8n_config):
        """Test that users can't access other users' configs"""
        config = await N8NConfig.create(**test_n8n_config)

        # Different user tries to access
        other_user = {"id": "other-user-456"}

        with pytest.raises(PermissionError):
            await trigger_workflow(config.id, {}, other_user["id"])

    @pytest.mark.asyncio
    async def test_invalid_webhook_url_rejected(self, test_user):
        """Test that invalid URLs are rejected"""
        with pytest.raises(ValueError):
            await N8NConfig.create(
                user_id=test_user["id"],
                name="Test",
                n8n_url="not-a-valid-url",
                webhook_id="webhook-123"
            )

    @pytest.mark.asyncio
    async def test_payload_sanitization(self, test_n8n_config):
        """Test that malicious payloads are sanitized"""
        config = await N8NConfig.create(**test_n8n_config)

        # Attempt XSS injection
        malicious_payload = {
            "prompt": "<script>alert('xss')</script>",
            "data": {"key": "<img src=x onerror=alert('xss')>"}
        }

        execution = await trigger_workflow(
            config.id,
            malicious_payload,
            test_n8n_config["user_id"]
        )

        # Payload should be sanitized
        assert "<script>" not in execution.prompt
        assert "alert" not in execution.prompt

    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_n8n_config):
        """Test rate limiting prevents abuse"""
        config = await N8NConfig.create(**test_n8n_config)

        # Attempt 100 rapid requests
        tasks = [
            trigger_workflow(config.id, {}, test_n8n_config["user_id"])
            for _ in range(100)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should be rate limited
        rate_limited = [r for r in results if isinstance(r, RateLimitError)]
        assert len(rate_limited) > 0


class TestN8NPerformance:
    """Test performance and scalability"""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, test_n8n_config):
        """Test handling concurrent workflow executions"""
        config = await N8NConfig.create(**test_n8n_config)

        # Execute 50 workflows concurrently
        start_time = time.time()

        tasks = [
            trigger_workflow(config.id, {"id": i}, test_n8n_config["user_id"])
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks)

        duration = time.time() - start_time

        # All should succeed
        assert all(r.status == "success" for r in results)

        # Should complete in reasonable time (parallel execution)
        assert duration < 10  # Less than 10 seconds for 50 concurrent

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, test_n8n_config):
        """Test handling large workflow payloads"""
        config = await N8NConfig.create(**test_n8n_config)

        # 10MB payload
        large_payload = {
            "data": "x" * (10 * 1024 * 1024)
        }

        execution = await trigger_workflow(
            config.id,
            large_payload,
            test_n8n_config["user_id"]
        )

        assert execution.status == "success"

    @pytest.mark.asyncio
    async def test_long_running_workflow(self, test_n8n_config):
        """Test handling workflows that take >60s"""
        config = await N8NConfig.create(
            **{**test_n8n_config, "timeout_seconds": 300}
        )

        # Mock 2-minute workflow
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(120)
            return httpx.Response(200, json={"success": True})

        with patch("httpx.AsyncClient.post", side_effect=slow_response):
            execution = await trigger_workflow(config.id, {}, test_n8n_config["user_id"])

            assert execution.status == "success"
            assert execution.duration_ms >= 120000


# Helper functions (would be imported from actual implementation)

async def trigger_workflow(config_id: str, payload: dict, user_id: str):
    """Mock implementation of trigger_workflow"""
    # This would be the actual implementation in production
    pass

async def trigger_workflow_stream(config_id: str, payload: dict, user_id: str):
    """Mock implementation of streaming workflow trigger"""
    # This would be the actual implementation in production
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])

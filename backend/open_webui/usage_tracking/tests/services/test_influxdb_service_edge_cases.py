"""
Edge case tests for InfluxDBService
Tests error conditions, performance, and boundary cases
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import TimeoutError
from influxdb_client import Point
from influxdb_client.client.exceptions import InfluxDBError

from backend.open_webui.usage_tracking.services.influxdb_service import InfluxDBService


class TestInfluxDBServiceEdgeCases:
    """Edge case tests for InfluxDBService"""
    
    @pytest.fixture
    def service_with_mocks(self, monkeypatch):
        """Create service with mocked dependencies"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "true")
        monkeypatch.setenv("INFLUXDB_URL", "http://localhost:8086")
        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("INFLUXDB_ORG", "test-org")
        monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
        
        with patch('backend.open_webui.usage_tracking.services.influxdb_service.InfluxDBClient'):
            service = InfluxDBService()
            service.write_api = Mock()
            service.query_api = Mock()
            return service
    
    @pytest.mark.asyncio
    async def test_write_with_very_large_token_count(self, service_with_mocks):
        """Test writing extremely large token counts"""
        webhook_data = {
            "model": "gpt-4",
            "tokens_used": 999999999,  # Very large number
            "cost": 29999.99,
            "api_key": "test-key"
        }
        
        result = await service_with_mocks.write_usage_record(webhook_data)
        
        assert result is True
        assert service_with_mocks.write_api.write.called
    
    @pytest.mark.asyncio
    async def test_write_with_negative_values(self, service_with_mocks):
        """Test handling negative values (should still write)"""
        webhook_data = {
            "model": "gpt-4",
            "tokens_used": -100,  # Negative tokens (correction)
            "cost": -0.003,      # Negative cost (refund)
            "api_key": "test-key"
        }
        
        result = await service_with_mocks.write_usage_record(webhook_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_write_with_special_characters(self, service_with_mocks):
        """Test handling special characters in string fields"""
        webhook_data = {
            "model": "gpt-4-turbo-🚀",
            "tokens_used": 100,
            "cost": 0.003,
            "external_user": "user@example.com; DROP TABLE users;--",
            "api_key": "test-key"
        }
        
        result = await service_with_mocks.write_usage_record(webhook_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self, service_with_mocks):
        """Test multiple concurrent writes"""
        webhook_data_list = [
            {
                "model": f"model-{i}",
                "tokens_used": 100 * i,
                "cost": 0.003 * i,
                "api_key": f"key-{i}"
            }
            for i in range(10)
        ]
        
        # Execute concurrent writes
        tasks = [
            service_with_mocks.write_usage_record(data)
            for data in webhook_data_list
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert all(results)
        assert service_with_mocks.write_api.write.call_count == 10
    
    @pytest.mark.asyncio
    async def test_write_timeout_handling(self, monkeypatch):
        """Test handling of write timeouts"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "true")
        monkeypatch.setenv("INFLUXDB_WRITE_TIMEOUT", "1")  # 1ms timeout
        
        with patch('backend.open_webui.usage_tracking.services.influxdb_service.InfluxDBClient'):
            service = InfluxDBService()
            service.write_api = Mock()
            service.write_api.write.side_effect = TimeoutError("Write timeout")
            
            result = await service.write_usage_record({"model": "gpt-4", "tokens_used": 100, "cost": 0.003})
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_influxdb_connection_error_on_init(self, monkeypatch):
        """Test graceful handling of connection errors during initialization"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "true")
        
        with patch('backend.open_webui.usage_tracking.services.influxdb_service.InfluxDBClient') as mock_client:
            mock_client.side_effect = Exception("Connection refused")
            
            service = InfluxDBService()
            
            assert service.enabled is False
            assert service.client is None
    
    @pytest.mark.asyncio
    async def test_batch_query_with_no_data(self, service_with_mocks):
        """Test batch query when no data exists"""
        service_with_mocks.query_api.query.return_value = []
        
        result = await service_with_mocks.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(days=30),
            datetime.now(timezone.utc)
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_batch_query_with_malformed_response(self, service_with_mocks):
        """Test batch query with malformed response data"""
        # Mock malformed record (missing required fields)
        mock_record = Mock()
        mock_record.values = {"model": "gpt-4"}  # Missing other fields
        
        mock_table = Mock()
        mock_table.records = [mock_record]
        
        service_with_mocks.query_api.query.return_value = [mock_table]
        
        result = await service_with_mocks.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        # Should handle missing fields gracefully
        assert len(result) == 1
        assert result[0]["model"] == "gpt-4"
        assert result[0]["total_tokens"] == 0
        assert result[0]["cost_usd"] == 0.0
    
    @pytest.mark.asyncio
    async def test_date_boundary_conditions(self, service_with_mocks):
        """Test querying at exact date boundaries"""
        # Mock response
        mock_table = Mock()
        mock_table.records = []
        service_with_mocks.query_api.query.return_value = [mock_table]
        
        # Test various boundary conditions
        now = datetime.now(timezone.utc)
        
        # Same start and end time
        result1 = await service_with_mocks.get_data_for_batch(
            "client-123", now, now
        )
        assert result1 == []
        
        # End time before start time (should handle gracefully)
        result2 = await service_with_mocks.get_data_for_batch(
            "client-123",
            now,
            now - timedelta(hours=1)
        )
        assert result2 == []
    
    @pytest.mark.asyncio
    async def test_very_long_client_org_id(self, service_with_mocks):
        """Test handling of very long client organization IDs"""
        long_client_id = "x" * 1000  # 1000 character ID
        
        webhook_data = {
            "model": "gpt-4",
            "tokens_used": 100,
            "cost": 0.003,
            "client_org_id": long_client_id
        }
        
        result = await service_with_mocks.write_usage_record(webhook_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_unicode_in_all_fields(self, service_with_mocks):
        """Test Unicode characters in all string fields"""
        webhook_data = {
            "model": "gpt-4-日本語",
            "tokens_used": 100,
            "cost": 0.003,
            "external_user": "用户@例子.com",
            "request_id": "リクエスト-12345",
            "api_key": "キー-123"
        }
        
        result = await service_with_mocks.write_usage_record(webhook_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_extreme_date_ranges(self, service_with_mocks):
        """Test querying with extreme date ranges"""
        service_with_mocks.query_api.query.return_value = []
        
        # Query 10 years of data
        result = await service_with_mocks.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(days=3650),
            datetime.now(timezone.utc)
        )
        
        assert result == []
        assert service_with_mocks.query_api.query.called
    
    @pytest.mark.asyncio
    async def test_influxdb_specific_errors(self, service_with_mocks):
        """Test handling of InfluxDB-specific errors"""
        # Test authorization error
        service_with_mocks.query_api.query.side_effect = InfluxDBError(
            response=Mock(status=401, data="unauthorized")
        )
        
        result = await service_with_mocks.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_partial_write_api_initialization(self, monkeypatch):
        """Test when write API fails but query API succeeds"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "true")
        
        with patch('backend.open_webui.usage_tracking.services.influxdb_service.InfluxDBClient') as mock_client:
            mock_instance = Mock()
            mock_instance.write_api.side_effect = Exception("Write API failed")
            mock_instance.query_api.return_value = Mock()
            
            mock_client.return_value = mock_instance
            
            service = InfluxDBService()
            
            # Service should be disabled due to initialization failure
            assert service.enabled is False
    
    def test_close_with_no_client(self):
        """Test closing when client was never initialized"""
        service = InfluxDBService()
        service.client = None
        service.write_api = None
        
        # Should not raise exception
        service.close()
    
    def test_close_with_exception(self, service_with_mocks):
        """Test closing when close operations fail"""
        service_with_mocks.client = Mock()
        service_with_mocks.write_api.close.side_effect = Exception("Close failed")
        service_with_mocks.client.close.side_effect = Exception("Client close failed")
        
        # Should handle exceptions gracefully
        service_with_mocks.close()
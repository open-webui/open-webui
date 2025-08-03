"""
Unit tests for InfluxDBService
Tests write_usage_record and get_data_for_batch methods
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from influxdb_client import Point, WritePrecision
from influxdb_client.client.exceptions import InfluxDBError

from open_webui.usage_tracking.services.influxdb_service import InfluxDBService


class TestInfluxDBService:
    """Test suite for InfluxDBService"""
    
    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Set up test environment variables"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "true")
        monkeypatch.setenv("INFLUXDB_URL", "http://localhost:8086")
        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("INFLUXDB_ORG", "test-org")
        monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
        monkeypatch.setenv("INFLUXDB_WRITE_TIMEOUT", "2000")
        monkeypatch.setenv("INFLUXDB_MEASUREMENT", "usage_tracking")
        monkeypatch.setenv("CLIENT_ORG_ID", "test-client-123")
    
    @pytest.fixture
    def mock_influxdb_client(self):
        """Mock InfluxDB client"""
        with patch('open_webui.usage_tracking.services.influxdb_service.InfluxDBClient') as mock_client:
            # Mock write API
            mock_write_api = Mock()
            mock_write_api.write = Mock()
            
            # Mock query API
            mock_query_api = Mock()
            
            # Mock client instance
            mock_instance = Mock()
            mock_instance.write_api.return_value = mock_write_api
            mock_instance.query_api.return_value = mock_query_api
            
            mock_client.return_value = mock_instance
            
            yield {
                'client': mock_instance,
                'write_api': mock_write_api,
                'query_api': mock_query_api,
                'client_class': mock_client
            }
    
    @pytest.fixture
    def webhook_data(self):
        """Sample webhook data for testing"""
        return {
            "api_key": "test-api-key",
            "model": "gpt-4",
            "tokens_used": 1500,
            "cost": 0.045,
            "timestamp": "2025-01-30T10:30:00Z",
            "external_user": "user@example.com",
            "request_id": "req-12345",
            "latency_ms": 250
        }
    
    @pytest.mark.asyncio
    async def test_write_usage_record_success(self, mock_env_vars, mock_influxdb_client, webhook_data):
        """Test successful write to InfluxDB"""
        # Initialize service
        service = InfluxDBService()
        
        # Override the mocked write_api
        service.write_api = mock_influxdb_client['write_api']
        
        # Test write
        result = await service.write_usage_record(webhook_data)
        
        # Assertions
        assert result is True
        assert mock_influxdb_client['write_api'].write.called
        
        # Verify the call arguments
        call_args = mock_influxdb_client['write_api'].write.call_args
        assert call_args[1]['bucket'] == 'test-bucket'
        
        # Verify Point data
        point = call_args[1]['record']
        assert isinstance(point, Point)
    
    @pytest.mark.asyncio
    async def test_write_usage_record_disabled(self, monkeypatch):
        """Test write when InfluxDB is disabled"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "false")
        
        service = InfluxDBService()
        result = await service.write_usage_record({"test": "data"})
        
        assert result is False
        assert service.enabled is False
    
    @pytest.mark.asyncio
    async def test_write_usage_record_exception(self, mock_env_vars, mock_influxdb_client, webhook_data):
        """Test write failure handling"""
        service = InfluxDBService()
        service.write_api = mock_influxdb_client['write_api']
        
        # Mock write to raise exception
        mock_influxdb_client['write_api'].write.side_effect = Exception("Write failed")
        
        result = await service.write_usage_record(webhook_data)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_write_usage_record_with_optional_fields(self, mock_env_vars, mock_influxdb_client):
        """Test write with minimal data (no optional fields)"""
        minimal_data = {
            "model": "gpt-3.5-turbo",
            "tokens_used": 100,
            "cost": 0.002
        }
        
        service = InfluxDBService()
        service.write_api = mock_influxdb_client['write_api']
        
        result = await service.write_usage_record(minimal_data)
        
        assert result is True
        assert mock_influxdb_client['write_api'].write.called
    
    @pytest.mark.asyncio
    async def test_write_usage_record_cloud_mode(self, mock_env_vars, mock_influxdb_client, webhook_data):
        """Test write in cloud mode (async)"""
        # Set cloud mode
        with patch.dict(os.environ, {"INFLUXDB_USE_CLOUD": "true"}):
            service = InfluxDBService()
            service.use_cloud = True
            service.write_api = mock_influxdb_client['write_api']
            
            # Mock asyncio executor
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
                
                result = await service.write_usage_record(webhook_data)
                
                assert result is True
                assert mock_loop.return_value.run_in_executor.called
    
    @pytest.mark.asyncio
    async def test_get_data_for_batch_success(self, mock_env_vars, mock_influxdb_client):
        """Test successful batch data query"""
        # Mock query result
        mock_table = Mock()
        mock_record = Mock()
        mock_record.values = {
            "model": "gpt-4",
            "external_user": "user@example.com",
            "total_tokens": 5000,
            "cost_usd": 0.15
        }
        mock_table.records = [mock_record]
        
        mock_influxdb_client['query_api'].query.return_value = [mock_table]
        
        service = InfluxDBService()
        service.query_api = mock_influxdb_client['query_api']
        
        # Test query
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        result = await service.get_data_for_batch("test-client-123", start_time, end_time)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["model"] == "gpt-4"
        assert result[0]["external_user"] == "user@example.com"
        assert result[0]["total_tokens"] == 5000
        assert result[0]["cost_usd"] == 0.15
    
    @pytest.mark.asyncio
    async def test_get_data_for_batch_disabled(self, monkeypatch):
        """Test batch query when InfluxDB is disabled"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "false")
        
        service = InfluxDBService()
        result = await service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc),
            datetime.now(timezone.utc)
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_data_for_batch_exception(self, mock_env_vars, mock_influxdb_client):
        """Test batch query error handling"""
        mock_influxdb_client['query_api'].query.side_effect = Exception("Query failed")
        
        service = InfluxDBService()
        service.query_api = mock_influxdb_client['query_api']
        
        result = await service.get_data_for_batch(
            "test-client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_data_for_batch_multiple_records(self, mock_env_vars, mock_influxdb_client):
        """Test batch query with multiple records"""
        # Mock multiple records
        records = []
        for i in range(3):
            mock_record = Mock()
            mock_record.values = {
                "model": f"model-{i}",
                "external_user": f"user{i}@example.com",
                "total_tokens": 1000 * (i + 1),
                "cost_usd": 0.03 * (i + 1)
            }
            records.append(mock_record)
        
        mock_table = Mock()
        mock_table.records = records
        
        mock_influxdb_client['query_api'].query.return_value = [mock_table]
        
        service = InfluxDBService()
        service.query_api = mock_influxdb_client['query_api']
        
        result = await service.get_data_for_batch(
            "test-client-123",
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc)
        )
        
        assert len(result) == 3
        assert result[0]["model"] == "model-0"
        assert result[1]["total_tokens"] == 2000
        assert result[2]["cost_usd"] == 0.09
    
    @pytest.mark.asyncio
    async def test_hash_api_key(self, mock_env_vars):
        """Test API key hashing"""
        service = InfluxDBService()
        
        # Test with valid API key
        hash1 = service._hash_api_key("test-api-key-123")
        assert len(hash1) == 8
        assert hash1 != "test-api-key-123"
        
        # Test consistency
        hash2 = service._hash_api_key("test-api-key-123")
        assert hash1 == hash2
        
        # Test different keys produce different hashes
        hash3 = service._hash_api_key("different-key")
        assert hash3 != hash1
        
        # Test empty key
        hash_empty = service._hash_api_key("")
        assert hash_empty == "unknown"
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_env_vars, mock_influxdb_client):
        """Test health check when InfluxDB is healthy"""
        mock_influxdb_client['query_api'].query.return_value = []
        
        service = InfluxDBService()
        service.query_api = mock_influxdb_client['query_api']
        
        health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert health["url"] == "http://localhost:8086"
        assert health["bucket"] == "test-bucket"
        assert health["org"] == "test-org"
        assert health["mode"] == "local"
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_env_vars, mock_influxdb_client):
        """Test health check when InfluxDB is unhealthy"""
        mock_influxdb_client['query_api'].query.side_effect = Exception("Connection failed")
        
        service = InfluxDBService()
        service.query_api = mock_influxdb_client['query_api']
        
        health = await service.health_check()
        
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert health["url"] == "http://localhost:8086"
    
    @pytest.mark.asyncio
    async def test_health_check_disabled(self, monkeypatch):
        """Test health check when InfluxDB is disabled"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "false")
        
        service = InfluxDBService()
        health = await service.health_check()
        
        assert health["status"] == "disabled"
        assert "message" in health
    
    def test_close_connection(self, mock_env_vars, mock_influxdb_client):
        """Test closing InfluxDB connection"""
        service = InfluxDBService()
        service.client = mock_influxdb_client['client']
        service.write_api = mock_influxdb_client['write_api']
        
        service.close()
        
        assert mock_influxdb_client['write_api'].close.called
        assert mock_influxdb_client['client'].close.called
    
    @pytest.mark.asyncio
    async def test_get_usage_summary(self, mock_env_vars, mock_influxdb_client):
        """Test usage summary retrieval"""
        # Mock query result for summary
        mock_tokens_record = Mock()
        mock_tokens_record.values = {"_field": "total_tokens", "_value": 50000}
        
        mock_cost_record = Mock()
        mock_cost_record.values = {"_field": "cost_usd", "_value": 1.5}
        
        mock_table1 = Mock()
        mock_table1.records = [mock_tokens_record]
        
        mock_table2 = Mock()
        mock_table2.records = [mock_cost_record]
        
        mock_influxdb_client['query_api'].query.return_value = [mock_table1, mock_table2]
        
        service = InfluxDBService()
        service.query_api = mock_influxdb_client['query_api']
        
        summary = await service.get_usage_summary("test-client-123", days_back=7)
        
        assert summary["client_org_id"] == "test-client-123"
        assert summary["period_days"] == 7
        assert summary["total_tokens"] == 50000
        assert summary["total_cost_usd"] == 1.5
    
    @pytest.mark.asyncio
    async def test_timestamp_parsing(self, mock_env_vars, mock_influxdb_client):
        """Test various timestamp formats in webhook data"""
        service = InfluxDBService()
        service.write_api = mock_influxdb_client['write_api']
        
        # Test ISO format with Z
        data1 = {
            "model": "gpt-4",
            "tokens_used": 100,
            "cost": 0.003,
            "timestamp": "2025-01-30T10:30:00Z"
        }
        result1 = await service.write_usage_record(data1)
        assert result1 is True
        
        # Test ISO format with timezone
        data2 = {
            "model": "gpt-4",
            "tokens_used": 100,
            "cost": 0.003,
            "timestamp": "2025-01-30T10:30:00+00:00"
        }
        result2 = await service.write_usage_record(data2)
        assert result2 is True
        
        # Test invalid timestamp (should use current time)
        data3 = {
            "model": "gpt-4",
            "tokens_used": 100,
            "cost": 0.003,
            "timestamp": "invalid-timestamp"
        }
        result3 = await service.write_usage_record(data3)
        assert result3 is True
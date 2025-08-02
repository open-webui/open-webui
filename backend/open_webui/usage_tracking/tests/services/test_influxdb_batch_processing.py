"""
Focused tests for InfluxDBService get_data_for_batch method
Tests batch processing scenarios for daily aggregation
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from decimal import Decimal

from backend.open_webui.usage_tracking.services.influxdb_service import InfluxDBService


class TestInfluxDBBatchProcessing:
    """Test suite for batch processing functionality"""
    
    @pytest.fixture
    def mock_service(self, monkeypatch):
        """Create service with mocked environment"""
        monkeypatch.setenv("INFLUXDB_ENABLED", "true")
        monkeypatch.setenv("INFLUXDB_URL", "http://localhost:8086")
        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("INFLUXDB_ORG", "test-org")
        monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
        monkeypatch.setenv("INFLUXDB_MEASUREMENT", "usage_tracking")
        
        with patch('backend.open_webui.usage_tracking.services.influxdb_service.InfluxDBClient'):
            service = InfluxDBService()
            service.query_api = Mock()
            return service
    
    def create_mock_records(self, data_list):
        """Helper to create mock InfluxDB records"""
        records = []
        for data in data_list:
            record = Mock()
            record.values = data
            records.append(record)
        return records
    
    @pytest.mark.asyncio
    async def test_batch_aggregation_by_model(self, mock_service):
        """Test aggregation of usage data by model"""
        # Create test data with multiple entries for same model
        test_data = [
            {
                "model": "gpt-4",
                "external_user": "user1@example.com",
                "total_tokens": 1000,
                "cost_usd": 0.03
            },
            {
                "model": "gpt-4",
                "external_user": "user2@example.com",
                "total_tokens": 2000,
                "cost_usd": 0.06
            },
            {
                "model": "gpt-3.5-turbo",
                "external_user": "user1@example.com",
                "total_tokens": 500,
                "cost_usd": 0.001
            }
        ]
        
        mock_table = Mock()
        mock_table.records = self.create_mock_records(test_data)
        mock_service.query_api.query.return_value = [mock_table]
        
        # Query for daily batch
        start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        result = await mock_service.get_data_for_batch("client-123", start_time, end_time)
        
        assert len(result) == 3
        
        # Verify data integrity
        gpt4_records = [r for r in result if r["model"] == "gpt-4"]
        assert len(gpt4_records) == 2
        assert sum(r["total_tokens"] for r in gpt4_records) == 3000
        assert sum(r["cost_usd"] for r in gpt4_records) == 0.09
    
    @pytest.mark.asyncio
    async def test_batch_aggregation_by_user(self, mock_service):
        """Test aggregation grouped by external user"""
        # Create test data with multiple models per user
        test_data = [
            {
                "model": "gpt-4",
                "external_user": "power-user@example.com",
                "total_tokens": 5000,
                "cost_usd": 0.15
            },
            {
                "model": "gpt-3.5-turbo",
                "external_user": "power-user@example.com",
                "total_tokens": 10000,
                "cost_usd": 0.02
            },
            {
                "model": "claude-3-opus",
                "external_user": "power-user@example.com",
                "total_tokens": 3000,
                "cost_usd": 0.45
            }
        ]
        
        mock_table = Mock()
        mock_table.records = self.create_mock_records(test_data)
        mock_service.query_api.query.return_value = [mock_table]
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc)
        )
        
        # All records should be for the same user
        assert len(result) == 3
        assert all(r["external_user"] == "power-user@example.com" for r in result)
        
        # Total usage for the user
        total_tokens = sum(r["total_tokens"] for r in result)
        total_cost = sum(r["cost_usd"] for r in result)
        assert total_tokens == 18000
        assert abs(total_cost - 0.62) < 0.001  # Float comparison
    
    @pytest.mark.asyncio
    async def test_batch_with_missing_users(self, mock_service):
        """Test handling records with missing external_user"""
        test_data = [
            {
                "model": "gpt-4",
                "external_user": None,  # Missing user
                "total_tokens": 1000,
                "cost_usd": 0.03
            },
            {
                "model": "gpt-4",
                "external_user": "unknown",  # Default placeholder
                "total_tokens": 2000,
                "cost_usd": 0.06
            }
        ]
        
        mock_table = Mock()
        mock_table.records = self.create_mock_records(test_data)
        mock_service.query_api.query.return_value = [mock_table]
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        assert len(result) == 2
        # Should handle None as "unknown"
        assert result[0]["external_user"] == "unknown"
        assert result[1]["external_user"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_batch_time_range_precision(self, mock_service):
        """Test precise time range filtering in queries"""
        mock_service.query_api.query.return_value = []
        
        # Test daily batch at 13:00 CET
        batch_time = datetime(2025, 1, 30, 13, 0, 0, tzinfo=timezone.utc)
        start_time = batch_time - timedelta(days=1)
        end_time = batch_time
        
        await mock_service.get_data_for_batch("client-123", start_time, end_time)
        
        # Verify the query was called with correct time range
        call_args = mock_service.query_api.query.call_args[1]['query']
        assert start_time.isoformat() in call_args
        assert end_time.isoformat() in call_args
    
    @pytest.mark.asyncio
    async def test_batch_with_decimal_precision(self, mock_service):
        """Test handling of high-precision decimal values"""
        test_data = [
            {
                "model": "gpt-4",
                "external_user": "user@example.com",
                "total_tokens": 1234,
                "cost_usd": 0.0370200001  # High precision
            },
            {
                "model": "gpt-4",
                "external_user": "user@example.com",
                "total_tokens": 5678,
                "cost_usd": 0.1703399999  # High precision
            }
        ]
        
        mock_table = Mock()
        mock_table.records = self.create_mock_records(test_data)
        mock_service.query_api.query.return_value = [mock_table]
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        # Should maintain precision
        assert len(result) == 2
        assert result[0]["cost_usd"] == 0.0370200001
        assert result[1]["cost_usd"] == 0.1703399999
    
    @pytest.mark.asyncio
    async def test_batch_empty_time_range(self, mock_service):
        """Test querying with various empty result scenarios"""
        # Empty result
        mock_service.query_api.query.return_value = []
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(minutes=1),
            datetime.now(timezone.utc)
        )
        
        assert result == []
        
        # Result with empty tables
        mock_table = Mock()
        mock_table.records = []
        mock_service.query_api.query.return_value = [mock_table]
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(minutes=1),
            datetime.now(timezone.utc)
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_batch_query_construction(self, mock_service):
        """Test the Flux query construction for batch processing"""
        mock_service.query_api.query.return_value = []
        
        client_org_id = "test-org-123"
        start_time = datetime(2025, 1, 29, 13, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 30, 13, 0, 0, tzinfo=timezone.utc)
        
        await mock_service.get_data_for_batch(client_org_id, start_time, end_time)
        
        # Verify query structure
        query = mock_service.query_api.query.call_args[1]['query']
        
        # Check key components
        assert 'from(bucket: "test-bucket")' in query
        assert f'range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)' in query
        assert 'filter(fn: (r) => r["_measurement"] == "usage_tracking")' in query
        assert f'filter(fn: (r) => r["client_org_id"] == "{client_org_id}")' in query
        assert 'group(columns: ["model", "external_user", "_field"])' in query
        assert 'sum()' in query
        assert 'pivot(rowKey: ["model", "external_user"], columnKey: ["_field"], valueColumn: "_value")' in query
    
    @pytest.mark.asyncio
    async def test_batch_with_multiple_tables(self, mock_service):
        """Test handling multiple tables in query result"""
        # Create multiple tables (can happen with complex queries)
        table1_data = [
            {
                "model": "gpt-4",
                "external_user": "user1@example.com",
                "total_tokens": 1000,
                "cost_usd": 0.03
            }
        ]
        
        table2_data = [
            {
                "model": "claude-3",
                "external_user": "user2@example.com",
                "total_tokens": 2000,
                "cost_usd": 0.30
            }
        ]
        
        mock_table1 = Mock()
        mock_table1.records = self.create_mock_records(table1_data)
        
        mock_table2 = Mock()
        mock_table2.records = self.create_mock_records(table2_data)
        
        mock_service.query_api.query.return_value = [mock_table1, mock_table2]
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        # Should process all tables
        assert len(result) == 2
        models = [r["model"] for r in result]
        assert "gpt-4" in models
        assert "claude-3" in models
    
    @pytest.mark.asyncio
    async def test_batch_field_type_conversion(self, mock_service):
        """Test type conversion for fields"""
        test_data = [
            {
                "model": "gpt-4",
                "external_user": "user@example.com",
                "total_tokens": "1000",  # String instead of int
                "cost_usd": "0.03"      # String instead of float
            }
        ]
        
        mock_table = Mock()
        mock_table.records = self.create_mock_records(test_data)
        mock_service.query_api.query.return_value = [mock_table]
        
        result = await mock_service.get_data_for_batch(
            "client-123",
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        )
        
        # Should convert types properly
        assert len(result) == 1
        assert isinstance(result[0]["total_tokens"], int)
        assert isinstance(result[0]["cost_usd"], float)
        assert result[0]["total_tokens"] == 1000
        assert result[0]["cost_usd"] == 0.03
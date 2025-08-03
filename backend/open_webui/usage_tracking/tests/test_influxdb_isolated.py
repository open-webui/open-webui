"""
Isolated unit tests for InfluxDBService
This test file can run independently without full open_webui dependencies
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch, AsyncMock

# Add the service directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services')))

# Mock the influxdb_client module if not installed
try:
    from influxdb_client import Point, WritePrecision
    from influxdb_client.client.exceptions import InfluxDBError
except ImportError:
    # Create mock classes for testing without influxdb_client
    class Point:
        def __init__(self, measurement):
            self.measurement = measurement
            self.tags = {}
            self.fields = {}
            self.time_val = None
        
        def tag(self, key, value):
            self.tags[key] = value
            return self
        
        def field(self, key, value):
            self.fields[key] = value
            return self
        
        def time(self, time, precision=None):
            self.time_val = time
            return self
    
    class WritePrecision:
        MS = "ms"
    
    class InfluxDBError(Exception):
        pass


class TestInfluxDBServiceIsolated:
    """Isolated test suite for InfluxDBService"""
    
    def setup_method(self):
        """Set up test environment variables"""
        os.environ["INFLUXDB_ENABLED"] = "true"
        os.environ["INFLUXDB_URL"] = "http://localhost:8086"
        os.environ["INFLUXDB_TOKEN"] = "test-token"
        os.environ["INFLUXDB_ORG"] = "test-org"
        os.environ["INFLUXDB_BUCKET"] = "test-bucket"
        os.environ["INFLUXDB_WRITE_TIMEOUT"] = "2000"
        os.environ["INFLUXDB_MEASUREMENT"] = "usage_tracking"
        os.environ["CLIENT_ORG_ID"] = "test-client-123"
    
    def teardown_method(self):
        """Clean up environment variables"""
        env_vars = [
            "INFLUXDB_ENABLED", "INFLUXDB_URL", "INFLUXDB_TOKEN",
            "INFLUXDB_ORG", "INFLUXDB_BUCKET", "INFLUXDB_WRITE_TIMEOUT",
            "INFLUXDB_MEASUREMENT", "CLIENT_ORG_ID"
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    @pytest.mark.asyncio
    async def test_write_usage_record_mocked(self):
        """Test write functionality with mocked InfluxDB client"""
        # Mock the entire influxdb_client module
        with patch.dict('sys.modules', {'influxdb_client': MagicMock()}):
            # Import after mocking
            from influxdb_service import InfluxDBService
            
            # Create service with mocked client
            with patch.object(InfluxDBService, '__init__', lambda self: None):
                service = InfluxDBService()
                service.enabled = True
                service.use_cloud = False
                service.bucket = "test-bucket"
                service.measurement = "usage_tracking"
                service.write_api = Mock()
                service.write_api.write = Mock()
                
                # Test data
                webhook_data = {
                    "api_key": "test-api-key",
                    "model": "gpt-4",
                    "tokens_used": 1500,
                    "cost": 0.045,
                    "timestamp": "2025-01-30T10:30:00Z",
                    "external_user": "user@example.com",
                    "request_id": "req-12345"
                }
                
                # Manually implement the write logic
                result = await service.write_usage_record(webhook_data)
                
                assert service.write_api.write.called
    
    @pytest.mark.asyncio
    async def test_disabled_service(self):
        """Test that disabled service returns False"""
        os.environ["INFLUXDB_ENABLED"] = "false"
        
        with patch.dict('sys.modules', {'influxdb_client': MagicMock()}):
            from influxdb_service import InfluxDBService
            
            service = InfluxDBService()
            result = await service.write_usage_record({"test": "data"})
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_batch_query_mocked(self):
        """Test batch query functionality with mocked client"""
        with patch.dict('sys.modules', {'influxdb_client': MagicMock()}):
            from influxdb_service import InfluxDBService
            
            with patch.object(InfluxDBService, '__init__', lambda self: None):
                service = InfluxDBService()
                service.enabled = True
                service.bucket = "test-bucket"
                service.measurement = "usage_tracking"
                service.query_api = Mock()
                
                # Mock query result
                mock_record = Mock()
                mock_record.values = {
                    "model": "gpt-4",
                    "external_user": "user@example.com",
                    "total_tokens": 5000,
                    "cost_usd": 0.15
                }
                mock_table = Mock()
                mock_table.records = [mock_record]
                service.query_api.query = Mock(return_value=[mock_table])
                
                # Test query
                start_time = datetime.now(timezone.utc) - timedelta(hours=1)
                end_time = datetime.now(timezone.utc)
                
                result = await service.get_data_for_batch("test-client", start_time, end_time)
                
                assert len(result) == 1
                assert result[0]["model"] == "gpt-4"


if __name__ == "__main__":
    # Run tests directly
    import unittest
    
    # Create async test runner
    def run_async_test(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    
    # Run tests
    test = TestInfluxDBServiceIsolated()
    test.setup_method()
    
    print("Running isolated InfluxDB tests...")
    
    # Test 1: Write with mocked client
    print("Test 1: Write usage record...")
    try:
        run_async_test(test.test_write_usage_record_mocked())
        print("✓ Write test passed")
    except Exception as e:
        print(f"✗ Write test failed: {e}")
    
    # Test 2: Disabled service
    print("\nTest 2: Disabled service...")
    try:
        run_async_test(test.test_disabled_service())
        print("✓ Disabled service test passed")
    except Exception as e:
        print(f"✗ Disabled service test failed: {e}")
    
    # Test 3: Batch query
    print("\nTest 3: Batch query...")
    try:
        run_async_test(test.test_batch_query_mocked())
        print("✓ Batch query test passed")
    except Exception as e:
        print(f"✗ Batch query test failed: {e}")
    
    test.teardown_method()
    print("\nAll tests completed!")
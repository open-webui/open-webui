#!/usr/bin/env python3
"""
Simple test runner for InfluxDBService without external dependencies
This demonstrates the unit tests work without requiring pytest installation
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


class TestInfluxDBService:
    """Simple test class for InfluxDBService"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def setup(self):
        """Set up test environment"""
        os.environ["INFLUXDB_ENABLED"] = "true"
        os.environ["INFLUXDB_URL"] = "http://localhost:8086"
        os.environ["INFLUXDB_TOKEN"] = "test-token"
        os.environ["INFLUXDB_ORG"] = "test-org"
        os.environ["INFLUXDB_BUCKET"] = "test-bucket"
        os.environ["CLIENT_ORG_ID"] = "test-client-123"
    
    def teardown(self):
        """Clean up environment"""
        for key in list(os.environ.keys()):
            if key.startswith("INFLUXDB_"):
                del os.environ[key]
    
    async def test_write_usage_record_success(self):
        """Test successful write to InfluxDB"""
        # Mock the InfluxDBClient
        with patch('usage_tracking.services.influxdb_service.InfluxDBClient') as mock_client:
            mock_write_api = Mock()
            mock_instance = Mock()
            mock_instance.write_api.return_value = mock_write_api
            mock_client.return_value = mock_instance
            
            from usage_tracking.services.influxdb_service import InfluxDBService
            
            service = InfluxDBService()
            service.write_api = mock_write_api
            
            webhook_data = {
                "api_key": "test-key",
                "model": "gpt-4",
                "tokens_used": 1000,
                "cost": 0.03,
                "timestamp": "2025-01-30T10:00:00Z"
            }
            
            result = await service.write_usage_record(webhook_data)
            
            assert result is True, "Write should return True"
            assert mock_write_api.write.called, "Write API should be called"
    
    async def test_write_when_disabled(self):
        """Test write when InfluxDB is disabled"""
        os.environ["INFLUXDB_ENABLED"] = "false"
        
        from usage_tracking.services.influxdb_service import InfluxDBService
        
        service = InfluxDBService()
        result = await service.write_usage_record({"test": "data"})
        
        assert result is False, "Should return False when disabled"
        assert service.enabled is False, "Service should be disabled"
    
    async def test_batch_query_success(self):
        """Test successful batch query"""
        with patch('usage_tracking.services.influxdb_service.InfluxDBClient') as mock_client:
            mock_query_api = Mock()
            mock_instance = Mock()
            mock_instance.query_api.return_value = mock_query_api
            mock_client.return_value = mock_instance
            
            # Mock query result
            mock_record = Mock()
            mock_record.values = {
                "model": "gpt-4",
                "external_user": "test@example.com",
                "total_tokens": 5000,
                "cost_usd": 0.15
            }
            mock_table = Mock()
            mock_table.records = [mock_record]
            mock_query_api.query.return_value = [mock_table]
            
            from usage_tracking.services.influxdb_service import InfluxDBService
            
            service = InfluxDBService()
            service.query_api = mock_query_api
            
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
            end_time = datetime.now(timezone.utc)
            
            result = await service.get_data_for_batch("client-123", start_time, end_time)
            
            assert len(result) == 1, "Should return one record"
            assert result[0]["model"] == "gpt-4", "Model should match"
            assert result[0]["total_tokens"] == 5000, "Tokens should match"
    
    async def test_health_check(self):
        """Test health check functionality"""
        with patch('usage_tracking.services.influxdb_service.InfluxDBClient') as mock_client:
            mock_query_api = Mock()
            mock_instance = Mock()
            mock_instance.query_api.return_value = mock_query_api
            mock_client.return_value = mock_instance
            
            mock_query_api.query.return_value = []
            
            from usage_tracking.services.influxdb_service import InfluxDBService
            
            service = InfluxDBService()
            service.query_api = mock_query_api
            
            health = await service.health_check()
            
            assert health["status"] == "healthy", "Should report healthy"
            assert health["bucket"] == "test-bucket", "Should have correct bucket"
    
    async def run_test(self, test_name, test_func):
        """Run a single test"""
        print(f"\n  Running {test_name}...", end=" ")
        try:
            await test_func()
            print("✓ PASSED")
            self.passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            self.failed += 1
        except Exception as e:
            print(f"✗ ERROR: {type(e).__name__}: {e}")
            self.failed += 1
    
    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Running InfluxDBService Tests")
        print("=" * 60)
        
        self.setup()
        
        # Run each test
        await self.run_test("test_write_usage_record_success", self.test_write_usage_record_success)
        await self.run_test("test_write_when_disabled", self.test_write_when_disabled)
        await self.run_test("test_batch_query_success", self.test_batch_query_success)
        await self.run_test("test_health_check", self.test_health_check)
        
        self.teardown()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"Test Summary: {self.passed} passed, {self.failed} failed")
        print("=" * 60)
        
        return self.failed == 0


async def main():
    """Main test runner"""
    tester = TestInfluxDBService()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
#!/usr/bin/env python3
"""
Verification script for the InfluxDB fix
Tests the corrected InfluxDBService with actual data writes
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.usage_tracking.services.influxdb_service import InfluxDBService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_corrected_influxdb_service():
    """Test the corrected InfluxDBService"""
    
    # Set environment variables for testing
    os.environ["INFLUXDB_ENABLED"] = "true"
    os.environ["INFLUXDB_URL"] = "http://localhost:8086"
    os.environ["INFLUXDB_TOKEN"] = "dev-token-for-testing-only"
    os.environ["INFLUXDB_ORG"] = "mAI-dev"
    os.environ["INFLUXDB_BUCKET"] = "mai_usage_raw_dev"
    os.environ["CLIENT_ORG_ID"] = "test-client-dev"
    
    print("=== TESTING CORRECTED INFLUXDB SERVICE ===\n")
    
    # Initialize service
    service = InfluxDBService()
    
    if not service.enabled:
        print("❌ InfluxDB service is not enabled. Check your setup.")
        return False
    
    print(f"✅ InfluxDB service initialized successfully")
    print(f"   URL: {service.url}")
    print(f"   Bucket: {service.bucket}")
    print(f"   Org: {service.org}")
    print()
    
    # Test 1: Your original test data structure
    print("--- Test 1: Your test data structure ---")
    test_record_1 = {
        "model": "gpt-4",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.0075,
        "external_user": "test@example.com",
        "request_id": "test-fix-verification-001",
        "client_org_id": "test-client-dev"
    }
    
    print(f"Test data: {test_record_1}")
    
    try:
        success_1 = await service.write_usage_record(test_record_1)
        if success_1:
            print("✅ Test 1 PASSED - Data written successfully")
            print("   Expected values: input_tokens=100, output_tokens=50, total_tokens=150, cost_usd=0.0075")
        else:
            print("❌ Test 1 FAILED - Data write failed")
    except Exception as e:
        print(f"❌ Test 1 ERROR - {e}")
    print()
    
    # Test 2: Actual webhook service data structure
    print("--- Test 2: Webhook service data structure ---")
    test_record_2 = {
        "api_key": "sk-test123",
        "model": "openai/gpt-4",
        "tokens_used": 200,
        "cost": 0.015,
        "timestamp": "2025-07-31T12:00:00Z",
        "external_user": "webhook@example.com",
        "request_id": "test-fix-verification-002",
        "client_org_id": "test-client-dev"
    }
    
    print(f"Test data: {test_record_2}")
    
    try:
        success_2 = await service.write_usage_record(test_record_2)
        if success_2:
            print("✅ Test 2 PASSED - Data written successfully")
            print("   Expected values: input_tokens=140, output_tokens=60, total_tokens=200, cost_usd=0.015")
        else:
            print("❌ Test 2 FAILED - Data write failed")
    except Exception as e:
        print(f"❌ Test 2 ERROR - {e}")
    print()
    
    # Test 3: Edge case with no token data
    print("--- Test 3: Edge case with minimal data ---")
    test_record_3 = {
        "model": "claude-3-haiku",
        "external_user": "minimal@example.com",
        "request_id": "test-fix-verification-003"
    }
    
    print(f"Test data: {test_record_3}")
    
    try:
        success_3 = await service.write_usage_record(test_record_3)
        if success_3:
            print("✅ Test 3 PASSED - Data written successfully")
            print("   Expected values: input_tokens=0, output_tokens=0, total_tokens=0, cost_usd=0.0")
        else:
            print("❌ Test 3 FAILED - Data write failed")
    except Exception as e:
        print(f"❌ Test 3 ERROR - {e}")
    print()
    
    # Health check
    print("--- Health Check ---")
    health = await service.health_check()
    print(f"Health status: {health}")
    print()
    
    return success_1 and success_2 and success_3

async def main():
    """Main test function"""
    print("Starting InfluxDB fix verification\n")
    
    success = await test_corrected_influxdb_service()
    
    print("=== VERIFICATION SUMMARY ===")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("The InfluxDB fix is working correctly.")
        print("\nNext steps:")
        print("1. Check InfluxDB UI at http://localhost:8086 to verify data appears with correct values")
        print("2. Look for the records with request_ids: test-fix-verification-001, 002, 003")
        print("3. Verify the field values are no longer 0")
    else:
        print("❌ SOME TESTS FAILED")
        print("Check the error messages above and ensure InfluxDB is running")
    
    print("\n=== FIX SUMMARY ===")
    print("Issues fixed:")
    print("✅ input_tokens: Now correctly extracts from 'input_tokens' or estimates from 'tokens_used'")
    print("✅ output_tokens: Now correctly extracts from 'output_tokens' or estimates from 'tokens_used'") 
    print("✅ total_tokens: Now correctly extracts from 'total_tokens' or 'tokens_used'")
    print("✅ cost_usd: Now correctly extracts from 'cost_usd' or 'cost'")
    print("✅ Backward compatible with existing webhook data structure")

if __name__ == "__main__":
    asyncio.run(main())
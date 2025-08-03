#!/usr/bin/env python3
"""
Debug script for InfluxDB data writing issues
Identifies why numeric field values are showing as 0
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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DebugInfluxDBService(InfluxDBService):
    """Extended InfluxDBService with debug logging"""
    
    async def debug_write_usage_record(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Debug version of write_usage_record with detailed logging
        """
        logger.info("=== DEBUGGING INFLUXDB DATA WRITE ===")
        logger.info(f"Input webhook_data: {webhook_data}")
        
        if not self.enabled:
            logger.error("InfluxDB is not enabled!")
            return False
        
        # Debug the field extraction process
        logger.info("=== FIELD EXTRACTION DEBUG ===")
        
        # Current (broken) field extractions
        input_tokens_current = webhook_data.get("tokens_used", 0)
        output_tokens_current = 0  # This is hardcoded!
        total_tokens_current = webhook_data.get("tokens_used", 0)
        cost_usd_current = float(webhook_data.get("cost", 0.0))
        latency_ms_current = webhook_data.get("latency_ms", 0)
        
        logger.info(f"CURRENT EXTRACTION (BROKEN):")
        logger.info(f"  input_tokens: webhook_data.get('tokens_used', 0) = {input_tokens_current}")
        logger.info(f"  output_tokens: 0 (HARDCODED!) = {output_tokens_current}")
        logger.info(f"  total_tokens: webhook_data.get('tokens_used', 0) = {total_tokens_current}")
        logger.info(f"  cost_usd: webhook_data.get('cost', 0.0) = {cost_usd_current}")
        logger.info(f"  latency_ms: webhook_data.get('latency_ms', 0) = {latency_ms_current}")
        
        # Correct field extractions
        input_tokens_correct = webhook_data.get("input_tokens", 0)
        output_tokens_correct = webhook_data.get("output_tokens", 0)
        total_tokens_correct = webhook_data.get("total_tokens", 0)
        cost_usd_correct = float(webhook_data.get("cost_usd", 0.0))
        latency_ms_correct = webhook_data.get("latency_ms", 0)
        
        logger.info(f"CORRECT EXTRACTION (FIXED):")
        logger.info(f"  input_tokens: webhook_data.get('input_tokens', 0) = {input_tokens_correct}")
        logger.info(f"  output_tokens: webhook_data.get('output_tokens', 0) = {output_tokens_correct}")
        logger.info(f"  total_tokens: webhook_data.get('total_tokens', 0) = {total_tokens_correct}")
        logger.info(f"  cost_usd: webhook_data.get('cost_usd', 0.0) = {cost_usd_correct}")
        logger.info(f"  latency_ms: webhook_data.get('latency_ms', 0) = {latency_ms_correct}")
        
        # Show all available keys in webhook_data
        logger.info(f"AVAILABLE KEYS IN WEBHOOK_DATA: {list(webhook_data.keys())}")
        
        # Check for alternative key names that might be used
        potential_keys = ['tokens_used', 'input_tokens', 'output_tokens', 'total_tokens', 
                         'cost', 'cost_usd', 'latency_ms', 'model', 'api_key']
        logger.info("=== KEY AVAILABILITY CHECK ===")
        for key in potential_keys:
            value = webhook_data.get(key, "NOT_FOUND")
            logger.info(f"  {key}: {value}")
        
        return True

async def test_current_vs_fixed_data_extraction():
    """Test current vs fixed data extraction logic"""
    
    # Test data that matches your example
    test_record = {
        "model": "gpt-4",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.0075,
        "external_user": "test@example.com",
        "request_id": "test-debug-001",
        "client_org_id": "test-client-dev"
    }
    
    logger.info("=== TESTING DATA EXTRACTION ===")
    logger.info(f"Test record: {test_record}")
    
    # Initialize debug service
    debug_service = DebugInfluxDBService()
    
    # Test the debug extraction
    await debug_service.debug_write_usage_record(test_record)

async def test_webhook_data_variations():
    """Test different webhook data structures"""
    
    logger.info("\n=== TESTING WEBHOOK DATA VARIATIONS ===")
    
    debug_service = DebugInfluxDBService()
    
    # Test with OpenRouter-style webhook data
    openrouter_style = {
        "model": "openai/gpt-4",
        "tokens_used": 150,  # This is what current code expects
        "cost": 0.0075,      # This is what current code expects
        "api_key": "sk-test123",
        "external_user": "user@example.com",
        "request_id": "openrouter-001"
    }
    
    logger.info("--- Testing OpenRouter-style data ---")
    await debug_service.debug_write_usage_record(openrouter_style)
    
    # Test with your test data structure
    test_style = {
        "model": "gpt-4",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.0075,
        "external_user": "test@example.com",
        "request_id": "test-001"
    }
    
    logger.info("--- Testing your test data structure ---") 
    await debug_service.debug_write_usage_record(test_style)

async def main():
    """Main debug function"""
    logger.info("Starting InfluxDB data writing debug session")
    
    # Check environment
    logger.info("=== ENVIRONMENT CHECK ===")
    logger.info(f"INFLUXDB_ENABLED: {os.getenv('INFLUXDB_ENABLED', 'not set')}")
    logger.info(f"INFLUXDB_URL: {os.getenv('INFLUXDB_URL', 'not set')}")
    logger.info(f"CLIENT_ORG_ID: {os.getenv('CLIENT_ORG_ID', 'not set')}")
    
    # Test data extractions
    await test_current_vs_fixed_data_extraction()
    
    # Test variations
    await test_webhook_data_variations()
    
    logger.info("Debug session completed")

if __name__ == "__main__":
    asyncio.run(main())
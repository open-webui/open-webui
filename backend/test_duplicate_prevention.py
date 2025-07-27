#!/usr/bin/env python3
"""
Test script for duplicate prevention in usage tracking
Tests with real OpenRouter data provided by the user
"""

import sys
import os
import asyncio
from datetime import datetime
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

async def test_duplicate_prevention():
    """Test duplicate prevention with OpenRouter data"""
    
    # Import after path setup
    from open_webui.utils.openrouter_client_manager import openrouter_client_manager
    from open_webui.models.organization_usage import ProcessedGenerationDB, ClientUsageDB
    
    # Test data from user's OpenRouter response
    test_generation_id = "gen_01jasszm6m13e27ms9p6a3q3y6"
    test_user_id = "b2e10c4b-5678-efgh-ijkl-mnopqrstuvwx"
    test_model = "anthropic/claude-3.7-sonnet"
    test_input_tokens = 1607
    test_output_tokens = 36
    test_raw_cost = 0.0019644
    
    print(f"\n🧪 Testing duplicate prevention with generation_id: {test_generation_id}")
    print("=" * 80)
    
    # Test 1: First recording should succeed
    print("\n📝 Test 1: First recording (should succeed)")
    result1 = await openrouter_client_manager.record_real_time_usage(
        user_id=test_user_id,
        model_name=test_model,
        input_tokens=test_input_tokens,
        output_tokens=test_output_tokens,
        raw_cost=test_raw_cost,
        generation_id=test_generation_id,
        provider="anthropic",
        generation_time=22.30
    )
    print(f"Result: {'✅ Success' if result1 else '❌ Failed'}")
    
    # Check if generation was marked as processed
    # We need to get the client_org_id for testing
    from open_webui.config import OPENROUTER_EXTERNAL_USER
    client_org_id = OPENROUTER_EXTERNAL_USER or "test_client"
    is_processed = ProcessedGenerationDB.is_generation_processed(test_generation_id, client_org_id)
    print(f"Generation marked as processed: {'✅ Yes' if is_processed else '❌ No'}")
    
    # Test 2: Second recording with same generation_id should be skipped
    print("\n📝 Test 2: Duplicate recording (should skip)")
    result2 = await openrouter_client_manager.record_real_time_usage(
        user_id=test_user_id,
        model_name=test_model,
        input_tokens=test_input_tokens,
        output_tokens=test_output_tokens,
        raw_cost=test_raw_cost,
        generation_id=test_generation_id,
        provider="anthropic",
        generation_time=22.30
    )
    print(f"Result: {'✅ Skipped (as expected)' if result2 else '❌ Failed'}")
    
    # Test 3: Recording without generation_id should always succeed
    print("\n📝 Test 3: Recording without generation_id (should succeed)")
    result3 = await openrouter_client_manager.record_real_time_usage(
        user_id=test_user_id,
        model_name=test_model,
        input_tokens=100,
        output_tokens=50,
        raw_cost=0.001,
        generation_id=None,  # No generation_id
        provider="anthropic"
    )
    print(f"Result: {'✅ Success' if result3 else '❌ Failed'}")
    
    # Test 4: Different generation_id should succeed
    print("\n📝 Test 4: Different generation_id (should succeed)")
    different_id = "gen_different_12345678901234567890"
    result4 = await openrouter_client_manager.record_real_time_usage(
        user_id=test_user_id,
        model_name=test_model,
        input_tokens=200,
        output_tokens=100,
        raw_cost=0.002,
        generation_id=different_id,
        provider="anthropic"
    )
    print(f"Result: {'✅ Success' if result4 else '❌ Failed'}")
    
    # Verify database state
    print("\n📊 Database verification:")
    
    # Check processed generations count
    from open_webui.config import DATA_DIR
    import sqlite3
    
    db_path = os.path.join(DATA_DIR, "webui.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count processed generations
    cursor.execute("SELECT COUNT(*) FROM processed_generations WHERE generation_id IN (?, ?)", 
                   (test_generation_id, different_id))
    processed_count = cursor.fetchone()[0]
    print(f"Processed generations in DB: {processed_count} (expected: 2)")
    
    # Check usage records for today
    cursor.execute("""
        SELECT COUNT(*), SUM(total_tokens), SUM(markup_cost) 
        FROM client_daily_usage 
        WHERE usage_date = date('now')
    """)
    usage_stats = cursor.fetchone()
    print(f"Today's usage records: {usage_stats[0]} entries, {usage_stats[1] or 0} tokens, ${usage_stats[2] or 0:.6f}")
    
    conn.close()
    
    print("\n✅ Duplicate prevention test completed!")
    print("=" * 80)

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_duplicate_prevention())
#!/usr/bin/env python3
"""
Simple test for duplicate prevention - to be run inside the Docker container
"""

import asyncio
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def test_duplicate_prevention():
    """Test duplicate prevention with OpenRouter data"""
    
    from open_webui.utils.openrouter_client_manager import openrouter_client_manager
    from open_webui.models.organization_usage import ProcessedGenerationDB
    from open_webui.config import OPENROUTER_EXTERNAL_USER
    
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
    
    # Small delay to ensure DB write completes
    await asyncio.sleep(0.5)
    
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
    print(f"Result: {'✅ Skipped successfully' if result2 else '❌ Failed (should have been skipped)'}")
    
    # Test 3: Different generation_id should succeed
    print("\n📝 Test 3: Different generation_id (should succeed)")
    different_id = f"gen_different_{datetime.now().timestamp()}"
    result3 = await openrouter_client_manager.record_real_time_usage(
        user_id=test_user_id,
        model_name=test_model,
        input_tokens=200,
        output_tokens=100,
        raw_cost=0.002,
        generation_id=different_id,
        provider="anthropic"
    )
    print(f"Result: {'✅ Success' if result3 else '❌ Failed'}")
    
    print("\n✅ Duplicate prevention test completed!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_duplicate_prevention())
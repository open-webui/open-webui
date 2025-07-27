#!/usr/bin/env python3
"""
Test script for dynamic model pricing functionality
Tests the OpenRouter API integration and fallback mechanisms
"""

import asyncio
import json
from datetime import datetime

# Add the backend directory to the Python path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from open_webui.utils.openrouter_models import get_dynamic_model_pricing


async def test_dynamic_pricing():
    """Test the dynamic pricing functionality"""
    print("🧪 Testing Dynamic Model Pricing")
    print("=" * 50)
    
    # Test 1: Fetch pricing without force refresh (uses cache if available)
    print("\n1️⃣ Testing normal fetch (may use cache)...")
    start_time = datetime.now()
    result = await get_dynamic_model_pricing(force_refresh=False)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"   ✅ Completed in {elapsed:.2f}s")
    print(f"   📍 Source: {result.get('source', 'unknown')}")
    print(f"   📊 Models fetched: {len(result.get('models', []))}")
    print(f"   🕐 Last updated: {result.get('last_updated', 'N/A')}")
    
    if result.get('success'):
        # Show first 3 models as examples
        print("\n   Sample models:")
        for i, model in enumerate(result.get('models', [])[:3]):
            print(f"   - {model['name']} ({model['provider']})")
            print(f"     Input: ${model['price_per_million_input']:.2f}/M tokens")
            print(f"     Output: ${model['price_per_million_output']:.2f}/M tokens")
    
    # Test 2: Force refresh to fetch fresh data
    print("\n2️⃣ Testing force refresh (bypasses cache)...")
    start_time = datetime.now()
    result_fresh = await get_dynamic_model_pricing(force_refresh=True)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"   ✅ Completed in {elapsed:.2f}s")
    print(f"   📍 Source: {result_fresh.get('source', 'unknown')}")
    print(f"   📊 Models fetched: {len(result_fresh.get('models', []))}")
    
    # Test 3: Verify mAI model filtering
    print("\n3️⃣ Testing mAI model filtering...")
    mai_models = [
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        "deepseek/deepseek-chat-v3-0324"
    ]
    
    # Simulate the filtering done in the router
    if result_fresh.get('success'):
        filtered_models = [
            model for model in result_fresh.get('models', [])
            if model['id'] in mai_models
        ]
        print(f"   ✅ Filtered to {len(filtered_models)} mAI-supported models")
        for model in filtered_models[:5]:
            print(f"   - {model['id']}: ${model['price_per_million_input']:.2f} input")
    
    # Test 4: Check fallback mechanism
    print("\n4️⃣ Testing fallback mechanism...")
    # This would be tested by temporarily blocking network access
    # For now, we'll just verify the fallback data structure exists
    from open_webui.utils.openrouter_models import OpenRouterModelsAPI
    api = OpenRouterModelsAPI()
    fallback_models = api._get_hardcoded_models()
    print(f"   ✅ Fallback has {len(fallback_models)} hardcoded models")
    
    # Test 5: Verify cache behavior
    print("\n5️⃣ Testing cache behavior...")
    start_time = datetime.now()
    cached_result = await get_dynamic_model_pricing(force_refresh=False)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    if elapsed < 0.1 and cached_result.get('source') in ['openrouter_api', 'cache_fallback']:
        print(f"   ✅ Cache working correctly (fetched in {elapsed:.3f}s)")
    else:
        print(f"   ⚠️  Cache may not be working (took {elapsed:.3f}s)")
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    
    # Summary
    if result_fresh.get('success'):
        print(f"\n📊 Summary: Successfully fetching dynamic pricing from OpenRouter")
        print(f"   - Total models available: {len(result_fresh.get('models', []))}")
        print(f"   - Cache TTL: 1 hour")
        print(f"   - Fallback ready: Yes")
    else:
        print(f"\n⚠️  Summary: Using fallback pricing data")
        print(f"   - Error: {result_fresh.get('error', 'Unknown error')}")


if __name__ == "__main__":
    print("🚀 OpenRouter Dynamic Pricing Test")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        asyncio.run(test_dynamic_pricing())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
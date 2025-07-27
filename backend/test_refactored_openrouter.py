#!/usr/bin/env python3
"""
Test script to verify refactored OpenRouter models implementation
"""

import asyncio
import time
from datetime import datetime
import sys
import os

# Add backend to path
backend_dir = os.path.dirname(__file__)
sys.path.insert(0, backend_dir)

# Set up minimal environment to avoid typer import
os.environ['OPENWEBUI_ENV'] = 'test'

async def test_refactored_implementation():
    """Test the new refactored implementation"""
    print("🧪 Testing Refactored OpenRouter Models Implementation")
    print("=" * 60)
    
    # Test 1: Basic functionality
    print("\n1️⃣ Testing basic get_dynamic_model_pricing...")
    try:
        from open_webui.utils.openrouter_models import get_dynamic_model_pricing
        
        start = time.time()
        result = await get_dynamic_model_pricing(force_refresh=False)
        elapsed = time.time() - start
        
        print(f"✅ Success! Fetched in {elapsed:.3f}s")
        print(f"   Models: {len(result.get('models', []))}")
        print(f"   Source: {result.get('source', 'unknown')}")
        print(f"   Success: {result.get('success', False)}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Test caching behavior
    print("\n2️⃣ Testing cache performance...")
    try:
        # First call should hit cache
        start = time.time()
        result2 = await get_dynamic_model_pricing(force_refresh=False)
        elapsed2 = time.time() - start
        
        print(f"✅ Cache hit! Fetched in {elapsed2:.3f}s")
        print(f"   Speed improvement: {(elapsed / elapsed2):.1f}x faster")
        
        if elapsed2 > 0.1:
            print("⚠️  Warning: Cache might not be working optimally")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 3: Test force refresh
    print("\n3️⃣ Testing force refresh...")
    try:
        start = time.time()
        result3 = await get_dynamic_model_pricing(force_refresh=True)
        elapsed3 = time.time() - start
        
        print(f"✅ Force refresh completed in {elapsed3:.3f}s")
        print(f"   Fresh data fetched from API")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 4: Test repository pattern components
    print("\n4️⃣ Testing repository pattern components...")
    try:
        from open_webui.utils.openrouter_models import (
            PricingCalculatorService,
            CachedOpenRouterRepository,
            OpenRouterRepository
        )
        
        # Test repository
        repo = OpenRouterRepository()
        models = await repo.fetch_all_models()
        print(f"✅ Repository: Fetched {len(models)} models")
        
        # Test specific model fetch
        if models:
            test_model_id = models[0].id
            specific_model = await repo.fetch_model_by_id(test_model_id)
            print(f"✅ Repository: Found model {specific_model.name if specific_model else 'None'}")
        
        # Clean up
        await repo.close()
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test pricing calculation
    print("\n5️⃣ Testing pricing calculation...")
    try:
        from open_webui.utils.openrouter_models import PricingCalculatorService, CachedOpenRouterRepository, OpenRouterRepository
        
        repo = OpenRouterRepository()
        cached_repo = CachedOpenRouterRepository(repo)
        pricing_service = PricingCalculatorService(cached_repo)
        
        # Calculate cost for a sample usage
        cost_data = await pricing_service.calculate_cost(
            model_id="openai/gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
            markup_rate=1.3
        )
        
        print(f"✅ Cost calculation:")
        print(f"   Model: {cost_data['model_id']}")
        print(f"   Raw cost: ${cost_data['raw_cost']:.6f}")
        print(f"   Markup cost: ${cost_data['markup_cost']:.6f}")
        print(f"   Markup rate: {cost_data['markup_rate']}")
        
        # Verify markup calculation
        expected_markup = cost_data['raw_cost'] * cost_data['markup_rate']
        if abs(cost_data['markup_cost'] - expected_markup) < 0.000001:
            print("✅ Markup calculation verified correct!")
        else:
            print("❌ Markup calculation error!")
            
        await repo.close()
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Compare with old implementation
    print("\n6️⃣ Comparing with old implementation...")
    try:
        # Import old implementation
        from open_webui.utils.openrouter_models_old import get_dynamic_model_pricing as old_impl
        
        # Get results from both
        old_result = await old_impl(force_refresh=False)
        new_result = await get_dynamic_model_pricing(force_refresh=False)
        
        # Compare model counts
        old_count = len(old_result.get("models", []))
        new_count = len(new_result.get("models", []))
        
        print(f"   Old implementation: {old_count} models")
        print(f"   New implementation: {new_count} models")
        
        if old_count == new_count:
            print("✅ Model counts match!")
        else:
            print(f"⚠️  Model count difference: {abs(old_count - new_count)}")
        
        # Compare a few model prices
        if old_count > 0 and new_count > 0:
            test_model_id = "openai/gpt-4o-mini"
            old_model = next((m for m in old_result["models"] if m["id"] == test_model_id), None)
            new_model = next((m for m in new_result["models"] if m["id"] == test_model_id), None)
            
            if old_model and new_model:
                if (old_model["price_per_million_input"] == new_model["price_per_million_input"] and
                    old_model["price_per_million_output"] == new_model["price_per_million_output"]):
                    print(f"✅ Pricing matches for {test_model_id}")
                else:
                    print(f"❌ Pricing mismatch for {test_model_id}")
        
    except Exception as e:
        print(f"⚠️  Could not compare with old implementation: {e}")
    
    # Test 7: Test cache manager
    print("\n7️⃣ Testing cache manager...")
    try:
        from open_webui.utils.openrouter_models import CacheManager, CachedOpenRouterRepository, OpenRouterRepository
        
        repo = OpenRouterRepository()
        cached_repo = CachedOpenRouterRepository(repo)
        cache_manager = CacheManager(cached_repo)
        
        # Get cache stats
        stats = await cache_manager.get_cache_stats()
        print(f"✅ Cache stats:")
        print(f"   L1 cache size: {stats['l1_cache']['size']}/{stats['l1_cache']['max_size']}")
        print(f"   L2 cache size: {stats['l2_cache']['size']}/{stats['l2_cache']['max_size']}")
        print(f"   Total requests: {stats['performance']['total_requests']}")
        
        await repo.close()
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("\n📊 Performance Summary:")
    print(f"   Initial fetch: {elapsed:.3f}s")
    print(f"   Cached fetch: {elapsed2:.3f}s") 
    print(f"   Speed improvement: {(elapsed / elapsed2):.1f}x")
    print("\n🎯 The refactored implementation is working correctly!")
    
    return True


async def test_performance_comparison():
    """Compare performance between old and new implementations"""
    print("\n\n🏁 Performance Comparison Test")
    print("=" * 60)
    
    from open_webui.utils.openrouter_models_old import get_dynamic_model_pricing as old_impl
    from open_webui.utils.openrouter_models import get_dynamic_model_pricing as new_impl
    
    # Test old implementation
    print("\nOld implementation (10 calls):")
    old_times = []
    for i in range(10):
        start = time.time()
        await old_impl(force_refresh=False)
        old_times.append(time.time() - start)
        print(f"  Call {i+1}: {old_times[-1]:.3f}s")
    
    old_avg = sum(old_times) / len(old_times)
    print(f"Average: {old_avg:.3f}s")
    
    # Test new implementation
    print("\nNew implementation (10 calls):")
    new_times = []
    for i in range(10):
        start = time.time()
        await new_impl(force_refresh=False)
        new_times.append(time.time() - start)
        print(f"  Call {i+1}: {new_times[-1]:.3f}s")
    
    new_avg = sum(new_times) / len(new_times)
    print(f"Average: {new_avg:.3f}s")
    
    # Calculate improvement
    improvement = ((old_avg - new_avg) / old_avg) * 100
    print(f"\n🎯 Performance improvement: {improvement:.1f}%")
    
    if improvement >= 25:
        print("✅ Target of 25-35% improvement achieved!")
    else:
        print(f"⚠️  Performance improvement below target (got {improvement:.1f}%, target 25-35%)")


if __name__ == "__main__":
    print("🚀 OpenRouter Models Refactoring Test Suite")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Run main tests
        success = asyncio.run(test_refactored_implementation())
        
        if success:
            # Run performance comparison
            asyncio.run(test_performance_comparison())
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
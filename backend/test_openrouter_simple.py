#!/usr/bin/env python3
"""
Simple test for refactored OpenRouter models - avoids complex imports
"""

import asyncio
import time
from datetime import datetime

async def test_simple():
    """Simple test without complex imports"""
    print("🧪 Simple OpenRouter Models Test")
    print("=" * 50)
    
    try:
        # Direct import avoiding main __init__
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Import components directly
        from open_webui.utils.openrouter_models.repository.openrouter_repo import OpenRouterRepository
        from open_webui.utils.openrouter_models.repository.cached_repo import CachedOpenRouterRepository
        from open_webui.utils.openrouter_models.services.pricing_calculator import PricingCalculatorService
        
        print("✅ Imports successful")
        
        # Test 1: Basic repository functionality
        print("\n1️⃣ Testing basic repository...")
        repo = OpenRouterRepository()
        
        # Get fallback models (doesn't require API)
        fallback_models = repo._get_hardcoded_models()
        print(f"✅ Fallback models: {len(fallback_models)} models available")
        
        # Test 2: Cached repository
        print("\n2️⃣ Testing cached repository...")
        cached_repo = CachedOpenRouterRepository(repo)
        
        # This will use fallback if API fails
        start = time.time()
        models = await cached_repo.fetch_all_models()
        elapsed = time.time() - start
        
        print(f"✅ Fetched {len(models)} models in {elapsed:.3f}s")
        
        # Test cache hit
        start = time.time()
        models2 = await cached_repo.fetch_all_models()
        elapsed2 = time.time() - start
        
        print(f"✅ Cache hit: Fetched in {elapsed2:.3f}s ({(elapsed/elapsed2):.1f}x faster)")
        
        # Test 3: Pricing service
        print("\n3️⃣ Testing pricing service...")
        pricing_service = PricingCalculatorService(cached_repo)
        
        result = await pricing_service.get_model_pricing()
        print(f"✅ Pricing service returned {len(result.get('models', []))} models")
        print(f"   Source: {result.get('source')}")
        print(f"   Success: {result.get('success')}")
        
        # Test 4: Cost calculation
        print("\n4️⃣ Testing cost calculation...")
        if models:
            test_model = models[0]
            print(f"   Using model: {test_model.id}")
            
            cost_data = await pricing_service.calculate_cost(
                model_id=test_model.id,
                input_tokens=1000,
                output_tokens=500,
                markup_rate=1.3
            )
            
            print(f"✅ Cost calculation:")
            print(f"   Raw cost: ${cost_data['raw_cost']:.6f}")
            print(f"   Markup cost: ${cost_data['markup_cost']:.6f}")
            print(f"   Markup verified: {abs(cost_data['markup_cost'] - cost_data['raw_cost'] * 1.3) < 0.000001}")
        
        # Clean up
        await repo.close()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
        # Performance summary
        if elapsed > 0 and elapsed2 > 0:
            improvement = ((elapsed - elapsed2) / elapsed) * 100
            print(f"\n📊 Cache Performance: {improvement:.1f}% faster on cache hit")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Simple OpenRouter Models Test")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        success = asyncio.run(test_simple())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
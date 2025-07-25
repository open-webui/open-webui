#!/usr/bin/env python3
"""
Test script to verify the model pricing API endpoint
"""

import sys
import os
sys.path.append('backend')

import asyncio
from backend.open_webui.routers.usage_tracking import get_mai_model_pricing

async def test_model_pricing_api():
    print("=== Testing Model Pricing API Endpoint ===")
    print()
    
    try:
        # Test the API endpoint directly
        result = await get_mai_model_pricing()
        
        print(f"✅ API Response Success: {result.get('success', False)}")
        
        models = result.get('models', [])
        print(f"📊 Number of models returned: {len(models)}")
        print()
        
        if models:
            print("🔍 Model Pricing Data:")
            print("-" * 100)
            print(f"{'#':<3} {'Model Name':<35} {'Provider':<10} {'Input $/1M':<12} {'Output $/1M':<13} {'Category':<12}")
            print("-" * 100)
            
            for i, model in enumerate(models, 1):
                model_name = model.get('name', 'Unknown')
                provider = model.get('provider', 'Unknown')
                input_price = f"${model.get('price_per_million_input', 0):.2f}"
                output_price = f"${model.get('price_per_million_output', 0):.2f}"
                category = model.get('category', 'Unknown')
                
                print(f"{i:<3} {model_name:<35} {provider:<10} {input_price:<12} {output_price:<13} {category:<12}")
            
            print("-" * 100)
            print()
            
            # Count models by category
            categories = {}
            for model in models:
                category = model.get('category', 'Unknown')
                categories[category] = categories.get(category, 0) + 1
            
            print("📈 Models by Category:")
            for category, count in categories.items():
                print(f"   • {category}: {count} models")
            
            print()
            if len(models) == 12:
                print("✅ SUCCESS: All 12 models are available!")
            else:
                print(f"⚠️  Expected 12 models, got {len(models)}")
        else:
            print("❌ No models returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_model_pricing_api())
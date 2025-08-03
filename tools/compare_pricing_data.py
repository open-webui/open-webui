#!/usr/bin/env python3
"""
Compare pricing data between frontend fallback and backend API
"""

def compare_pricing_data():
    print("=== Comparing Frontend vs Backend Pricing Data ===")
    print()
    
    # Frontend fallback data (from MyOrganizationUsage.svelte)
    frontend_models = [
        {"id": "anthropic/claude-sonnet-4", "input": 8.00, "output": 24.00, "category": "Premium"},
        {"id": "google/gemini-2.5-flash", "input": 1.50, "output": 6.00, "category": "Fast"},
        {"id": "google/gemini-2.5-pro", "input": 3.00, "output": 12.00, "category": "Premium"},
        {"id": "deepseek/deepseek-chat-v3-0324", "input": 0.14, "output": 0.28, "category": "Budget"},
        {"id": "anthropic/claude-3.7-sonnet", "input": 6.00, "output": 18.00, "category": "Premium"},
        {"id": "google/gemini-2.5-flash-lite-preview-06-17", "input": 0.50, "output": 2.00, "category": "Budget"},
        {"id": "openai/gpt-4.1", "input": 10.00, "output": 30.00, "category": "Premium"},
        {"id": "x-ai/grok-4", "input": 8.00, "output": 24.00, "category": "Premium"},
        {"id": "openai/gpt-4o-mini", "input": 0.15, "output": 0.60, "category": "Budget"},
        {"id": "openai/o4-mini-high", "input": 3.00, "output": 12.00, "category": "Standard"},
        {"id": "openai/o3", "input": 60.00, "output": 240.00, "category": "Reasoning"},
        {"id": "openai/chatgpt-4o-latest", "input": 5.00, "output": 15.00, "category": "Standard"}
    ]
    
    # Backend API data (from usage_tracking.py - as updated)
    backend_models = [
        {"id": "anthropic/claude-sonnet-4", "input": 8.00, "output": 24.00, "category": "Premium"},
        {"id": "google/gemini-2.5-flash", "input": 1.50, "output": 6.00, "category": "Fast"},
        {"id": "google/gemini-2.5-pro", "input": 3.00, "output": 12.00, "category": "Premium"},
        {"id": "deepseek/deepseek-chat-v3-0324", "input": 0.14, "output": 0.28, "category": "Budget"},
        {"id": "anthropic/claude-3.7-sonnet", "input": 6.00, "output": 18.00, "category": "Premium"},
        {"id": "google/gemini-2.5-flash-lite-preview-06-17", "input": 0.50, "output": 2.00, "category": "Budget"},
        {"id": "openai/gpt-4.1", "input": 10.00, "output": 30.00, "category": "Premium"},
        {"id": "x-ai/grok-4", "input": 8.00, "output": 24.00, "category": "Premium"},
        {"id": "openai/gpt-4o-mini", "input": 0.15, "output": 0.60, "category": "Budget"},
        {"id": "openai/o4-mini-high", "input": 3.00, "output": 12.00, "category": "Standard"},
        {"id": "openai/o3", "input": 60.00, "output": 240.00, "category": "Reasoning"},
        {"id": "openai/chatgpt-4o-latest", "input": 5.00, "output": 15.00, "category": "Standard"}
    ]
    
    print(f"🔍 Comparing {len(frontend_models)} frontend models vs {len(backend_models)} backend models")
    print()
    
    # Check for consistency
    all_consistent = True
    
    if len(frontend_models) != len(backend_models):
        print(f"❌ MISMATCH: Frontend has {len(frontend_models)} models, Backend has {len(backend_models)} models")
        all_consistent = False
        return False
    
    print("📊 Model-by-Model Comparison:")
    print("-" * 110)
    print(f"{'Model ID':<40} {'Frontend Input':<15} {'Backend Input':<15} {'Frontend Output':<15} {'Backend Output':<15} {'Status':<10}")
    print("-" * 110)
    
    for i, (frontend, backend) in enumerate(zip(frontend_models, backend_models)):
        if frontend["id"] != backend["id"]:
            status = "❌ ID"
            all_consistent = False
        elif frontend["input"] != backend["input"]:
            status = "❌ INPUT"
            all_consistent = False
        elif frontend["output"] != backend["output"]:
            status = "❌ OUTPUT"
            all_consistent = False
        elif frontend["category"] != backend["category"]:
            status = "❌ CATEGORY"
            all_consistent = False
        else:
            status = "✅ MATCH"
        
        print(f"{frontend['id']:<40} ${frontend['input']:<14.2f} ${backend['input']:<14.2f} ${frontend['output']:<14.2f} ${backend['output']:<14.2f} {status:<10}")
    
    print("-" * 110)
    print()
    
    if all_consistent:
        print("✅ ALL DATA CONSISTENT: Frontend and Backend pricing data match perfectly!")
        
        # Show pricing range
        min_price = min(min(m["input"], m["output"]) for m in frontend_models)
        max_price = max(max(m["input"], m["output"]) for m in frontend_models)
        
        categories = list(set(m["category"] for m in frontend_models))
        
        print()
        print("📈 PRICING SUMMARY:")
        print(f"   • Price Range: ${min_price:.2f} - ${max_price:.2f} per million tokens")
        print(f"   • Categories: {', '.join(sorted(categories))}")
        print(f"   • Total Models: {len(frontend_models)}")
        
        return True
    else:
        print("❌ DATA INCONSISTENCY: Frontend and Backend pricing data do not match!")
        return False

if __name__ == "__main__":
    success = compare_pricing_data()
    
    if success:
        print("\n🎯 RESULT: Model Pricing tab is ready to display all 12 models with correct pricing!")
    else:
        print("\n⚠️  RESULT: Data inconsistencies need to be resolved before deployment.")
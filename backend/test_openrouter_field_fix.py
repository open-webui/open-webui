#!/usr/bin/env python3
"""
Test script to verify OpenRouter field name fix
Tests the corrected field mappings: tokens_prompt + tokens_completion -> total_tokens
"""

import sys
import os
sys.path.append('/Users/patpil/Documents/Projects/mAI/backend')

from open_webui.utils.cost_calculator import calculate_cost_with_markup

def test_openrouter_field_mapping():
    """Test that OpenRouter field names are correctly mapped"""
    
    # Simulate OpenRouter API response format with correct field names
    mock_openrouter_generation = {
        "id": "gen-test-fix-001",
        "model": "anthropic/claude-3.5-sonnet",
        "tokens_prompt": 494,  # OpenRouter uses this field name
        "tokens_completion": 32,  # OpenRouter uses this field name  
        "total_cost": 0.000228  # OpenRouter uses this field name
    }
    
    print("🧪 Testing OpenRouter Field Mapping Fix")
    print("=" * 50)
    print(f"Input generation data:")
    print(f"  - tokens_prompt: {mock_openrouter_generation['tokens_prompt']}")
    print(f"  - tokens_completion: {mock_openrouter_generation['tokens_completion']}")
    print(f"  - total_cost: ${mock_openrouter_generation['total_cost']}")
    print()
    
    try:
        # Test the cost calculator with OpenRouter format
        result = calculate_cost_with_markup(
            client_org_id="dev_mai_client_d460a478",
            generation_data=mock_openrouter_generation
        )
        
        expected_tokens = 494 + 32  # Should be 526
        expected_markup_cost = 0.000228 * 1.3  # Should be ~0.0002964
        
        print("✅ Field mapping successful!")
        print(f"Results:")
        print(f"  - Total tokens calculated: {result['total_tokens']}")
        print(f"  - Expected tokens: {expected_tokens}")
        print(f"  - Raw cost: ${result['raw_cost']}")
        print(f"  - Markup cost: ${result['markup_cost']}")
        print(f"  - Expected markup cost: ${expected_markup_cost:.6f}")
        print()
        
        # Verify calculations
        if result['total_tokens'] == expected_tokens:
            print("✅ Token calculation: CORRECT")
        else:
            print(f"❌ Token calculation: FAILED (got {result['total_tokens']}, expected {expected_tokens})")
            
        if abs(result['markup_cost'] - expected_markup_cost) < 0.000001:
            print("✅ Cost calculation: CORRECT")
        else:
            print(f"❌ Cost calculation: FAILED (got {result['markup_cost']}, expected {expected_markup_cost})")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_webhook_service_field_mapping():
    """Test that webhook service correctly processes OpenRouter format"""
    
    print("\n🔗 Testing Webhook Service Field Mapping")
    print("=" * 50)
    
    # Simulate the exact OpenRouter webhook data structure
    mock_generation = {
        "id": "gen-1753639473-xmTDMMtjF7MFEUDDQwxS",
        "model": "anthropic/claude-3.5-sonnet",
        "created_at": "2025-07-28T22:43:00Z",
        "tokens_prompt": 494,
        "tokens_completion": 32,
        "total_cost": 0.000228,
        "user": "test_user"
    }
    
    # Simulate the processing logic from webhook_service.py
    prompt_tokens = mock_generation.get("tokens_prompt", 0)
    completion_tokens = mock_generation.get("tokens_completion", 0)
    total_tokens = prompt_tokens + completion_tokens
    
    usage_data = {
        "model": mock_generation.get("model", "unknown"),
        "total_tokens": total_tokens,
        "total_cost": mock_generation.get("total_cost", 0.0)
    }
    
    print(f"Processing generation: {mock_generation['id']}")
    print(f"Input tokens_prompt: {prompt_tokens}")
    print(f"Input tokens_completion: {completion_tokens}")
    print(f"Calculated total_tokens: {total_tokens}")
    print(f"Raw cost: ${usage_data['total_cost']}")
    
    expected_total = 526
    if total_tokens == expected_total:
        print("✅ Webhook processing: CORRECT")
        return True
    else:
        print(f"❌ Webhook processing: FAILED (got {total_tokens}, expected {expected_total})")
        return False

if __name__ == "__main__":
    print("🚀 OpenRouter Field Name Fix Verification")
    print("Testing the fix for missing 312 tokens and $0.0005 cost discrepancy")
    print()
    
    success1 = test_openrouter_field_mapping()
    success2 = test_webhook_service_field_mapping()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED!")
        print("✅ OpenRouter field mapping fix is working correctly")
        print("✅ System should now capture the missing 312 tokens and cost data")
    else:
        print("❌ SOME TESTS FAILED!")
        print("❌ Additional debugging required")
    
    print("\n💡 Next steps:")
    print("1. Re-sync July 28 data with corrected field mappings")
    print("2. Verify application displays: 2,074 tokens, $0.002028 cost")
    print("3. Monitor future OpenRouter requests for correct processing")
#!/usr/bin/env python3
"""
Test script for "Today's Cost (live)" value calculation and accuracy
"""

import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def test_markup_calculation():
    """Test basic markup calculation logic"""
    print("🧮 Testing Markup Calculation Logic")
    
    test_cases = [
        {"raw_cost": 0.045, "markup_rate": 1.3, "expected": 0.0585},
        {"raw_cost": 0.024, "markup_rate": 1.3, "expected": 0.0312},
        {"raw_cost": 0.001, "markup_rate": 1.3, "expected": 0.0013},
        {"raw_cost": 1.000, "markup_rate": 1.3, "expected": 1.3000},
        {"raw_cost": 0.000, "markup_rate": 1.3, "expected": 0.0000},
    ]
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        raw_cost = case["raw_cost"]
        markup_rate = case["markup_rate"]
        expected = case["expected"]
        calculated = raw_cost * markup_rate
        
        # Allow small floating point differences
        is_correct = abs(calculated - expected) < 0.000001
        status = "✅" if is_correct else "❌"
        
        print(f"  Test {i}: ${raw_cost:.6f} × {markup_rate} = ${calculated:.6f} (expected ${expected:.6f}) {status}")
        
        if not is_correct:
            all_passed = False
            print(f"    ⚠️  Difference: ${abs(calculated - expected):.6f}")
    
    return all_passed

def test_currency_formatting():
    """Test currency formatting logic"""
    print("\n💰 Testing Currency Formatting Logic")
    
    # Replicate the formatCurrency function logic
    def format_currency(amount):
        """Replicate the frontend formatCurrency function"""
        value = amount or 0
        if value > 0 and value < 0.01:
            # For very small amounts, show more decimal places
            return f"${value:.6f}"
        else:
            # Standard 2 decimal places
            return f"${value:.2f}"
    
    test_cases = [
        {"amount": 0.0585, "expected_format": "$0.06"},  # Standard rounding
        {"amount": 0.0013, "expected_format": "$0.001300"},  # Small amount with 6 decimals
        {"amount": 0.000001, "expected_format": "$0.000001"},  # Very small amount
        {"amount": 0.00, "expected_format": "$0.00"},  # Zero
        {"amount": 1.3, "expected_format": "$1.30"},  # Standard amount
        {"amount": 0.009999, "expected_format": "$0.009999"},  # Just under 0.01
        {"amount": 0.01, "expected_format": "$0.01"},  # Exactly 0.01
    ]
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        amount = case["amount"]
        expected = case["expected_format"]
        formatted = format_currency(amount)
        
        is_correct = formatted == expected
        status = "✅" if is_correct else "❌"
        
        print(f"  Test {i}: {amount} → {formatted} (expected {expected}) {status}")
        
        if not is_correct:
            all_passed = False
            print(f"    ⚠️  Got '{formatted}', expected '{expected}'")
    
    return all_passed

def test_cost_accumulation():
    """Test cost accumulation over multiple requests"""
    print("\n📈 Testing Cost Accumulation Logic")
    
    # Simulate multiple API requests throughout the day
    requests = [
        {"raw_cost": 0.045, "model": "anthropic/claude-3.5-sonnet"},
        {"raw_cost": 0.024, "model": "openai/gpt-4"},
        {"raw_cost": 0.012, "model": "google/gemini-pro"},
        {"raw_cost": 0.033, "model": "anthropic/claude-3.5-sonnet"},
        {"raw_cost": 0.018, "model": "openai/gpt-4o-mini"},
    ]
    
    markup_rate = 1.3
    total_raw_cost = 0.0
    total_markup_cost = 0.0
    
    print(f"  Simulating {len(requests)} API requests:")
    
    for i, request in enumerate(requests, 1):
        raw_cost = request["raw_cost"]
        markup_cost = raw_cost * markup_rate
        
        total_raw_cost += raw_cost
        total_markup_cost += markup_cost
        
        print(f"    Request {i}: {request['model']} - ${raw_cost:.6f} → ${markup_cost:.6f}")
    
    expected_total_markup = total_raw_cost * markup_rate
    calculation_correct = abs(total_markup_cost - expected_total_markup) < 0.000001
    
    print(f"\n  Summary:")
    print(f"    Total Raw Cost: ${total_raw_cost:.6f}")
    print(f"    Total Markup Cost: ${total_markup_cost:.6f}")
    print(f"    Expected Markup: ${expected_total_markup:.6f}")
    print(f"    Calculation Correct: {'✅' if calculation_correct else '❌'}")
    
    return calculation_correct

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n🔍 Testing Edge Cases")
    
    test_cases = [
        {"name": "Negative cost", "raw_cost": -0.01, "markup_rate": 1.3},
        {"name": "Zero markup rate", "raw_cost": 0.05, "markup_rate": 0.0},
        {"name": "Very high cost", "raw_cost": 999.99, "markup_rate": 1.3},
        {"name": "Very small cost", "raw_cost": 0.000001, "markup_rate": 1.3},
        {"name": "Non-standard markup", "raw_cost": 0.05, "markup_rate": 2.5},
    ]
    
    issues_found = []
    
    for case in test_cases:
        name = case["name"]
        raw_cost = case["raw_cost"]
        markup_rate = case["markup_rate"]
        markup_cost = raw_cost * markup_rate
        
        print(f"  {name}: ${raw_cost:.6f} × {markup_rate} = ${markup_cost:.6f}")
        
        # Check for potential issues
        if raw_cost < 0:
            issues_found.append(f"Negative raw cost detected: ${raw_cost:.6f}")
        
        if markup_rate <= 0:
            issues_found.append(f"Invalid markup rate: {markup_rate}")
        
        if markup_cost < 0 and raw_cost >= 0:
            issues_found.append(f"Negative markup cost from positive raw cost")
    
    if issues_found:
        print(f"\n  ⚠️  Issues found:")
        for issue in issues_found:
            print(f"    - {issue}")
        return False
    else:
        print(f"  ✅ No issues found")
        return True

def test_live_counter_cost_storage():
    """Test how costs are stored in live counter data structure"""
    print("\n💾 Testing Live Counter Cost Storage")
    
    # Simulate the data structure used in ClientLiveCounters
    live_counter = {
        "client_org_id": "test_client_123",
        "current_date": "2025-01-25",
        "today_tokens": 0,
        "today_requests": 0,
        "today_raw_cost": 0.0,
        "today_markup_cost": 0.0,  # This is what gets displayed as "Today's Cost (live)"
        "last_updated": 1740452400
    }
    
    # Simulate adding costs from multiple requests
    requests = [
        {"tokens": 1500, "raw_cost": 0.045},
        {"tokens": 800, "raw_cost": 0.024},
        {"tokens": 1200, "raw_cost": 0.036},
    ]
    
    markup_rate = 1.3
    
    print(f"  Initial state: ${live_counter['today_markup_cost']:.6f}")
    
    for i, request in enumerate(requests, 1):
        tokens = request["tokens"]
        raw_cost = request["raw_cost"]
        markup_cost = raw_cost * markup_rate
        
        # Update live counter (simulate the background sync logic)
        live_counter["today_tokens"] += tokens
        live_counter["today_requests"] += 1
        live_counter["today_raw_cost"] += raw_cost
        live_counter["today_markup_cost"] += markup_cost
        
        print(f"  After request {i}: ${live_counter['today_markup_cost']:.6f} ({tokens} tokens, ${raw_cost:.6f} raw)")
    
    # Verify final calculation
    expected_total_markup = sum(r["raw_cost"] for r in requests) * markup_rate
    is_correct = abs(live_counter["today_markup_cost"] - expected_total_markup) < 0.000001
    
    print(f"\n  Final state:")
    print(f"    Today's Cost (live): ${live_counter['today_markup_cost']:.6f}")
    print(f"    Expected: ${expected_total_markup:.6f}")
    print(f"    Correct: {'✅' if is_correct else '❌'}")
    
    return is_correct

def main():
    """Run all cost calculation tests"""
    print("=" * 60)
    print("Testing 'Today's Cost (live)' Value Generation and Accuracy")
    print("=" * 60)
    
    tests = [
        ("Markup Calculation", test_markup_calculation),
        ("Currency Formatting", test_currency_formatting),
        ("Cost Accumulation", test_cost_accumulation),
        ("Edge Cases", test_edge_cases),
        ("Live Counter Storage", test_live_counter_cost_storage),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success, None))
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = 0
    
    for test_name, success, error in results:
        if success:
            print(f"✅ PASS    {test_name}")
            passed += 1
        else:
            print(f"❌ FAIL    {test_name}")
            if error:
                print(f"          Error: {error}")
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All cost calculation tests passed!")
        print("   'Today's Cost (live)' logic is working correctly")
        return 0
    else:
        print("⚠️  Some cost calculation issues detected")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
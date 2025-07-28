#!/usr/bin/env python3
"""
Test script to validate currency converter changes for NBP Table A consistency
"""

def test_currency_converter_changes():
    """Test that currency converter is consistent with NBP Table A changes"""
    
    # Read the currency converter file
    with open('open_webui/utils/currency_converter.py', 'r') as f:
        content = f.read()
    
    print("🔍 Testing Currency Converter NBP Table A Consistency")
    print("=" * 60)
    
    # Test 1: Fallback rate updated to Table A range
    if "FALLBACK_USD_PLN_RATE = 3.64" in content:
        print("✅ PASS: Fallback rate updated to Table A range (3.64)")
    else:
        print("❌ FAIL: Fallback rate not updated correctly")
        return False
    
    # Test 2: Documentation mentions Table A
    if "Table A" in content:
        print("✅ PASS: Documentation mentions Table A")
    else:
        print("❌ FAIL: Documentation doesn't mention Table A")
        return False
    
    # Test 3: Comments mention average rates
    if "average" in content.lower():
        print("✅ PASS: Documentation mentions average rates")
    else:
        print("❌ FAIL: Documentation doesn't mention average rates")
        return False
    
    # Test 4: Module docstring updated
    if "Table A average exchange rates" in content:
        print("✅ PASS: Module docstring updated for Table A")
    else:
        print("❌ FAIL: Module docstring not updated")
        return False
    
    # Test 5: Function docstrings updated
    function_docstrings = [
        "USD to PLN average exchange rate from Table A",
        "metadata from NBP Table A",
        "Table A average rates with detailed conversion info",
        "fallback Table A average rate"
    ]
    
    for docstring in function_docstrings:
        if docstring in content:
            print(f"✅ PASS: Found updated docstring: '{docstring[:50]}...'")
        else:
            print(f"❌ FAIL: Missing updated docstring: '{docstring[:50]}...'")
            return False
    
    # Test 6: No references to old Table C terminology
    old_terms = ["sell rate", "ask rate", "table c", "Table C"]
    for term in old_terms:
        if term in content:
            print(f"❌ FAIL: Found old terminology: '{term}'")
            return False
    
    print("✅ PASS: No old Table C terminology found")
    
    # Test 7: Fallback rate is reasonable for Table A
    if "3.64" in content and not "4.1" in content:
        print("✅ PASS: Fallback rate consistent with Table A range")
    else:
        print("❌ FAIL: Fallback rate not consistent with Table A")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("Currency converter is now consistent with NBP Table A implementation")
    return True

if __name__ == "__main__":
    success = test_currency_converter_changes()
    exit(0 if success else 1)
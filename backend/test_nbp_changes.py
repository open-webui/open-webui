#!/usr/bin/env python3
"""
Test script to validate NBP API changes from Table C to Table A
"""

def test_nbp_api_changes():
    """Test the key changes made to NBP client"""
    
    # Read the modified file
    with open('open_webui/utils/nbp_client.py', 'r') as f:
        content = f.read()
    
    # Test 1: API endpoint changed to Table A
    assert '/exchangerates/tables/a/' in content, "API endpoint should use Table A"
    assert '/exchangerates/tables/c/' not in content, "API endpoint should not use Table C"
    
    # Test 2: Rate field changed to 'mid'
    assert "rate.get('mid')" in content, "Should use 'mid' field from Table A"
    assert "rate.get('ask')" not in content, "Should not use 'ask' field from Table C"
    
    # Test 3: Documentation updated
    assert "Table A (average rates)" in content, "Documentation should mention Table A"
    assert "Table C (buy/sell rates)" not in content, "Documentation should not mention Table C"
    
    # Test 4: Bid rate removed
    assert "'bid': rate.get('bid')" not in content, "Bid rate should be removed as it doesn't exist in Table A"
    
    # Test 5: Example rate updated
    assert "3.6446" in content, "Example should show Table A rate"
    
    # Test 6: Table number example updated
    assert "012/A/NBP/2024" in content, "Table number example should be Table A"
    
    print("✅ All NBP API changes validated successfully!")
    print("📋 Changes made:")
    print("  - API endpoint: /exchangerates/tables/c/ → /exchangerates/tables/a/")
    print("  - Rate field: rate.get('ask') → rate.get('mid')")
    print("  - Documentation: Table C → Table A")
    print("  - Example rate: ~4.08 → 3.6446")
    print("  - Removed bid rate (not available in Table A)")
    print("  - Updated table number examples")

if __name__ == "__main__":
    test_nbp_api_changes()
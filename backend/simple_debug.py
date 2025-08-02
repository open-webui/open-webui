#!/usr/bin/env python3
"""Simple debug script to test data extraction"""

def debug_data_extraction():
    """Debug the data extraction logic"""
    
    # Your test data
    test_record = {
        "model": "gpt-4",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.0075,
        "external_user": "test@example.com",
        "request_id": "test-write-001",
        "client_org_id": "test-client-dev"
    }
    
    print("=== DEBUGGING DATA EXTRACTION ===")
    print(f"Test data: {test_record}")
    print()
    
    print("=== CURRENT (BROKEN) EXTRACTION ===")
    # This is what the current code does
    input_tokens_current = test_record.get("tokens_used", 0)  # Wrong key!
    output_tokens_current = 0  # Hardcoded!
    total_tokens_current = test_record.get("tokens_used", 0)  # Wrong key!
    cost_usd_current = float(test_record.get("cost", 0.0))    # Wrong key!
    latency_ms_current = test_record.get("latency_ms", 0)
    
    print(f"input_tokens: webhook_data.get('tokens_used', 0) = {input_tokens_current}")
    print(f"output_tokens: 0 (HARDCODED!) = {output_tokens_current}")
    print(f"total_tokens: webhook_data.get('tokens_used', 0) = {total_tokens_current}")
    print(f"cost_usd: webhook_data.get('cost', 0.0) = {cost_usd_current}")
    print(f"latency_ms: webhook_data.get('latency_ms', 0) = {latency_ms_current}")
    print()
    
    print("=== CORRECT (FIXED) EXTRACTION ===")
    # This is what it should be
    input_tokens_correct = test_record.get("input_tokens", 0)
    output_tokens_correct = test_record.get("output_tokens", 0)
    total_tokens_correct = test_record.get("total_tokens", 0)
    cost_usd_correct = float(test_record.get("cost_usd", 0.0))
    latency_ms_correct = test_record.get("latency_ms", 0)
    
    print(f"input_tokens: webhook_data.get('input_tokens', 0) = {input_tokens_correct}")
    print(f"output_tokens: webhook_data.get('output_tokens', 0) = {output_tokens_correct}")
    print(f"total_tokens: webhook_data.get('total_tokens', 0) = {total_tokens_correct}")
    print(f"cost_usd: webhook_data.get('cost_usd', 0.0) = {cost_usd_correct}")
    print(f"latency_ms: webhook_data.get('latency_ms', 0) = {latency_ms_correct}")
    print()
    
    print("=== AVAILABLE KEYS ===")
    print(f"Keys in test data: {list(test_record.keys())}")
    print()
    
    print("=== PROBLEM IDENTIFICATION ===")
    print("Issues found:")
    print("1. input_tokens field uses 'tokens_used' key but test data has 'input_tokens'")
    print("2. output_tokens is hardcoded to 0")
    print("3. total_tokens field uses 'tokens_used' key but test data has 'total_tokens'") 
    print("4. cost_usd field uses 'cost' key but test data has 'cost_usd'")
    print()
    
    print("=== SOLUTION ===")
    print("The field mappings need to be updated to match the actual webhook data structure.")

if __name__ == "__main__":
    debug_data_extraction()
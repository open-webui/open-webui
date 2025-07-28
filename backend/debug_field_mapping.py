#!/usr/bin/env python3
"""
Debug field mapping - check if system is using correct OpenRouter fields
Compare what we expect vs what the system captured
"""

import sys
import sqlite3

def debug_field_mapping():
    """Debug which fields the system is actually using"""
    
    print("🔍 Debugging OpenRouter Field Mapping")
    print("=" * 50)
    
    # Expected from raw OpenRouter data
    expected_data = {
        "gen-1753737632-sj6yK57NKZVB9SWNfgOZ": {
            "tokens_prompt": 305, "tokens_completion": 17, "total_normalized": 322,
            "native_tokens_prompt": 333, "native_tokens_completion": 21, "total_native": 354,
            "usage": 0.001314
        },
        "gen-1753737629-x1JYGEvD2pV2I8dSup5c": {
            "tokens_prompt": 413, "tokens_completion": 14, "total_normalized": 427,
            "native_tokens_prompt": 472, "native_tokens_completion": 19, "total_native": 491,
            "usage": 0.001701
        },
        "gen-1753737626-F6Hp1h3cFioIjCCA6PNP": {
            "tokens_prompt": 343, "tokens_completion": 75, "total_normalized": 418,
            "native_tokens_prompt": 378, "native_tokens_completion": 90, "total_native": 468,
            "usage": 0.002484
        }
    }
    
    # Connect to database
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, total_tokens, total_cost
            FROM processed_generations 
            WHERE generation_date = '2025-07-28'
            ORDER BY processed_at ASC
        ''')
        
        captured_data = cursor.fetchall()
        
        print("📊 Field Mapping Analysis:")
        print("-" * 30)
        
        for row in captured_data:
            gen_id, captured_tokens, captured_cost = row
            
            if gen_id in expected_data:
                expected = expected_data[gen_id]
                
                print(f"\n🔎 {gen_id[:20]}...")
                print(f"  📊 OpenRouter Raw Data:")
                print(f"     tokens_prompt: {expected['tokens_prompt']}")
                print(f"     tokens_completion: {expected['tokens_completion']}")
                print(f"     total_normalized: {expected['total_normalized']}")
                print(f"     native_tokens_prompt: {expected['native_tokens_prompt']}")
                print(f"     native_tokens_completion: {expected['native_tokens_completion']}")
                print(f"     total_native: {expected['total_native']}")
                print(f"     usage: ${expected['usage']:.6f}")
                
                print(f"  🗄️  Database Captured:")
                print(f"     total_tokens: {captured_tokens}")
                print(f"     total_cost: ${captured_cost:.6f}")
                
                print(f"  🔍 Field Mapping Detection:")
                if captured_tokens == expected['total_normalized']:
                    print(f"     ✅ Using tokens_prompt + tokens_completion (normalized)")
                elif captured_tokens == expected['total_native']:
                    print(f"     ⚠️  Using native_tokens_prompt + native_tokens_completion (native)")
                else:
                    print(f"     ❌ Unknown token calculation method")
                
                if abs(captured_cost - expected['usage']) < 0.000001:
                    print(f"     ✅ Using 'usage' field for cost")
                else:
                    print(f"     ❌ Cost doesn't match 'usage' field")
        
        print(f"\n🎯 Conclusion:")
        print("Based on the analysis above, the system appears to be using:")
        
        # Check the pattern from captured data
        sample_gen = captured_data[0]
        sample_id = sample_gen[0]
        sample_tokens = sample_gen[1]
        
        if sample_id in expected_data:
            expected = expected_data[sample_id]
            if sample_tokens == expected['total_native']:
                print("  📊 NATIVE token fields (native_tokens_prompt + native_tokens_completion)")
                print("  💡 This explains the discrepancy - we should use 'tokens_prompt' + 'tokens_completion'")
                return "native"
            elif sample_tokens == expected['total_normalized']:
                print("  📊 NORMALIZED token fields (tokens_prompt + tokens_completion)")
                print("  ✅ This is correct as per OpenRouter documentation")
                return "normalized"
            else:
                print("  ❓ UNKNOWN field mapping")
                return "unknown"
        
        return "unknown"
        
    except Exception as e:
        print(f"❌ Error debugging field mapping: {e}")
        return "error"
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 OpenRouter Field Mapping Debug")
    print("Investigating which fields our system is actually using")
    print()
    
    result = debug_field_mapping()
    
    print(f"\n🔧 Recommended Action:")
    if result == "native":
        print("❌ System is using native_tokens_* fields instead of tokens_* fields")
        print("🛠️  Need to update field mapping in webhook_service.py and cost_calculator.py")
    elif result == "normalized":
        print("✅ System is correctly using normalized tokens_* fields")
        print("🎯 Field mapping is working as intended")
    else:
        print("❓ Unable to determine field mapping - manual investigation needed")
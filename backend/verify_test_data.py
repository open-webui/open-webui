#!/usr/bin/env python3
"""
Verify test data was captured correctly with OpenRouter field mapping fix
Compare expected vs actual data from the 4 test queries
"""

import sys
import sqlite3
from datetime import datetime

def verify_test_data():
    """Verify the 4 test queries were captured correctly"""
    
    print("🔍 Step 3: Verifying Test Data in Database")
    print("=" * 60)
    
    # Expected data from the 4 test queries
    expected_generations = [
        {"id": "gen-1753737632-sj6yK57NKZVB9SWNfgOZ", "tokens": 305 + 17, "cost": 0.001314},
        {"id": "gen-1753737629-x1JYGEvD2pV2I8dSup5c", "tokens": 413 + 14, "cost": 0.001701}, 
        {"id": "gen-1753737626-F6Hp1h3cFioIjCCA6PNP", "tokens": 343 + 75, "cost": 0.002484},
        {"id": "gen-1753737621-vee4KwY88XdvWdgQJCDA", "tokens": 19 + 120, "cost": 0.001992}
    ]
    
    expected_total_tokens = sum(gen["tokens"] for gen in expected_generations)
    expected_total_cost = sum(gen["cost"] for gen in expected_generations)
    expected_markup_cost = expected_total_cost * 1.3
    
    print("📊 Expected Results from 4 Test Queries:")
    for i, gen in enumerate(expected_generations, 1):
        print(f"  Query {i}: {gen['tokens']} tokens, ${gen['cost']:.6f} cost")
    print(f"  💯 TOTAL: {expected_total_tokens} tokens, ${expected_total_cost:.6f} raw cost")
    print(f"  📈 MARKUP: ${expected_markup_cost:.6f} (1.3x multiplier)")
    print()
    
    # Connect to database
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cursor = conn.cursor()
    
    try:
        # Check processed generations
        print("🔎 Checking Processed Generations:")
        print("-" * 40)
        
        cursor.execute('''
            SELECT id, total_tokens, total_cost, processed_at
            FROM processed_generations 
            WHERE generation_date = '2025-07-28'
            ORDER BY processed_at ASC
        ''')
        
        processed_gens = cursor.fetchall()
        print(f"📦 Found {len(processed_gens)} processed generations")
        
        found_generations = []
        for row in processed_gens:
            gen_id, tokens, cost, processed_at = row
            print(f"  ✅ {gen_id}")
            print(f"     Tokens: {tokens}, Cost: ${cost:.6f}")
            print(f"     Processed: {datetime.fromtimestamp(processed_at)}")
            found_generations.append({"id": gen_id, "tokens": tokens, "cost": cost})
            print()
        
        # Check if we found all expected generations
        print("🎯 Generation ID Matching:")
        all_found = True
        for expected in expected_generations:
            found = any(gen["id"] == expected["id"] for gen in found_generations)
            status = "✅ Found" if found else "❌ Missing"
            print(f"  {status}: {expected['id'][:20]}...")
            if not found:
                all_found = False
        
        print()
        
        # Check daily usage aggregation
        print("📈 Checking Daily Usage Aggregation:")
        print("-" * 40)
        
        cursor.execute('''
            SELECT usage_date, total_tokens, raw_cost, markup_cost
            FROM client_daily_usage 
            WHERE client_org_id = 'dev_mai_client_d460a478'
            AND usage_date = '2025-07-28'
        ''')
        
        daily_usage = cursor.fetchall()
        
        if daily_usage:
            date, actual_tokens, actual_raw_cost, actual_markup_cost = daily_usage[0]
            print(f"📅 Date: {date}")
            print(f"🔢 Actual Tokens: {actual_tokens}")
            print(f"💰 Actual Raw Cost: ${actual_raw_cost:.6f}")
            print(f"📈 Actual Markup Cost: ${actual_markup_cost:.6f}")
            print()
            
            # Compare with expected values
            print("⚖️  Expected vs Actual Comparison:")
            token_match = actual_tokens == expected_total_tokens
            raw_cost_match = abs(actual_raw_cost - expected_total_cost) < 0.000001
            markup_cost_match = abs(actual_markup_cost - expected_markup_cost) < 0.000001
            
            token_status = "✅ MATCH" if token_match else "❌ MISMATCH"
            raw_cost_status = "✅ MATCH" if raw_cost_match else "❌ MISMATCH"
            markup_cost_status = "✅ MATCH" if markup_cost_match else "❌ MISMATCH"
            
            print(f"  {token_status} Tokens: {actual_tokens} vs {expected_total_tokens}")
            print(f"  {raw_cost_status} Raw Cost: ${actual_raw_cost:.6f} vs ${expected_total_cost:.6f}")
            print(f"  {markup_cost_status} Markup Cost: ${actual_markup_cost:.6f} vs ${expected_markup_cost:.6f}")
            
            # Overall assessment
            all_match = token_match and raw_cost_match and markup_cost_match
            
            print()
            if all_match and all_found:
                print("🎉 SUCCESS: All data captured correctly!")
                print("✅ OpenRouter field mapping fix is working perfectly")
                return True
            else:
                print("❌ ISSUES DETECTED:")
                if not all_found:
                    print("  - Some generation IDs missing from database")
                if not all_match:
                    print("  - Aggregation calculations don't match expected values")
                return False
                
        else:
            print("❌ No daily usage data found for 2025-07-28")
            print("  This indicates the aggregation process may not have run")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying data: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 OpenRouter Field Mapping Fix - Test Verification")
    print("Checking if the 4 test queries were captured correctly")
    print()
    
    success = verify_test_data()
    
    print("\n" + "="*60)
    if success:
        print("🎯 TEST PASSED: Field mapping fix is working correctly!")
        print("👉 Ready for Step 4: UI verification")
    else:
        print("⚠️  TEST ISSUES: Some data discrepancies detected")
        print("🔧 Investigation needed")
#!/usr/bin/env python3
"""
Test script to verify the model usage functionality
"""

import sys
import os
sys.path.append('backend')

from datetime import date
from open_webui.models.organization_usage import ClientUsageDB

def test_model_usage():
    print("=== Testing Model Usage Functionality ===")
    print()
    
    # Test with the first active client org
    client_org_id = "client_default_organization_1753362006"
    
    print(f"Testing with client_org_id: {client_org_id}")
    print()
    
    try:
        # Test the get_usage_by_model method
        usage_data = ClientUsageDB.get_usage_by_model(client_org_id)
        
        print(f"✅ Method executed successfully")
        print(f"📊 Number of models returned: {len(usage_data)}")
        print()
        
        if usage_data:
            print("🔍 Model Usage Data:")
            print("-" * 80)
            for i, model in enumerate(usage_data, 1):
                cost = model.get('markup_cost', 0.0)
                cost_str = f"${cost:.6f}" if cost > 0 else "$0.00"
                print(f"{i:2d}. {model['model_name']:<40} | {model['provider']:<10} | {cost_str}")
            print("-" * 80)
            
            # Count models with usage vs without
            with_usage = sum(1 for m in usage_data if m.get('markup_cost', 0) > 0)
            without_usage = len(usage_data) - with_usage
            
            print()
            print(f"📈 Models with usage: {with_usage}")
            print(f"📉 Models without usage: {without_usage}")
            print(f"📋 Total models: {len(usage_data)}")
            
            if len(usage_data) == 12:
                print("✅ SUCCESS: All 12 models are displayed!")
            else:
                print(f"❌ ISSUE: Expected 12 models, got {len(usage_data)}")
        else:
            print("❌ No data returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_model_usage()
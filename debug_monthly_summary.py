#!/usr/bin/env python3
"""
Debug script to test the monthly summary API endpoint
"""

import sys
import os
import asyncio
import json
from datetime import date

# Add the backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from open_webui.config import ORGANIZATION_NAME
from open_webui.usage_tracking.services.usage_service import UsageService

async def test_monthly_summary():
    """Test the monthly summary endpoint"""
    print("🔍 Testing Monthly Summary API...")
    print(f"Organization: {ORGANIZATION_NAME}")
    print(f"Current date: {date.today()}")
    print("-" * 50)
    
    usage_service = UsageService()
    
    try:
        result = await usage_service.get_organization_usage_summary()
        
        print("✅ API Response:")
        print(json.dumps(result, indent=2))
        print("\n" + "="*60)
        
        # Check specific fields
        if result.get('success'):
            stats = result.get('stats', {})
            monthly_summary = stats.get('monthly_summary', {})
            
            print("📊 Monthly Summary Details:")
            print(f"- Top Models: {monthly_summary.get('top_models', [])}")
            print(f"- Active Users: {monthly_summary.get('total_unique_users', 0)}")
            print(f"- Stats available: {bool(stats)}")
            print(f"- Client ID: {result.get('client_id', 'N/A')}")
            
            # Check for empty data
            if not monthly_summary.get('top_models'):
                print("\n⚠️  ISSUE: top_models is empty")
            if monthly_summary.get('total_unique_users', 0) == 0:
                print("⚠️  ISSUE: total_unique_users is 0")
                
        else:
            print(f"❌ API Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_monthly_summary())
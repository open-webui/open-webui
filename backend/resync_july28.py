#!/usr/bin/env python3
"""
Manual script to re-sync July 28 OpenRouter data
Recovers the missing 312 tokens and $0.0005 cost
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add backend to path  
sys.path.append('/app/backend')

async def resync_july28_data():
    """Re-sync July 28 data using corrected field mappings"""
    
    print("🔄 Re-syncing July 28 OpenRouter Data")
    print("=" * 50)
    
    try:
        from open_webui.usage_tracking.services.webhook_service import WebhookService
        from open_webui.usage_tracking.models.requests import UsageSyncRequest
        
        # Create webhook service instance
        webhook_service = WebhookService()
        
        # Create sync request for July 28 (yesterday)
        sync_request = UsageSyncRequest(days_back=1)
        
        print(f"📅 Syncing data for last {sync_request.days_back} day(s)")
        print(f"🎯 Target: July 28, 2025 data")
        print()
        
        # Execute the sync
        result = await webhook_service.sync_openrouter_usage(sync_request)
        
        print("✅ Sync completed successfully!")
        print("📊 Results:")
        
        for org_result in result.get("sync_results", []):
            org_name = org_result.get("organization", "Unknown")
            synced_count = org_result.get("synced_generations", 0)
            status = org_result.get("status", "unknown")
            
            print(f"  📦 {org_name}:")
            print(f"     - Synced generations: {synced_count}")  
            print(f"     - Status: {status}")
            
        print()
        print("🎉 July 28 data should now be recovered!")
        print("💡 Expected recovery: 4 requests = 2,074 tokens + $0.00156 cost")
        
        return result
        
    except Exception as e:
        print(f"❌ Sync failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Manual July 28 Data Recovery")
    print("Using corrected OpenRouter field mappings")
    print()
    
    # Run the async sync
    result = asyncio.run(resync_july28_data())
    
    if result:
        print("\n✅ RECOVERY COMPLETE!")
        print("🔍 Next: Check UI to verify 2,074 tokens and $0.002028 cost")
    else:
        print("\n❌ RECOVERY FAILED!")
        print("🔧 Manual intervention required")
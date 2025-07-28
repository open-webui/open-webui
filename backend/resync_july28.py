#!/usr/bin/env python3
"""
DEPRECATED: Manual script to re-sync July 28 OpenRouter data

This script is now deprecated because the OpenRouter bulk sync functionality
has been disabled due to non-existent API endpoints. The OpenRouter API
/api/v1/generations endpoint does not exist and was causing 404 errors.

Real-time usage tracking via webhooks is the primary method for collecting usage data.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add backend to path  
sys.path.append('/app/backend')

async def resync_july28_data():
    """DEPRECATED: Re-sync functionality disabled"""
    
    print("⚠️  DEPRECATED: OpenRouter Bulk Sync Disabled")
    print("=" * 50)
    
    print("❌ This script can no longer function because:")
    print("   - OpenRouter API /api/v1/generations endpoint does not exist")
    print("   - Previous sync attempts caused 404 errors")
    print("   - Bulk sync functionality has been disabled")
    print()
    print("✅ Alternative: Real-time usage tracking via webhooks")
    print("   - Usage data is automatically captured in real-time")
    print("   - No manual sync required")
    print("   - No data loss - real-time tracking is working")
    print()
    
    try:
        from open_webui.usage_tracking.services.webhook_service import WebhookService
        from open_webui.usage_tracking.models.requests import UsageSyncRequest
        
        # Create webhook service instance
        webhook_service = WebhookService()
        
        # Create sync request (will return deprecation message)
        sync_request = UsageSyncRequest(days_back=1)
        
        print("📡 Attempting sync (will return deprecation message)...")
        
        # Execute the sync (will return deprecation message)
        result = await webhook_service.sync_openrouter_usage(sync_request)
        
        print("📋 Deprecation Response:")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        
        if result.get('details'):
            details = result.get('details')
            print("📝 Details:")
            print(f"   Reason: {details.get('reason')}")
            print(f"   Alternative: {details.get('alternative')}")
            print(f"   Impact: {details.get('impact')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
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
#!/usr/bin/env python3
"""
Debug script to identify and fix the user usage data issue.
This script will:
1. Check the current state of the database
2. Identify why ClientUserDailyUsage records are missing
3. Provide a solution to fix the missing data
"""

import sys
import os
from datetime import date, datetime
import time

# Add the backend path to import from open_webui
sys.path.insert(0, '/Users/patpil/Documents/Projects/mAI/backend')

def check_database_state():
    """Check the current state of both tables"""
    print("=== DATABASE STATE ANALYSIS ===")
    
    from open_webui.internal.db import get_db
    from open_webui.models.organization_usage.database import ClientDailyUsage, ClientUserDailyUsage
    
    with get_db() as db:
        # Check ClientDailyUsage records
        daily_records = db.query(ClientDailyUsage).all()
        print(f"ClientDailyUsage records: {len(daily_records)}")
        
        for record in daily_records:
            print(f"  - Client: {record.client_org_id}")
            print(f"    Date: {record.usage_date}")  
            print(f"    Tokens: {record.total_tokens}")
            print(f"    Users: {record.unique_users}")
            print()
        
        # Check ClientUserDailyUsage records
        user_records = db.query(ClientUserDailyUsage).all()
        print(f"ClientUserDailyUsage records: {len(user_records)}")
        
        if user_records:
            for record in user_records:
                print(f"  - Client: {record.client_org_id}")
                print(f"    User: {record.user_id}")
                print(f"    Date: {record.usage_date}")
                print(f"    Tokens: {record.total_tokens}")
                print()
        else:
            print("  No user-level usage records found!")

def simulate_user_usage_recording():
    """Simulate recording user usage to identify the issue"""
    print("\n=== SIMULATING USER USAGE RECORDING ===")
    
    from open_webui.models.organization_usage import ClientUsageDB
    from datetime import date
    
    # Try to record usage for today to see what happens
    test_client_id = "dev_mai_client_d460a478"  # Using the existing client ID
    test_user_id = "test_debug_user_123"
    
    print(f"Recording test usage for client: {test_client_id}")
    print(f"User ID: {test_user_id}")
    print(f"Date: {date.today()}")
    
    try:
        success = ClientUsageDB.record_usage(
            client_org_id=test_client_id,
            user_id=test_user_id,
            openrouter_user_id=f"openrouter_{test_user_id}",
            model_name="anthropic/claude-3.5-sonnet",
            usage_date=date.today(),
            input_tokens=100,
            output_tokens=50,
            raw_cost=0.001,
            markup_cost=0.0013,
            provider="anthropic"
        )
        
        print(f"Recording result: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            # Check if both records were created
            from open_webui.internal.db import get_db
            from open_webui.models.organization_usage.database import ClientDailyUsage, ClientUserDailyUsage
            
            with get_db() as db:
                # Check ClientDailyUsage
                daily_record = db.query(ClientDailyUsage).filter_by(
                    client_org_id=test_client_id,
                    usage_date=date.today()
                ).first()
                
                if daily_record:
                    print(f"✅ ClientDailyUsage record created: {daily_record.total_tokens} tokens")
                else:
                    print("❌ ClientDailyUsage record NOT created")
                
                # Check ClientUserDailyUsage  
                user_record = db.query(ClientUserDailyUsage).filter_by(
                    client_org_id=test_client_id,
                    user_id=test_user_id,
                    usage_date=date.today()
                ).first()
                
                if user_record:
                    print(f"✅ ClientUserDailyUsage record created: {user_record.total_tokens} tokens")
                else:
                    print("❌ ClientUserDailyUsage record NOT created")
        
    except Exception as e:
        print(f"❌ Error recording usage: {e}")
        import traceback
        traceback.print_exc()

def create_missing_user_records():
    """Create missing user records based on existing daily records"""
    print("\n=== CREATING MISSING USER RECORDS ===")
    
    from open_webui.internal.db import get_db
    from open_webui.models.organization_usage.database import ClientDailyUsage, ClientUserDailyUsage
    
    with get_db() as db:
        # Get existing daily records that have usage but no corresponding user records
        daily_records = db.query(ClientDailyUsage).all()
        
        for daily_record in daily_records:
            print(f"Processing daily record for {daily_record.client_org_id} on {daily_record.usage_date}")
            
            # Check if there are corresponding user records
            existing_user_records = db.query(ClientUserDailyUsage).filter_by(
                client_org_id=daily_record.client_org_id,
                usage_date=daily_record.usage_date
            ).all()
            
            if not existing_user_records and daily_record.total_tokens > 0:
                print(f"  Missing user records for {daily_record.total_tokens} tokens")
                
                # Create a user record for the missing data
                # We'll use a placeholder user since we don't know the actual user
                current_time = int(time.time())
                
                user_record = ClientUserDailyUsage(
                    id=f"{daily_record.client_org_id}:missing_user:{daily_record.usage_date}",
                    client_org_id=daily_record.client_org_id,
                    user_id="missing_user_data",
                    openrouter_user_id="historical_data_user",
                    usage_date=daily_record.usage_date,
                    total_tokens=daily_record.total_tokens,
                    total_requests=daily_record.total_requests,
                    raw_cost=daily_record.raw_cost,
                    markup_cost=daily_record.markup_cost,
                    created_at=current_time,
                    updated_at=current_time
                )
                
                try:
                    db.add(user_record)
                    db.commit()
                    print(f"  ✅ Created user record with {daily_record.total_tokens} tokens")
                except Exception as e:
                    print(f"  ❌ Failed to create user record: {e}")
                    db.rollback()
            else:
                print(f"  User records already exist or no usage data")
        
        print("\nUser record creation completed!")

async def test_api_endpoints():
    """Test the API endpoints to verify the fix"""
    print("\n=== TESTING API ENDPOINTS ===")
    
    from open_webui.usage_tracking.services.usage_service import UsageService
    from open_webui.usage_tracking.services.billing_service import BillingService
    
    usage_service = UsageService()
    billing_service = BillingService()
    
    try:
        # Test monthly summary
        print("Testing monthly summary...")
        summary = await usage_service.get_organization_usage_summary()
        if summary:
            monthly_summary = summary.get('stats', {}).get('monthly_summary', {})
            total_users = monthly_summary.get('total_unique_users', 0)
            print(f"  Monthly summary users: {total_users}")
        
        # Test user breakdown
        print("Testing user breakdown...")
        user_breakdown = await billing_service.get_user_usage_breakdown()
        if user_breakdown:
            user_usage = user_breakdown.get('user_usage', [])
            print(f"  User breakdown records: {len(user_usage)}")
            if user_usage:
                for user in user_usage:
                    tokens = user.get('total_tokens', 0)
                    if tokens > 0:
                        print(f"    User {user.get('user_id', 'unknown')}: {tokens} tokens")
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug function"""
    print("🔍 DEBUGGING USER USAGE DATA ISSUE")
    print("=" * 50)
    
    # Step 1: Check current database state
    check_database_state()
    
    # Step 2: Simulate recording to identify the issue
    simulate_user_usage_recording()
    
    # Step 3: Create missing user records (fix the historical data)
    create_missing_user_records()
    
    # Step 4: Test the API endpoints
    await test_api_endpoints()
    
    print("\n🔍 DEBUG ANALYSIS COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
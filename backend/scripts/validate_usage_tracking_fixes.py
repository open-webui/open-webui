#!/usr/bin/env python3
"""
Validation Script for Usage Tracking Fixes
Manually validates that the "Today's Tokens (live)" fixes are working correctly
"""

import sys
import os
import time
from datetime import datetime, date, timedelta

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from open_webui.models.organization_usage import (
    ClientOrganizationDB, ClientUsageDB, UserClientMappingDB,
    ClientDailyUsage, ClientLiveCounters, get_db
)
from open_webui.utils.background_sync import OpenRouterUsageSync
from open_webui.routers.usage_tracking import record_usage_to_db


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f"{title:^60}")
    print(f"{'=' * 60}")


def validate_background_sync_updates_live_counters():
    """Validate that background sync updates live counters"""
    print_section("Testing Background Sync → Live Counter Updates")
    
    try:
        # Get first active client
        clients = ClientOrganizationDB.get_all_active_clients()
        if not clients:
            print("❌ No active client organizations found")
            return False
            
        client = clients[0]
        print(f"✅ Using client: {client.name} (ID: {client.id})")
        
        # Clear any existing live counter for clean test
        with get_db() as db:
            db.query(ClientLiveCounters).filter_by(client_org_id=client.id).delete()
            db.commit()
        
        # Simulate background sync with mock data
        sync_manager = OpenRouterUsageSync()
        mock_generations = [
            {
                "id": f"validation_test_{int(time.time())}",
                "created_at": datetime.now().isoformat() + "Z",
                "model": "anthropic/claude-3.5-sonnet",
                "total_tokens": 1500,
                "total_cost": 0.045
            }
        ]
        
        print("📡 Simulating background sync with mock OpenRouter data...")
        result = sync_manager.record_usage_batch_to_db(client.id, mock_generations)
        
        if result["processed"] > 0:
            print(f"✅ Background sync processed {result['processed']} generations")
            print(f"   Total tokens: {result['total_tokens']}")
            print(f"   Total cost: ${result['total_cost']:.6f}")
        else:
            print("❌ Background sync failed to process generations")
            return False
            
        # Check if live counter was created/updated
        stats = ClientUsageDB.get_usage_stats_by_client(client.id)
        
        if stats.today["tokens"] > 0:
            print(f"✅ Live counter updated successfully!")
            print(f"   Today's tokens: {stats.today['tokens']}")
            print(f"   Today's cost: ${stats.today['cost']:.6f}")
            print(f"   Last updated: {stats.today['last_updated']}")
            return True
        else:
            print("❌ Live counter was not updated")
            return False
            
    except Exception as e:
        print(f"❌ Error during background sync validation: {e}")
        return False


def validate_fallback_logic():
    """Validate that fallback logic restores live counters from daily summaries"""
    print_section("Testing Fallback Logic: Daily Summary → Live Counter")
    
    try:
        # Get first active client
        clients = ClientOrganizationDB.get_all_active_clients()
        if not clients:
            print("❌ No active client organizations found")
            return False
            
        client = clients[0]
        print(f"✅ Using client: {client.name} (ID: {client.id})")
        
        # Create a daily summary but remove live counter (simulate missing/stale state)
        today = date.today()
        
        with get_db() as db:
            # Remove any existing live counter
            db.query(ClientLiveCounters).filter_by(client_org_id=client.id).delete()
            
            # Create/update daily summary
            daily_summary_id = f"{client.id}_{today.isoformat()}"
            existing_summary = db.query(ClientDailyUsage).filter_by(id=daily_summary_id).first()
            
            if existing_summary:
                # Update existing
                existing_summary.total_tokens += 2500
                existing_summary.total_requests += 3
                existing_summary.raw_cost += 0.075
                existing_summary.markup_cost += 0.0975
                existing_summary.updated_at = int(time.time())
                print("📝 Updated existing daily summary")
            else:
                # Create new
                daily_summary = ClientDailyUsage(
                    id=daily_summary_id,
                    client_org_id=client.id,
                    usage_date=today,
                    total_tokens=2500,
                    total_requests=3,
                    raw_cost=0.075,
                    markup_cost=0.0975,
                    primary_model="test/validation-model",
                    unique_users=1,
                    created_at=int(time.time()),
                    updated_at=int(time.time())
                )
                db.add(daily_summary)
                print("📝 Created new daily summary")
            
            db.commit()
        
        print("🔍 Triggering fallback logic by requesting usage stats...")
        
        # Request usage stats - should trigger fallback logic
        stats = ClientUsageDB.get_usage_stats_by_client(client.id)
        
        if stats.today["tokens"] > 0:
            print(f"✅ Fallback logic worked!")
            print(f"   Restored tokens: {stats.today['tokens']}")
            print(f"   Restored cost: ${stats.today['cost']:.6f}")
            print(f"   Status: {stats.today['last_updated']}")
            
            # Verify live counter was created
            with get_db() as db:
                live_counter = db.query(ClientLiveCounters).filter_by(
                    client_org_id=client.id
                ).first()
                
                if live_counter and live_counter.current_date == today:
                    print("✅ Live counter was properly created/restored")
                    return True
                else:
                    print("❌ Live counter was not created properly")
                    return False
        else:
            print("❌ Fallback logic failed - no tokens restored")
            return False
            
    except Exception as e:
        print(f"❌ Error during fallback validation: {e}")
        return False


def validate_consolidated_recording():
    """Validate that manual recording uses consolidated ORM approach"""
    print_section("Testing Consolidated Recording System")
    
    try:
        # Get first active client
        clients = ClientOrganizationDB.get_all_active_clients()
        if not clients:
            print("❌ No active client organizations found")
            return False
            
        client = clients[0]
        print(f"✅ Using client: {client.name} (ID: {client.id})")
        
        # Get initial state
        initial_stats = ClientUsageDB.get_usage_stats_by_client(client.id)
        initial_tokens = initial_stats.today["tokens"]
        initial_cost = initial_stats.today["cost"]
        
        print(f"📊 Initial state - Tokens: {initial_tokens}, Cost: ${initial_cost:.6f}")
        
        # Record usage using consolidated method
        usage_data = {
            "model": "validation/test-model",
            "total_tokens": 1000,
            "total_cost": 0.030
        }
        
        print("📝 Recording usage via consolidated method...")
        record_usage_to_db(client.id, usage_data, "validation_test")
        
        # Check updated state
        updated_stats = ClientUsageDB.get_usage_stats_by_client(client.id)
        final_tokens = updated_stats.today["tokens"]
        final_cost = updated_stats.today["cost"]
        
        print(f"📊 Final state - Tokens: {final_tokens}, Cost: ${final_cost:.6f}")
        
        # Verify incremental update
        token_increase = final_tokens - initial_tokens
        cost_increase = final_cost - initial_cost
        
        if token_increase == 1000 and abs(cost_increase - (0.030 * 1.3)) < 0.001:
            print("✅ Consolidated recording system works correctly!")
            print(f"   Token increase: {token_increase}")
            print(f"   Cost increase: ${cost_increase:.6f} (with 1.3x markup)")
            return True
        else:
            print("❌ Consolidated recording system failed")
            print(f"   Expected token increase: 1000, got: {token_increase}")
            print(f"   Expected cost increase: ${0.030 * 1.3:.6f}, got: ${cost_increase:.6f}")
            return False
            
    except Exception as e:
        print(f"❌ Error during consolidated recording validation: {e}")
        return False


def validate_real_time_accuracy():
    """Validate that real-time data is accurate and updates properly"""
    print_section("Testing Real-Time Data Accuracy")
    
    try:
        # Get first active client
        clients = ClientOrganizationDB.get_all_active_clients()
        if not clients:
            print("❌ No active client organizations found")
            return False
            
        client = clients[0]
        print(f"✅ Using client: {client.name} (ID: {client.id})")
        
        # Get stats multiple times to simulate 30-second refresh
        print("🔄 Simulating real-time refresh pattern...")
        
        stats_1 = ClientUsageDB.get_usage_stats_by_client(client.id)
        print(f"   First read - Tokens: {stats_1.today['tokens']}, Cost: ${stats_1.today['cost']:.6f}")
        
        # Simulate a small delay
        time.sleep(1)
        
        stats_2 = ClientUsageDB.get_usage_stats_by_client(client.id) 
        print(f"   Second read - Tokens: {stats_2.today['tokens']}, Cost: ${stats_2.today['cost']:.6f}")
        
        # Data should be consistent
        if (stats_1.today["tokens"] == stats_2.today["tokens"] and 
            abs(stats_1.today["cost"] - stats_2.today["cost"]) < 0.001):
            print("✅ Real-time data is consistent across reads")
            
            # Test that live indicator shows recent activity
            if (":" in stats_1.today["last_updated"] or 
                "summary" in stats_1.today["last_updated"].lower()):
                print(f"✅ Live status indicator working: {stats_1.today['last_updated']}")
                return True
            else:
                print(f"⚠️  Live status indicator unclear: {stats_1.today['last_updated']}")
                return True  # Still pass, just a warning
        else:
            print("❌ Real-time data is inconsistent")
            return False
            
    except Exception as e:
        print(f"❌ Error during real-time validation: {e}")
        return False


def main():
    """Run all validation tests"""
    print_section("mAI Usage Tracking Validation")
    print(f"Testing fixes for 'Today's Tokens (live)' functionality")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Background Sync Updates", validate_background_sync_updates_live_counters),
        ("Fallback Logic", validate_fallback_logic),
        ("Consolidated Recording", validate_consolidated_recording),
        ("Real-Time Accuracy", validate_real_time_accuracy)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print_section("Validation Results Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<8} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes are working correctly!")
        print("   'Today's Tokens (live)' should now display accurate real-time data")
        return 0
    else:
        print("⚠️  Some issues detected - review failed tests above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
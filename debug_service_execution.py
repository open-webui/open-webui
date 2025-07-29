#!/usr/bin/env python3
"""
Debug script to simulate exact service execution
Identifies where the exception occurs in get_user_usage_breakdown
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set required environment variables
os.environ['DATA_DIR'] = str(Path(__file__).parent / "backend" / "data")
os.environ['ORGANIZATION_NAME'] = 'Test Organization'

async def debug_service_execution():
    """Debug the exact service execution that's failing"""
    print("🔍 DEBUG: Simulating exact service execution...")
    
    try:
        # Step 1: Import all required modules (potential failure point)
        print("🔍 Step 1: Importing modules...")
        
        # These imports mirror the billing_service.py imports
        from open_webui.utils.currency_converter import get_current_usd_pln_rate
        from open_webui.models.users import Users
        from open_webui.utils.user_mapping import get_external_user_id, user_mapping_service
        from open_webui.config import ORGANIZATION_NAME
        print("✅ Step 1: All imports successful")
        
        # Step 2: Get exchange rate (potential failure point)
        print("🔍 Step 2: Getting exchange rate...")
        try:
            usd_pln_rate = await get_current_usd_pln_rate()
            print(f"✅ Step 2: USD/PLN rate: {usd_pln_rate}")
        except Exception as e:
            print(f"❌ Step 2: Exchange rate failed: {e}")
            # Use fallback rate
            usd_pln_rate = 4.0
            print(f"🔍 Step 2: Using fallback rate: {usd_pln_rate}")
        
        # Step 3: Get client organization ID (potential failure point)
        print("🔍 Step 3: Getting client organization ID...")
        from open_webui.usage_tracking.repositories.client_repository import ClientRepository
        client_repo = ClientRepository()
        client_org_id = client_repo.get_environment_client_id()
        print(f"✅ Step 3: Client org ID: {client_org_id}")
        
        if not client_org_id:
            print("❌ Step 3: No client organization found")
            return {
                "success": False,
                "error": "No client organization found",
                "user_usage": []
            }
        
        # Step 4: Get usage data (potential failure point)
        print("🔍 Step 4: Getting usage data...")
        from open_webui.usage_tracking.repositories.usage_repository import UsageRepository
        usage_repo = UsageRepository()
        usage_data = usage_repo.get_usage_by_user(client_org_id)
        print(f"✅ Step 4: Raw usage data: {len(usage_data)} records")
        print(f"✅ Step 4: Sample data: {usage_data[:1] if usage_data else 'No data'}")
        
        # Step 5: Get all users (potential failure point)
        print("🔍 Step 5: Getting all users...")
        try:
            all_users = Users.get_users()
            print(f"✅ Step 5: Found {len(all_users)} users")
            user_dict = {u.id: u for u in all_users}
            print(f"✅ Step 5: User dict keys: {list(user_dict.keys())}")
        except Exception as e:
            print(f"❌ Step 5: Getting users failed: {e}")
            return {
                "success": False,
                "error": f"Failed to get users: {e}",
                "user_usage": []
            }
        
        # Step 6: Enhance usage data with user details (potential failure point)
        print("🔍 Step 6: Enhancing usage data...")
        user_usage_list = []
        for usage in usage_data:
            try:
                user_obj = user_dict.get(usage['user_id'])
                enhanced_usage = {
                    "user_id": usage['user_id'],
                    "user_name": user_obj.name if user_obj else usage['user_id'],
                    "user_email": user_obj.email if user_obj else "unknown@example.com",
                    "external_user_id": usage.get('openrouter_user_id', 'unknown'),
                    "total_tokens": usage['total_tokens'],
                    "total_requests": usage['total_requests'],
                    "markup_cost": usage['markup_cost'],
                    "cost_pln": round(usage['markup_cost'] * usd_pln_rate, 2),
                    "days_active": usage['days_active'],
                    "last_activity": None,
                    "user_mapping_enabled": True
                }
                user_usage_list.append(enhanced_usage)
            except Exception as e:
                print(f"❌ Step 6: Failed to enhance usage for user {usage.get('user_id', 'unknown')}: {e}")
                # Continue with other users
                continue
        
        print(f"✅ Step 6: Enhanced {len(user_usage_list)} user records")
        
        # Step 7: Add users with no usage data (potential failure point)
        print("🔍 Step 7: Adding users with no usage...")
        users_with_usage = {u['user_id'] for u in user_usage_list}
        for user_obj in all_users:
            if user_obj.id not in users_with_usage:
                try:
                    external_user_id = get_external_user_id(user_obj.id, user_obj.name)
                    user_usage_list.append({
                        "user_id": user_obj.id,
                        "user_name": user_obj.name,
                        "user_email": user_obj.email,
                        "external_user_id": external_user_id,
                        "total_tokens": 0,
                        "total_requests": 0,
                        "markup_cost": 0.0,
                        "cost_pln": 0.0,
                        "days_active": 0,
                        "last_activity": None,
                        "user_mapping_enabled": True
                    })
                except Exception as e:
                    print(f"⚠️ Step 7: User mapping failed for {user_obj.id}: {e}")
                    user_usage_list.append({
                        "user_id": user_obj.id,
                        "user_name": user_obj.name,
                        "user_email": user_obj.email,
                        "external_user_id": "mapping_error",
                        "total_tokens": 0,
                        "total_requests": 0,
                        "markup_cost": 0.0,
                        "cost_pln": 0.0,
                        "days_active": 0,
                        "last_activity": None,
                        "user_mapping_enabled": False,
                        "error": str(e)
                    })
        
        print(f"✅ Step 7: Total users in response: {len(user_usage_list)}")
        
        # Step 8: Get user mapping info (potential failure point)
        print("🔍 Step 8: Getting user mapping info...")
        try:
            user_mapping_info = user_mapping_service.get_mapping_info()
            print(f"✅ Step 8: User mapping info obtained")
        except Exception as e:
            print(f"⚠️ Step 8: User mapping info failed: {e}")
            user_mapping_info = None
        
        # Step 9: Build final response
        print("🔍 Step 9: Building final response...")
        response = {
            "success": True,
            "user_usage": user_usage_list,
            "organization_name": ORGANIZATION_NAME or "My Organization",
            "total_users": len(user_usage_list),
            "user_mapping_info": user_mapping_info
        }
        
        print(f"✅ Step 9: Final response built successfully")
        print(f"✅ Response summary: success={response['success']}, users={response['total_users']}")
        
        return response
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "user_usage": [],
            "organization_name": "Error",
            "total_users": 0
        }

if __name__ == "__main__":
    result = asyncio.run(debug_service_execution())
    print(f"\n🎯 FINAL RESULT:")
    print(f"Success: {result['success']}")
    print(f"Users: {result.get('total_users', 0)}")
    if not result['success']:
        print(f"Error: {result.get('error', 'Unknown error')}")
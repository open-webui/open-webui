#!/usr/bin/env python3
"""
Production initialization for mAI usage tracking
Run this after deployment to ensure usage tracking is properly configured
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.webui.internal.db import engine
from apps.webui.models.users import Users
from apps.webui.models.organization_usage import (
    ClientOrganizationDB, UserClientMappingDB, ClientUsageDB
)
from datetime import datetime
import uuid

def init_usage_tracking():
    """Initialize usage tracking for production deployment"""
    print("🚀 Initializing mAI Usage Tracking")
    print("=" * 50)
    
    try:
        # 1. Check if tables exist
        from apps.webui.internal.migration_safety import ensure_usage_tracking_ready
        if not ensure_usage_tracking_ready():
            print("❌ Usage tracking tables not ready. Run migrations first.")
            return False
        
        # 2. Get admin user
        admin_users = Users.get_users_by_role("admin")
        if not admin_users:
            print("❌ No admin users found. Create admin user first.")
            return False
        
        admin = admin_users[0]
        print(f"✅ Found admin user: {admin.name} ({admin.email})")
        
        # 3. Check organization mapping
        mapping = UserClientMappingDB.get_mapping_by_user_id(admin.id)
        if mapping:
            print(f"✅ Admin already mapped to organization: {mapping.client_org_id}")
            
            # Ensure API key is synced from UI
            org = ClientOrganizationDB.get_client_by_id(mapping.client_org_id)
            if org and not org.openrouter_api_key:
                print("⚠️  Organization missing API key. Admin must set it in Settings → Connections")
        else:
            # Get default organization
            orgs = ClientOrganizationDB.get_all_active_clients()
            if orgs:
                org = orgs[0]
                print(f"📦 Mapping admin to organization: {org.name}")
                
                # Create mapping
                UserClientMappingDB.create_mapping({
                    "user_id": admin.id,
                    "client_org_id": org.id,
                    "openrouter_user_id": "",  # Will be auto-learned
                    "is_active": True
                })
                print("✅ Created user-organization mapping")
            else:
                print("❌ No organizations found. This should not happen.")
                return False
        
        # 4. Initialize live counters if needed
        ClientUsageDB.ensure_live_counters_exist(org.id if 'org' in locals() else mapping.client_org_id)
        
        print("\n✅ Usage tracking initialized successfully!")
        print("\n📋 Next Steps:")
        print("1. Admin must set OpenRouter API key in Settings → Connections")
        print("2. The API key will auto-sync to the organization")
        print("3. Usage will be tracked automatically on first API call")
        print("4. Check Admin Settings → Usage tab for statistics")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_usage_tracking()
    sys.exit(0 if success else 1)
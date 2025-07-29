#!/usr/bin/env python3
"""
Debug script to understand why get_models_by_user_id() returns no models
"""

from open_webui.models.models import ModelsTable
from open_webui.internal.db import get_db
from sqlalchemy import text

def main():
    models_table = ModelsTable()
    test_user_id = "test-user-123"
    
    with get_db() as db:
        print("=== DEBUG: Model Access Investigation ===\n")
        
        # 1. Check if user exists and is in organization
        user = db.execute(
            text("SELECT id, name, email FROM user WHERE id = :user_id"),
            {"user_id": test_user_id}
        ).fetchone()
        print(f"1. User: {user}")
        
        org_membership = db.execute(
            text("SELECT organization_id FROM organization_members WHERE user_id = :user_id AND is_active = 1"),
            {"user_id": test_user_id}
        ).fetchone()
        print(f"2. Organization membership: {org_membership}")
        
        # 2. Check organization models
        if org_membership:
            org_id = org_membership[0]
            org_models = db.execute(
                text("SELECT model_id FROM organization_models WHERE organization_id = :org_id AND is_active = 1"),
                {"org_id": org_id}
            ).fetchall()
            print(f"3. Organization models ({len(org_models)}):")
            for (model_id,) in org_models:
                print(f"   - {model_id}")
        
        # 3. Check if models exist in model table
        all_models = db.execute(text("SELECT id, name FROM model")).fetchall()
        print(f"4. Models in database ({len(all_models)}):")
        for model_id, name in all_models:
            print(f"   - {model_id}: {name}")
        
        # 4. Test the get_models function step by step
        print("\n5. Testing get_models_by_user_id() components:")
        
        # Get all models first
        all_models_from_function = models_table.get_models()
        print(f"   get_models() returned: {len(all_models_from_function)} models")
        
        # Get user organizations 
        try:
            user_orgs = db.execute(
                text("SELECT DISTINCT organization_id FROM organization_members WHERE user_id = :user_id AND is_active = 1"),
                {"user_id": test_user_id}
            ).fetchall()
            print(f"   User organizations: {[org[0] for org in user_orgs]}")
            
            if user_orgs:
                org_id = user_orgs[0][0]
                org_models_result = db.execute(
                    text("SELECT DISTINCT model_id FROM organization_models WHERE organization_id = :org_id AND is_active = 1"),
                    {"org_id": org_id}
                ).fetchall()
                user_org_models = {model[0] for model in org_models_result}
                print(f"   Organization model IDs: {user_org_models}")
                
                # Check which models match
                matching_models = [
                    model for model in all_models_from_function
                    if model.id in user_org_models
                ]
                print(f"   Matching models: {len(matching_models)}")
                for model in matching_models:
                    print(f"     - {model.id}")
                    
        except Exception as e:
            print(f"   Error in organization lookup: {e}")
        
        # 5. Call the actual function
        accessible_models = models_table.get_models_by_user_id(test_user_id)
        print(f"\n6. Final result from get_models_by_user_id(): {len(accessible_models)} models")

if __name__ == "__main__":
    main()
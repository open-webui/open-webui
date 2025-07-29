#!/usr/bin/env python3
"""
Test script to verify Pat and Olaf can see the 12 mAI business models
"""

from open_webui.models.models import ModelsTable
from open_webui.internal.db import get_db
from sqlalchemy import text
from open_webui.constants import MAI_BUSINESS_MODEL_IDS

def test_user_access(user_id, user_name):
    models_table = ModelsTable()
    
    with get_db() as db:
        print(f"\n{'='*60}")
        print(f"🔍 Testing Model Access for {user_name}")
        print(f"{'='*60}")
        
        # Check if user exists and is in organization
        user = db.execute(
            text("SELECT id, name, email FROM user WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if not user:
            print(f"❌ User {user_id} not found")
            return False
            
        print(f"👤 User: {user[1]} ({user[2]})")
        
        # Check organization membership
        org_membership = db.execute(
            text("SELECT organization_id FROM organization_members WHERE user_id = :user_id AND is_active = 1"),
            {"user_id": user_id}
        ).fetchone()
        
        if org_membership:
            print(f"🏢 Organization: {org_membership[0]}")
        else:
            print("⚠️  User is not in any organization")
            return False
        
        # Get models accessible to user
        accessible_models = models_table.get_models_by_user_id(user_id)
        accessible_ids = {model.id for model in accessible_models}
        
        print(f"📊 Models accessible: {len(accessible_models)}")
        print(f"📊 Expected mAI models: {len(MAI_BUSINESS_MODEL_IDS)}")
        
        # Check matching
        correctly_accessible = accessible_ids & MAI_BUSINESS_MODEL_IDS
        missing_mai_models = MAI_BUSINESS_MODEL_IDS - accessible_ids
        extra_models = accessible_ids - MAI_BUSINESS_MODEL_IDS
        
        print(f"\n🎯 Results:")
        print(f"   ✅ Correct mAI models: {len(correctly_accessible)}/{len(MAI_BUSINESS_MODEL_IDS)}")
        
        if missing_mai_models:
            print(f"   ❌ Missing models: {len(missing_mai_models)}")
            for model_id in sorted(list(missing_mai_models)[:3]):  # Show first 3
                print(f"      - {model_id}")
        
        if extra_models:
            print(f"   ⚠️  Extra models: {len(extra_models)}")
            for model_id in sorted(list(extra_models)[:3]):  # Show first 3
                print(f"      - {model_id}")
        
        # Final result
        if len(correctly_accessible) == len(MAI_BUSINESS_MODEL_IDS) and len(missing_mai_models) == 0:
            if len(extra_models) == 0:
                print(f"   🎉 PERFECT: Access to exactly 12 mAI models")
                return True
            else:
                print(f"   ✅ GOOD: All mAI models + {len(extra_models)} extras")
                return True
        else:
            print(f"   ❌ ISSUE: Missing {len(missing_mai_models)} mAI models")
            return False

def main():
    print("🔍 mAI Development Environment - Model Access Test")
    print("Testing Pat and Olaf's access to organization models")
    
    # Test Pat
    pat_success = test_user_access("pat-user-12345", "Pat")
    
    # Test Olaf  
    olaf_success = test_user_access("olaf-user-67890", "Olaf")
    
    print(f"\n{'='*60}")
    print("🎉 FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Pat's access: {'✅ SUCCESS' if pat_success else '❌ FAILED'}")
    print(f"Olaf's access: {'✅ SUCCESS' if olaf_success else '❌ FAILED'}")
    
    if pat_success and olaf_success:
        print("\n🚀 SOLUTION VERIFIED: Both users can access the 12 mAI business models!")
        print("The discrepancy between user access and organization pricing tab is RESOLVED.")
    else:
        print("\n⚠️  Still some issues to resolve...")

if __name__ == "__main__":
    main()
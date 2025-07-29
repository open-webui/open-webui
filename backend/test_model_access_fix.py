#!/usr/bin/env python3
"""
Test script to verify that users can only see the 12 mAI business models
"""

from open_webui.models.models import ModelsTable
from open_webui.internal.db import get_db
from sqlalchemy import text
from open_webui.constants import MAI_BUSINESS_MODEL_IDS

def main():
    models = ModelsTable()
    
    print("=" * 60)
    print("🔍 mAI Model Access Verification")
    print("=" * 60)
    
    # Test user from organization
    test_user_id = "test-user-123"  # Our test user
    
    with get_db() as db:
        # Check if user exists
        user = db.execute(
            text("SELECT id, name, email FROM user WHERE id = :user_id"),
            {"user_id": test_user_id}
        ).fetchone()
        
        if not user:
            print(f"❌ User {test_user_id} not found, trying first available user...")
            user = db.execute(
                text("SELECT id, name, email FROM user WHERE role != 'pending' LIMIT 1")
            ).fetchone()
            if user:
                test_user_id = user[0]
            else:
                print("❌ No users found in database")
                return
        
        print(f"👤 Testing user: {user[1]} ({user[2]})")
        print(f"   User ID: {test_user_id}")
        
        # Check organization membership
        org_membership = db.execute(
            text("SELECT organization_id FROM organization_members WHERE user_id = :user_id"),
            {"user_id": test_user_id}
        ).fetchone()
        
        if org_membership:
            print(f"🏢 User belongs to organization: {org_membership[0]}")
        else:
            print("⚠️  User is not in any organization")
        
        print("\n" + "-" * 60)
        print("📊 Model Access Test Results:")
        print("-" * 60)
        
        # Get models accessible to user
        accessible_models = models.get_models_by_user_id(test_user_id)
        
        print(f"Models accessible to user: {len(accessible_models)}")
        print(f"Expected mAI business models: {len(MAI_BUSINESS_MODEL_IDS)}")
        
        # Check if accessible models match mAI business models
        accessible_ids = {model.id for model in accessible_models}
        mai_business_ids = MAI_BUSINESS_MODEL_IDS
        
        print("\n🎯 Model Matching Analysis:")
        
        # Models that should be accessible (mAI business models)
        correctly_accessible = accessible_ids & mai_business_ids
        print(f"✅ Correctly accessible mAI models: {len(correctly_accessible)}")
        for model_id in sorted(correctly_accessible):
            print(f"   ✓ {model_id}")
        
        # Missing mAI business models
        missing_mai_models = mai_business_ids - accessible_ids
        if missing_mai_models:
            print(f"\n❌ Missing mAI business models: {len(missing_mai_models)}")
            for model_id in sorted(missing_mai_models):
                print(f"   ✗ {model_id}")
        
        # Extra models that shouldn't be accessible
        extra_models = accessible_ids - mai_business_ids
        if extra_models:
            print(f"\n⚠️  Extra models (not mAI business models): {len(extra_models)}")
            for model_id in sorted(extra_models):
                print(f"   ? {model_id}")
        
        print("\n" + "=" * 60)
        print("🎉 FINAL RESULT:")
        
        if len(correctly_accessible) == len(mai_business_ids) and len(missing_mai_models) == 0:
            if len(extra_models) == 0:
                print("✅ PERFECT: User has access to exactly the 12 mAI business models")
            else:
                print(f"⚠️  GOOD: User has all mAI models but also {len(extra_models)} extra models")
        else:
            print(f"❌ ISSUE: User missing {len(missing_mai_models)} mAI models")
        
        print("=" * 60)

if __name__ == "__main__":
    main()
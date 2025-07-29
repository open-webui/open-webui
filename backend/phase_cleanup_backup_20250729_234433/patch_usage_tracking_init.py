#!/usr/bin/env python3
"""
Patch usage_tracking_init.py to include organization table creation.
This script safely updates the initialization to support organization-based model access.
"""

import os
import shutil
from datetime import datetime


def create_backup(file_path):
    """Create a backup of the original file"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    return backup_path


def patch_usage_tracking_init():
    """Apply the extended initialization to the actual file"""
    source_file = "/app/backend/extended_usage_tracking_init.py"
    target_file = "/app/backend/open_webui/utils/usage_tracking_init.py"
    
    print("🔧 Patching usage_tracking_init.py for organization support...")
    
    try:
        # Create backup of original
        backup = create_backup(target_file)
        
        # Copy extended version
        shutil.copy2(source_file, target_file)
        
        print("✅ Successfully patched usage_tracking_init.py")
        print(f"   Original backed up to: {backup}")
        print("\n📋 New features added:")
        print("   • Organization tables (organization_models, organization_members)")
        print("   • Performance indexes for organization queries")
        print("   • user_available_models view")
        print("   • Automatic model linking for new organizations")
        print("   • Development mode auto-population")
        
        return True
        
    except Exception as e:
        print(f"❌ Error patching file: {e}")
        return False


def verify_patch():
    """Verify the patch was applied correctly"""
    target_file = "/app/backend/open_webui/utils/usage_tracking_init.py"
    
    try:
        with open(target_file, 'r') as f:
            content = f.read()
        
        # Check for key features
        features = [
            "organization_models",
            "organization_members", 
            "user_available_models",
            "ensure_organization_tables",
            "populate_development_members"
        ]
        
        missing = []
        for feature in features:
            if feature not in content:
                missing.append(feature)
        
        if missing:
            print(f"⚠️  Missing features: {', '.join(missing)}")
            return False
        
        print("✅ Patch verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying patch: {e}")
        return False


def main():
    """Main patching function"""
    print("🚀 Usage Tracking Init Patcher")
    print("=" * 50)
    
    if patch_usage_tracking_init():
        if verify_patch():
            print("\n✅ Patching complete!")
            print("\n⚠️  IMPORTANT: Restart the backend for changes to take effect")
            print("   docker restart mai-backend-dev")
        else:
            print("\n⚠️  Patch applied but verification failed")
    else:
        print("\n❌ Patching failed!")
    
    return 0


if __name__ == "__main__":
    exit(main())
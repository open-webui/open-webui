#!/usr/bin/env python3
"""
Patch to modify the Models class to support organization-based model access.
This creates a new method that checks organization membership when determining model access.
"""

import os
import shutil
from datetime import datetime

# The updated get_models_by_user_id method that checks organization membership
NEW_METHOD = '''    def get_models_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[ModelUserResponse]:
        """Get models accessible to a user, including organization-based access"""
        models = self.get_models()
        
        # First, check if model access control is bypassed
        from open_webui.env import BYPASS_MODEL_ACCESS_CONTROL
        if BYPASS_MODEL_ACCESS_CONTROL:
            return models
            
        # Get user's organizations
        user_org_models = set()
        try:
            with get_db() as db:
                # Get user's organizations from organization_members table
                user_orgs = db.execute(
                    text("""
                        SELECT DISTINCT organization_id 
                        FROM organization_members 
                        WHERE user_id = :user_id AND is_active = 1
                    """),
                    {"user_id": user_id}
                ).fetchall()
                
                if user_orgs:
                    # Get models available to these organizations
                    org_ids = [org[0] for org in user_orgs]
                    # Use a different query approach for SQLite
                    placeholders = ', '.join(['?' for _ in org_ids])
                    org_models = db.execute(
                        text(f"""
                            SELECT DISTINCT model_id 
                            FROM organization_models 
                            WHERE organization_id IN ({placeholders}) AND is_active = 1
                        """),
                        org_ids
                    ).fetchall()
                    
                    user_org_models = {model[0] for model in org_models}
        except Exception as e:
            log.warning(f"Failed to get organization models for user {user_id}: {e}")
        
        # Filter models based on organization membership or direct access control
        return [
            model
            for model in models
            if model.id in user_org_models  # Organization-based access
            or model.user_id == user_id  # Owner access
            or has_access(user_id, permission, model.access_control)  # Direct access control
        ]'''

def create_backup(file_path):
    """Create a backup of the original file"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    return backup_path

def patch_models_file():
    """Patch the models.py file to include organization-based access"""
    models_file = "/app/backend/open_webui/models/models.py"
    
    print("🔧 Patching models.py for organization-based access...")
    
    # Read the file
    with open(models_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "organization_members" in content:
        print("⚠️  File already patched!")
        return
    
    # Create backup
    backup_path = create_backup(models_file)
    
    # Add necessary import
    if "from sqlalchemy import text" not in content:
        # Add import after other sqlalchemy imports
        import_line = "from sqlalchemy import or_, and_, func"
        content = content.replace(import_line, f"{import_line}, text")
        print("✅ Added text import")
    
    # Find the get_models_by_user_id method
    method_start = content.find("def get_models_by_user_id(")
    if method_start == -1:
        print("❌ Could not find get_models_by_user_id method!")
        return
    
    # Find the end of the method (next method definition)
    method_end = content.find("\n    def ", method_start + 1)
    if method_end == -1:
        method_end = len(content)
    
    # Replace the method
    before_method = content[:method_start]
    after_method = content[method_end:]
    
    new_content = before_method + NEW_METHOD.strip() + "\n\n" + after_method
    
    # Write the patched file
    with open(models_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully patched models.py")
    print(f"   Backup saved as: {backup_path}")
    
def verify_patch():
    """Verify the patch was applied correctly"""
    models_file = "/app/backend/open_webui/models/models.py"
    
    with open(models_file, 'r') as f:
        content = f.read()
    
    if "organization_members" in content and "organization_models" in content:
        print("✅ Patch verified successfully!")
        return True
    else:
        print("❌ Patch verification failed!")
        return False

def main():
    print("🚀 Organization Model Access Patcher")
    print("=" * 50)
    
    try:
        patch_models_file()
        verify_patch()
        print("\n✅ Patching complete!")
        print("⚠️  Please restart the mAI backend for changes to take effect.")
    except Exception as e:
        print(f"❌ Error during patching: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
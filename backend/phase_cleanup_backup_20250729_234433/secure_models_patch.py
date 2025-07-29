#!/usr/bin/env python3
"""
Security patch for models.py to fix SQL parameterization vulnerability
and add transaction safety to get_models_by_user_id method.
"""

import os
import shutil
from datetime import datetime


# The secure get_models_by_user_id method with proper parameterization and transaction safety
SECURE_METHOD = '''    def get_models_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[ModelUserResponse]:
        """Get models accessible to a user, including organization-based access"""
        models = self.get_models()
        
        # First, check if model access control is bypassed
        from open_webui.env import BYPASS_MODEL_ACCESS_CONTROL
        if BYPASS_MODEL_ACCESS_CONTROL:
            return models
            
        # Get user's organizations with transaction safety
        user_org_models = set()
        try:
            with get_db() as db:
                # Use explicit transaction for atomic reads
                with db.begin():
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
                        
                        # Use proper parameterization with named parameters
                        # This avoids SQL injection vulnerabilities
                        if len(org_ids) == 1:
                            # Single organization - simple query
                            org_models = db.execute(
                                text("""
                                    SELECT DISTINCT model_id 
                                    FROM organization_models 
                                    WHERE organization_id = :org_id AND is_active = 1
                                """),
                                {"org_id": org_ids[0]}
                            ).fetchall()
                        else:
                            # Multiple organizations - use SQLAlchemy's bindparam
                            from sqlalchemy import bindparam
                            
                            # Create a parameterized query with proper binding
                            params = {}
                            param_names = []
                            for i, org_id in enumerate(org_ids):
                                param_name = f"org_{i}"
                                params[param_name] = org_id
                                param_names.append(f":{param_name}")
                            
                            # Build query with named parameters
                            query = text(f"""
                                SELECT DISTINCT model_id 
                                FROM organization_models 
                                WHERE organization_id IN ({', '.join(param_names)}) 
                                AND is_active = 1
                            """)
                            
                            org_models = db.execute(query, params).fetchall()
                        
                        user_org_models = {model[0] for model in org_models}
                        
        except Exception as e:
            log.error(f"Failed to get organization models for user {user_id}: {e}")
            # In case of error, fall back to direct access control only
            # This ensures the method doesn't fail completely
            pass
        
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


def apply_security_patch():
    """Apply the security patch to models.py"""
    models_file = "/app/backend/open_webui/models/models.py"
    
    print("🔒 Applying Security Patch to models.py")
    print("=" * 60)
    
    try:
        # Read the current file
        with open(models_file, 'r') as f:
            content = f.read()
        
        # Check if already patched
        if "with db.begin():" in content:
            print("⚠️  File already patched with transaction safety!")
            return True
        
        # Create backup
        backup = create_backup(models_file)
        
        # Find the get_models_by_user_id method
        method_start = content.find("def get_models_by_user_id(")
        if method_start == -1:
            print("❌ Could not find get_models_by_user_id method!")
            return False
        
        # Find the end of the method (next method definition)
        method_end = content.find("\n    def ", method_start + 1)
        if method_end == -1:
            method_end = content.find("\n\nModels = ", method_start)
            if method_end == -1:
                method_end = len(content)
        
        # Replace the method
        before_method = content[:method_start]
        after_method = content[method_end:]
        
        new_content = before_method + SECURE_METHOD.strip() + "\n\n" + after_method
        
        # Write the patched file
        with open(models_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Security patch applied successfully!")
        print(f"   Backup saved as: {backup}")
        
        print("\n📋 Security improvements:")
        print("   • SQL injection vulnerability fixed")
        print("   • Proper parameter binding implemented")
        print("   • Transaction safety added")
        print("   • Error handling improved")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying patch: {e}")
        return False


def verify_patch():
    """Verify the security patch was applied correctly"""
    models_file = "/app/backend/open_webui/models/models.py"
    
    try:
        with open(models_file, 'r') as f:
            content = f.read()
        
        # Check for security features
        security_features = [
            "with db.begin():",  # Transaction safety
            "param_name = f\"org_{i}\"",  # Named parameters
            "{', '.join(param_names)}",  # Proper parameterization
            "log.error(f\"Failed to get organization models"  # Enhanced error handling
        ]
        
        missing = []
        for feature in security_features:
            if feature not in content:
                missing.append(feature)
        
        if missing:
            print(f"⚠️  Missing security features: {len(missing)}")
            for m in missing:
                print(f"   - {m}")
            return False
        
        print("✅ Security patch verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying patch: {e}")
        return False


def main():
    """Main security patching function"""
    print("🔒 SQLite Security & Transaction Safety Patcher")
    print("Version: 1.0")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if apply_security_patch():
        if verify_patch():
            print("\n✅ Security patching complete!")
            print("\n⚠️  IMPORTANT: Restart the backend for changes to take effect")
            print("   docker restart mai-backend-dev")
        else:
            print("\n⚠️  Patch applied but verification failed")
    else:
        print("\n❌ Security patching failed!")
    
    return 0


if __name__ == "__main__":
    exit(main())
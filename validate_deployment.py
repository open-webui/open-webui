#!/usr/bin/env python3
"""
Validation script for Open WebUI Render deployment
"""

import os
import sys

def validate_render_yaml():
    """Validate the render.yaml configuration"""
    print("🔍 Validating render.yaml configuration...")
    
    try:
        with open('render.yaml', 'r') as f:
            content = f.read()
        
        # Check required sections
        required_sections = [
            'services:',
            'databases:',
            'type: web',
            'name: openwebui',
            'runtime: docker',
            'plan: starter',
            'name: openwebui-postgres'
        ]
        
        for section in required_sections:
            assert section in content, f"Missing required section: {section}"
        
        # Check critical environment variables
        critical_vars = [
            'WEBUI_AUTH',
            'ENABLE_SIGNUP', 
            'ENABLE_INITIAL_ADMIN_SIGNUP',
            'ENABLE_WEB_SEARCH',
            'DATABASE_POOL_SIZE'
        ]
        
        for var in critical_vars:
            assert f"key: {var}" in content, f"Missing critical environment variable: {var}"
        
        # Validate specific settings
        assert 'value: "True"' in content.split('WEBUI_AUTH')[1].split('\n')[1], "Authentication should be enabled"
        assert 'value: "False"' in content.split('ENABLE_SIGNUP')[1].split('\n')[1], "Public signup should be disabled"
        assert 'generateValue: true' in content, "Secret key should be auto-generated"
        
        print("✅ render.yaml configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ render.yaml validation failed: {e}")
        return False

def check_required_files():
    """Check if all required files exist"""
    print("\n🔍 Checking required deployment files...")
    
    required_files = [
        'Dockerfile',
        'render.yaml',
        'DEPLOY_TO_RENDER.md',
        '.env.render.example',
        'backend/requirements.txt',
        'package.json'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def validate_security_config():
    """Validate security configuration"""
    print("\n🔍 Validating security configuration...")
    
    try:
        with open('render.yaml', 'r') as f:
            content = f.read()
        
        security_checks = [
            ('WEBUI_AUTH', 'True', "Authentication should be enabled"),
            ('ENABLE_SIGNUP', 'False', "Public signup should be disabled for private instance"),
            ('WEBUI_SESSION_COOKIE_SECURE', 'true', "Secure cookies should be enabled for HTTPS"),
            ('WEBUI_AUTH_COOKIE_SECURE', 'true', "Auth cookies should be secure for HTTPS"),
            ('DEFAULT_USER_ROLE', 'pending', "New users should require approval"),
        ]
        
        for var, expected, message in security_checks:
            if f"key: {var}" in content:
                # Simple check to see if the expected value appears after the key
                var_section = content.split(f"key: {var}")[1].split("key:")[0]  # Get section until next key
                assert f'value: "{expected}"' in var_section, f"{message} (expected {expected})"
        
        # Check that secret key will be generated
        assert 'generateValue: true' in content, "Secret key should be auto-generated"
        
        print("✅ Security configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ Security validation failed: {e}")
        return False

def main():
    """Main validation function"""
    print("🚀 Open WebUI Render Deployment Validator\n")
    
    all_checks_passed = True
    
    # Run validations
    all_checks_passed &= check_required_files()
    all_checks_passed &= validate_render_yaml()
    all_checks_passed &= validate_security_config()
    
    print("\n" + "="*50)
    
    if all_checks_passed:
        print("✅ All validations passed!")
        print("\n🎉 Your Open WebUI deployment is ready for Render!")
        print("\nNext steps:")
        print("1. Push this code to your GitHub repository")
        print("2. Go to Render Dashboard → New → Blueprint")
        print("3. Connect your repository and deploy")
        print("4. Wait 10-15 minutes for deployment")
        print("5. Set ADMIN_EMAIL in Render dashboard and create admin account")
        print("\nEstimated monthly cost: $14 (Web: $7 + Database: $7)")
        return 0
    else:
        print("❌ Some validations failed!")
        print("Please fix the issues above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

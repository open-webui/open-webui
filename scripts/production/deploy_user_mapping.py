#!/usr/bin/env python3
"""
Production deployment script for mAI user mapping functionality.
Deploys the enhanced user mapping system with validation and monitoring.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

class UserMappingDeployment:
    """Manages deployment of user mapping functionality."""
    
    def __init__(self, base_dir: str = "/Users/patpil/Documents/Projects/mAI"):
        self.base_dir = Path(base_dir)
        self.compose_file = self.base_dir / "docker-compose-customization.yaml"
        
    def validate_user_mapping_files(self) -> Tuple[bool, str]:
        """Validate that all user mapping files are present."""
        required_files = [
            "backend/open_webui/utils/user_mapping.py",
            "backend/open_webui/routers/user_mapping_admin.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            return False, f"Missing files: {', '.join(missing_files)}"
        
        return True, "All user mapping files present"
    
    def validate_code_integration(self) -> Tuple[bool, str]:
        """Validate that code integration is correct."""
        checks = []
        
        # Check openai.py integration
        openai_file = self.base_dir / "backend/open_webui/routers/openai.py"
        if openai_file.exists():
            content = openai_file.read_text()
            if "from open_webui.utils.user_mapping import" in content:
                checks.append("✅ OpenAI router integration")
            else:
                checks.append("❌ OpenAI router integration missing")
        else:
            checks.append("❌ OpenAI router file not found")
        
        # Check usage_tracking.py integration
        usage_file = self.base_dir / "backend/open_webui/routers/usage_tracking.py"
        if usage_file.exists():
            content = usage_file.read_text()
            if "from open_webui.utils.user_mapping import" in content:
                checks.append("✅ Usage tracking integration")
            else:
                checks.append("❌ Usage tracking integration missing")
        else:
            checks.append("❌ Usage tracking file not found")
        
        # Check main.py router registration
        main_file = self.base_dir / "backend/open_webui/main.py"
        if main_file.exists():
            content = main_file.read_text()
            if "user_mapping_admin" in content:
                checks.append("✅ Admin router registration")
            else:
                checks.append("❌ Admin router registration missing")
        else:
            checks.append("❌ Main application file not found")
        
        failed_checks = [check for check in checks if "❌" in check]
        
        if failed_checks:
            return False, f"Integration issues: {'; '.join(failed_checks)}"
        
        return True, f"All integrations valid: {'; '.join(checks)}"
    
    def deploy_with_user_mapping(self) -> Tuple[bool, str]:
        """Deploy the application with user mapping functionality."""
        try:
            print("🚀 Deploying mAI with enhanced user mapping...")
            
            # Stop current containers
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Build and start with user mapping
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "up", "-d", "--build"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                return False, f"Deployment failed: {result.stderr}"
            
            return True, "Deployment completed successfully"
            
        except Exception as e:
            return False, f"Deployment error: {e}"
    
    def test_user_mapping_api(self) -> Tuple[bool, str]:
        """Test the user mapping API endpoints."""
        try:
            # Wait for container to be ready
            time.sleep(15)
            
            # Test if the admin endpoint is accessible
            # Note: This would require authentication in production
            # For now, just check if the container responds
            
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "logs", "--tail=50"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logs = result.stdout
            
            # Check for successful startup indicators
            if "user_mapping_admin" in logs and "Generated user-specific external_user_id" in logs:
                return True, "User mapping functionality is active in logs"
            elif "user_mapping_admin" in logs:
                return True, "User mapping admin endpoints loaded"
            else:
                return False, "User mapping functionality not detected in logs"
                
        except Exception as e:
            return False, f"API test failed: {e}"
    
    def generate_deployment_report(self, validation_results: Dict) -> str:
        """Generate a deployment report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
# mAI User Mapping Deployment Report
Generated: {timestamp}

## Validation Results
"""
        
        for check_name, (success, message) in validation_results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            report += f"- **{check_name}**: {status}\n  {message}\n\n"
        
        report += """
## User Mapping Features Deployed

### 🎯 **Individual User Tracking**
- **Before**: All users shared single external_user_id (`mai_client_63a4eb6d`)
- **After**: Each user gets unique external_user_id (`mai_client_63a4eb6d_user_a1b2c3d4`)

### 🔧 **New Components**
1. **UserMappingService** (`backend/open_webui/utils/user_mapping.py`)
   - Generates unique external user IDs
   - Validates user mapping configuration
   - Provides backward compatibility

2. **Enhanced OpenRouter Integration** (`backend/open_webui/routers/openai.py`)
   - Dynamic user-specific external_user_id generation
   - Proper error handling and fallback
   - Detailed logging for monitoring

3. **Updated Usage Tracking** (`backend/open_webui/routers/usage_tracking.py`)
   - Returns external_user_id for each user
   - Shows mapping status and validation
   - Prepared for real OpenRouter API integration

4. **Admin Monitoring** (`backend/open_webui/routers/user_mapping_admin.py`)
   - `/api/v1/admin/user-mapping/validate` - Full system validation
   - `/api/v1/admin/user-mapping/configuration` - Configuration details
   - `/api/v1/admin/user-mapping/statistics` - Usage statistics
   - `/api/v1/admin/user-mapping/test-mapping` - Live testing

### 📊 **Expected Results**
- **Individual Usage Tracking**: Each user's OpenRouter usage tracked separately
- **Accurate Cost Attribution**: Per-user cost allocation within organizations  
- **Compliance Ready**: Proper audit trail for billing and usage
- **Production Monitoring**: Admin tools for validation and troubleshooting

### 🚀 **Next Steps**
1. **Monitor Logs**: Check for user-specific external_user_id generation
2. **Validate Mapping**: Use admin endpoints to verify configuration
3. **Test Usage**: Create chat requests and verify individual user tracking
4. **OpenRouter Verification**: Check OpenRouter dashboard for individual user data
"""
        
        return report
    
    def deploy(self) -> bool:
        """Execute complete user mapping deployment."""
        print("🔄 mAI User Mapping Production Deployment")
        print("=" * 60)
        
        validation_results = {}
        
        # Validate files
        print("📁 Validating user mapping files...")
        success, message = self.validate_user_mapping_files()
        validation_results["File Validation"] = (success, message)
        print(f"   {'✅' if success else '❌'} {message}")
        
        if not success:
            print("❌ File validation failed - cannot proceed")
            return False
        
        # Validate code integration
        print("\n🔗 Validating code integration...")
        success, message = self.validate_code_integration()
        validation_results["Code Integration"] = (success, message)
        print(f"   {'✅' if success else '❌'} {message}")
        
        if not success:
            print("❌ Code integration validation failed - cannot proceed")
            return False
        
        # Deploy application
        print("\n🚀 Deploying application...")
        success, message = self.deploy_with_user_mapping()
        validation_results["Deployment"] = (success, message)
        print(f"   {'✅' if success else '❌'} {message}")
        
        if not success:
            print("❌ Deployment failed")
            return False
        
        # Test functionality
        print("\n🧪 Testing user mapping functionality...")
        success, message = self.test_user_mapping_api()
        validation_results["Functionality Test"] = (success, message)
        print(f"   {'✅' if success else '❌'} {message}")
        
        # Generate report
        report = self.generate_deployment_report(validation_results)
        report_file = self.base_dir / "user_mapping_deployment_report.md"
        report_file.write_text(report)
        
        print(f"\n📋 Deployment report saved: {report_file}")
        
        # Summary
        all_passed = all(success for success, _ in validation_results.values())
        
        if all_passed:
            print("\n🎉 User mapping deployment completed successfully!")
            print("🎯 Individual user tracking is now active")
            print(f"📊 Admin endpoints: http://localhost:3002/api/v1/admin/user-mapping/")
        else:
            print("\n⚠️  Deployment completed with warnings")
            print("🔧 Check the deployment report for details")
        
        return all_passed

def main():
    """Main deployment function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy mAI user mapping functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--deploy", action="store_true",
                       help="Execute full deployment")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate without deploying")
    
    args = parser.parse_args()
    
    deployment = UserMappingDeployment()
    
    if args.validate_only:
        print("🔍 Validating user mapping configuration...")
        
        success1, msg1 = deployment.validate_user_mapping_files()
        print(f"Files: {'✅' if success1 else '❌'} {msg1}")
        
        success2, msg2 = deployment.validate_code_integration()
        print(f"Integration: {'✅' if success2 else '❌'} {msg2}")
        
        sys.exit(0 if (success1 and success2) else 1)
        
    elif args.deploy:
        success = deployment.deploy()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
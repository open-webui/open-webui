#!/usr/bin/env python3
"""
Production validation script for mAI OpenRouter model filtering.
Validates that the production deployment is working correctly.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

from model_filtering_config import get_expected_models, validate_model_config

class ProductionValidator:
    """Validates production deployment status."""
    
    def __init__(self, compose_file: str = "docker-compose-customization.yaml"):
        self.compose_file = compose_file
        self.expected_models = get_expected_models()
    
    def check_container_status(self) -> Tuple[bool, str]:
        """Check if containers are running."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file, "ps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Docker compose ps failed: {result.stderr}"
            
            if "Up" in result.stdout:
                return True, "Container is running"
            else:
                return False, "Container is not running"
                
        except Exception as e:
            return False, f"Error checking container status: {e}"
    
    def check_environment_variables(self) -> Tuple[bool, str]:
        """Check if environment variables are properly set."""
        try:
            result = subprocess.run(
                ["docker", "exec", "open-webui-customization", "env"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Failed to check environment: {result.stderr}"
            
            env_output = result.stdout
            
            # Check for required variables
            required_vars = [
                "OPENROUTER_API_KEY",
                "OPENROUTER_HOST", 
                "OPENAI_API_CONFIGS",
                "ORGANIZATION_NAME"
            ]
            
            missing_vars = []
            for var in required_vars:
                if f"{var}=" not in env_output:
                    missing_vars.append(var)
            
            if missing_vars:
                return False, f"Missing environment variables: {', '.join(missing_vars)}"
            
            # Validate OPENAI_API_CONFIGS JSON
            for line in env_output.split('\n'):
                if line.startswith('OPENAI_API_CONFIGS='):
                    config_json = line.split('=', 1)[1].strip("'\"")
                    try:
                        config = json.loads(config_json)
                        if not validate_model_config(config):
                            return False, "Invalid OPENAI_API_CONFIGS configuration"
                    except json.JSONDecodeError:
                        return False, "Invalid JSON in OPENAI_API_CONFIGS"
                    break
            
            return True, "Environment variables are properly configured"
            
        except Exception as e:
            return False, f"Error checking environment variables: {e}"
    
    def check_configuration_loading(self) -> Tuple[bool, str]:
        """Check if configuration is loaded correctly in logs."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file, "logs", "--tail=100"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Failed to get logs: {result.stderr}"
            
            logs = result.stdout
            
            # Check for configuration loading indicators
            checks = [
                ("Number of API configs: 1", "API configuration loaded"),
                ("model_ids", "Model IDs configuration present"),
                ("🔗 mAI: Using OpenRouter configuration", "OpenRouter integration active")
            ]
            
            for pattern, description in checks:
                if pattern not in logs:
                    return False, f"Missing: {description} (pattern: '{pattern}')"
            
            # Count model IDs in logs
            model_count = 0
            for model in self.expected_models:
                if model in logs:
                    model_count += 1
            
            if model_count < len(self.expected_models) // 2:  # At least half should be in logs
                return False, f"Only {model_count}/{len(self.expected_models)} expected models found in logs"
            
            return True, f"Configuration loaded successfully with {model_count} models visible"
            
        except Exception as e:
            return False, f"Error checking configuration loading: {e}"
    
    def check_model_filtering_active(self) -> Tuple[bool, str]:
        """Check if model filtering is active and working."""
        try:
            # Look for exact model ID usage in logs
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file, "logs", "--tail=200"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Failed to get detailed logs: {result.stderr}"
            
            logs = result.stdout
            
            # Check for model filtering indicators
            filtering_indicators = [
                "Using exact model IDs",
                "model_list",
                "enable.*true"
            ]
            
            found_indicators = 0
            for indicator in filtering_indicators:
                if indicator in logs:
                    found_indicators += 1
            
            if found_indicators == 0:
                return False, "No model filtering indicators found in logs"
            
            return True, f"Model filtering appears to be active ({found_indicators} indicators found)"
            
        except Exception as e:
            return False, f"Error checking model filtering: {e}"
    
    def validate_deployment(self) -> Dict[str, Tuple[bool, str]]:
        """Run complete deployment validation."""
        print("🔍 Validating production deployment...")
        print("=" * 60)
        
        checks = [
            ("Container Status", self.check_container_status),
            ("Environment Variables", self.check_environment_variables),
            ("Configuration Loading", self.check_configuration_loading),
            ("Model Filtering", self.check_model_filtering_active)
        ]
        
        results = {}
        
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}:")
            try:
                success, message = check_func()
                results[check_name] = (success, message)
                
                if success:
                    print(f"   ✅ {message}")
                else:
                    print(f"   ❌ {message}")
                    
            except Exception as e:
                error_msg = f"Check failed with exception: {e}"
                results[check_name] = (False, error_msg)
                print(f"   ❌ {error_msg}")
        
        return results
    
    def print_summary(self, results: Dict[str, Tuple[bool, str]]):
        """Print validation summary."""
        successful_checks = sum(1 for success, _ in results.values() if success)
        total_checks = len(results)
        
        print(f"\n📊 Validation Summary:")
        print(f"   ✅ Successful: {successful_checks}/{total_checks}")
        print(f"   ❌ Failed: {total_checks - successful_checks}/{total_checks}")
        
        if successful_checks == total_checks:
            print("\n🎉 Production deployment validation PASSED!")
            print(f"🎯 Model filtering active with {len(self.expected_models)} approved models")
            print("\n🚀 Ready for production use!")
        else:
            print("\n⚠️  Production deployment validation FAILED!")
            print("🔧 Please check the failed items above and resolve issues.")
            
            # Show failed checks
            failed_checks = [name for name, (success, _) in results.items() if not success]
            print(f"🚨 Failed checks: {', '.join(failed_checks)}")

def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate mAI production deployment")
    parser.add_argument("--compose-file", default="docker-compose-customization.yaml",
                       help="Docker compose file to use")
    parser.add_argument("--wait", type=int, default=0,
                       help="Wait N seconds before validation (for startup)")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for deployment to stabilize...")
        time.sleep(args.wait)
    
    validator = ProductionValidator(compose_file=args.compose_file)
    results = validator.validate_deployment()
    validator.print_summary(results)
    
    # Exit with appropriate code
    all_passed = all(success for success, _ in results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
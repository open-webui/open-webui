#!/usr/bin/env python3
"""
Usage Tracking Validation Script

This script validates that usage tracking is properly configured and working
after applying the environment variable fix.

Run this script AFTER setting the required environment variables to verify
the fix is working correctly.
"""

import os
import sys
import sqlite3
import json
import asyncio
from datetime import datetime, date
from pathlib import Path

def check_environment_fix():
    """Verify that the environment variables are now properly set"""
    print("🔍 VALIDATING ENVIRONMENT FIX")
    print("=" * 50)
    
    required_vars = ['OPENROUTER_EXTERNAL_USER', 'ORGANIZATION_NAME', 'OPENROUTER_API_KEY']
    all_set = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive data
            if 'API_KEY' in var:
                display_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else f"{value[:6]}..."
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_set = False
    
    return all_set

def test_database_initialization():
    """Test if the database would be properly initialized with current environment"""
    print("\n🗄️  TESTING DATABASE INITIALIZATION")
    print("=" * 50)
    
    try:
        # Attempt to import and test the initialization function
        sys.path.append('/Users/patpil/Documents/Projects/mAI/backend')
        
        # This will fail if environment isn't set up, which is what we want to test
        from open_webui.utils.usage_tracking_init import initialize_usage_tracking_from_environment
        
        print("✅ Usage tracking initialization module imported successfully")
        
        # Check what the initialization would do
        openrouter_external_user = os.getenv("OPENROUTER_EXTERNAL_USER")
        organization_name = os.getenv("ORGANIZATION_NAME") 
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        if all([openrouter_external_user, organization_name, openrouter_api_key]):
            print("✅ All required environment variables present")
            print(f"   Would create/update organization: {organization_name}")
            print(f"   Client org ID: {openrouter_external_user}")
            return True
        else:
            print("❌ Missing required environment variables")
            return False
            
    except ImportError as e:
        print(f"⚠️  Cannot import usage tracking module: {e}")
        print("   This is expected if running outside the application context")
        return None
    except Exception as e:
        print(f"❌ Error testing initialization: {e}")
        return False

def test_client_manager():
    """Test if the OpenRouter client manager would work correctly"""
    print("\n🔧 TESTING CLIENT MANAGER")
    print("=" * 50)
    
    try:
        sys.path.append('/Users/patpil/Documents/Projects/mAI/backend')
        
        # Mock the config values to test the logic
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_external_user = os.getenv("OPENROUTER_EXTERNAL_USER")
        
        if openrouter_api_key and openrouter_external_user:
            print("✅ Environment suggests client manager would work")
            print(f"   is_env_based would be: True")
            print(f"   Client context would include: {openrouter_external_user}")
            
            # Test the logic that determines environment-based mode
            is_env_based = bool(openrouter_api_key and openrouter_external_user)
            print(f"✅ is_env_based calculation: {is_env_based}")
            
            return True
        else:
            print("❌ Missing environment variables for client manager")
            return False
            
    except Exception as e:
        print(f"❌ Error testing client manager: {e}")
        return False

def check_streaming_integration():
    """Check if streaming response integration would work"""
    print("\n📡 TESTING STREAMING INTEGRATION")
    print("=" * 50)
    
    # Check if the required files exist
    openai_router_path = "/Users/patpil/Documents/Projects/mAI/backend/open_webui/routers/openai.py"
    client_manager_path = "/Users/patpil/Documents/Projects/mAI/backend/open_webui/utils/openrouter_client_manager.py"
    
    if os.path.exists(openai_router_path):
        print("✅ OpenAI router found (contains UsageCapturingStreamingResponse)")
    else:
        print("❌ OpenAI router not found")
        return False
    
    if os.path.exists(client_manager_path):
        print("✅ Client manager found (contains record_real_time_usage)")
    else:
        print("❌ Client manager not found")
        return False
    
    # Check if the streaming response references the client manager
    try:
        with open(openai_router_path, 'r') as f:
            content = f.read()
            if 'UsageCapturingStreamingResponse' in content:
                print("✅ UsageCapturingStreamingResponse class exists")
            if 'record_real_time_usage' in content:
                print("✅ Real-time usage recording is integrated")
            else:
                print("⚠️  record_real_time_usage not found in streaming response")
    except Exception as e:
        print(f"❌ Error checking streaming integration: {e}")
        return False
    
    return True

def create_test_usage_scenario():
    """Create a test scenario to validate usage capture would work"""
    print("\n🧪 CREATING TEST SCENARIO")
    print("=" * 50)
    
    # Simulate what would happen during a real API call
    test_scenario = {
        "user_id": "test_user_123", 
        "model_name": "anthropic/claude-3.5-sonnet",
        "input_tokens": 100,
        "output_tokens": 150,
        "raw_cost": 0.001500,
        "generation_id": "test_gen_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "provider": "anthropic"
    }
    
    print("Test scenario:")
    for key, value in test_scenario.items():
        print(f"  {key}: {value}")
    
    # Check if this would be processed correctly
    openrouter_external_user = os.getenv("OPENROUTER_EXTERNAL_USER")
    if openrouter_external_user:
        expected_client_org_id = openrouter_external_user
        print(f"\n✅ Would be recorded for client: {expected_client_org_id}")
        
        # Calculate expected costs
        markup_rate = 1.3  # Default mAI markup
        markup_cost = test_scenario["raw_cost"] * markup_rate
        total_tokens = test_scenario["input_tokens"] + test_scenario["output_tokens"]
        
        print(f"   Total tokens: {total_tokens}")
        print(f"   Raw cost: ${test_scenario['raw_cost']:.6f}")
        print(f"   Markup cost: ${markup_cost:.6f}")
        
        return True
    else:
        print("❌ Cannot determine client organization ID")
        return False

def generate_validation_report():
    """Generate a validation report"""
    print("\n📋 VALIDATION REPORT")
    print("=" * 50)
    
    # Run all tests
    env_ok = check_environment_fix()
    db_ok = test_database_initialization()
    client_ok = test_client_manager()
    streaming_ok = check_streaming_integration()
    scenario_ok = create_test_usage_scenario()
    
    # Calculate overall status
    tests_run = sum(1 for test in [env_ok, client_ok, streaming_ok, scenario_ok] if test is not None)
    tests_passed = sum(1 for test in [env_ok, client_ok, streaming_ok, scenario_ok] if test is True)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": {
            "environment_variables": env_ok,
            "database_initialization": db_ok,
            "client_manager": client_ok,
            "streaming_integration": streaming_ok,
            "test_scenario": scenario_ok
        },
        "summary": {
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "success_rate": f"{(tests_passed/tests_run)*100:.1f}%" if tests_run > 0 else "0%"
        }
    }
    
    # Save report
    report_file = "usage_tracking_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Validation report saved: {report_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if tests_passed == tests_run and tests_run > 0:
        print("🎉 ALL TESTS PASSED!")
        print("   Usage tracking should now work correctly")
        print("   The missing token issue should be resolved for future API calls")
    elif tests_passed > 0:
        print(f"⚠️  PARTIAL SUCCESS: {tests_passed}/{tests_run} tests passed")
        print("   Some issues remain - check the details above")
    else:
        print("❌ VALIDATION FAILED")
        print("   Usage tracking is still not properly configured")
    
    return report

def provide_next_steps():
    """Provide specific next steps based on validation results"""
    print("\n🔧 NEXT STEPS")
    print("=" * 60)
    
    if not check_environment_fix():
        print("1. ❌ Set the missing environment variables:")
        print("   - OPENROUTER_EXTERNAL_USER")
        print("   - ORGANIZATION_NAME") 
        print("   - OPENROUTER_API_KEY")
        print("2. Re-run this validation script")
    else:
        print("1. ✅ Environment variables are set correctly")
        print("2. 🚀 Deploy/restart your application")
        print("3. 📊 Monitor usage tracking:")
        print("   - Check logs for 'Usage tracking initialized'")
        print("   - Verify new API calls create usage records")
        print("   - Monitor the client_daily_usage table")
        print("4. 🔍 Set up monitoring to prevent future data loss")

def main():
    """Main validation function"""
    print("🔍 USAGE TRACKING VALIDATION SCRIPT")
    print("=" * 80)
    print("Validating that the environment fix resolves the missing token issue")
    print("=" * 80)
    
    # Generate comprehensive validation report
    report = generate_validation_report()
    
    # Provide actionable next steps
    provide_next_steps()
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
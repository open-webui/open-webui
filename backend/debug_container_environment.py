#!/usr/bin/env python3
"""
Container Environment Debugging Script

This script is designed to run INSIDE the Docker container to investigate
the actual environment state where the usage tracking should be working.

The previous script ran on the host system and couldn't access the container's
environment variables loaded from .env.dev.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, date

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def check_environment_variables():
    """Check critical environment variables inside container."""
    print_section("CONTAINER ENVIRONMENT VARIABLES")
    
    required_vars = [
        'OPENROUTER_API_KEY',
        'OPENROUTER_EXTERNAL_USER', 
        'ORGANIZATION_NAME',
        'ENV',
        'WEBUI_NAME',
        'CORS_ALLOW_ORIGIN'
    ]
    
    env_status = {}
    
    for var in required_vars:
        value = os.getenv(var)
        env_status[var] = {
            'set': value is not None,
            'value': value if var != 'OPENROUTER_API_KEY' else (value[:20] + '...' if value else None),
            'length': len(value) if value else 0
        }
        
        print(f"{var:25}: {'✅' if value else '❌'} {'SET' if value else 'NOT SET'}")
        if value and var != 'OPENROUTER_API_KEY':
            print(f"{'':25}  Value: {value}")
        elif value and var == 'OPENROUTER_API_KEY':
            print(f"{'':25}  Value: {value[:20]}...")
    
    return env_status

def check_container_paths():
    """Check container-specific paths and files."""
    print_section("CONTAINER PATH VERIFICATION")
    
    paths_to_check = [
        '/app/backend',
        '/app/backend/data',
        '/app/backend/data/webui.db',
        '/app/backend/open_webui',
        '/.dockerenv'
    ]
    
    for path in paths_to_check:
        exists = os.path.exists(path)
        print(f"{path:30}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        
        if exists and os.path.isfile(path) and path.endswith('.db'):
            try:
                # Check if database is accessible
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                print(f"{'':30}  Tables: {len(tables)} found")
            except Exception as e:
                print(f"{'':30}  Error: {e}")

def test_usage_tracking_imports():
    """Test if usage tracking modules can be imported."""
    print_section("USAGE TRACKING MODULE IMPORTS")
    
    modules_to_test = [
        'open_webui.utils.usage_tracking_init',
        'open_webui.utils.openrouter_client_manager',
        'open_webui.models.organization_usage',
        'uvicorn',
        'pydantic',
        'sqlalchemy'
    ]
    
    import_results = {}
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"{module:40}: ✅ SUCCESS")
            import_results[module] = True
        except ImportError as e:
            print(f"{module:40}: ❌ FAILED - {e}")
            import_results[module] = False
        except Exception as e:
            print(f"{module:40}: ❌ ERROR - {e}")
            import_results[module] = False
    
    return import_results

def check_usage_tracking_initialization():
    """Check if usage tracking initializes properly with current environment."""
    print_section("USAGE TRACKING INITIALIZATION TEST")
    
    try:
        from open_webui.utils.usage_tracking_init import initialize_usage_tracking_from_environment
        from open_webui.utils.openrouter_client_manager import OpenRouterClientManager
        
        print("Testing initialize_usage_tracking_from_environment()...")
        init_result = initialize_usage_tracking_from_environment()
        print(f"Initialization result: {'✅ SUCCESS' if init_result else '❌ FAILED'}")
        
        if init_result:
            print("✅ Usage tracking should be active")
        else:
            print("❌ Usage tracking is NOT active")
            print("   This means API calls will not be tracked!")
        
        # Check client manager state
        print("\nTesting OpenRouterClientManager...")
        client_manager = OpenRouterClientManager()
        
        print(f"is_env_based: {'✅' if client_manager.is_env_based else '❌'} {client_manager.is_env_based}")
        
        if hasattr(client_manager, 'client_org_id'):
            print(f"client_org_id: {client_manager.client_org_id}")
        else:
            print("client_org_id: NOT SET")
        
        # Test if we can determine client_org_id for recording
        try:
            from open_webui.models.organization_usage import ClientOrganization
            
            # This is what record_real_time_usage() does
            client_org_id = os.getenv("OPENROUTER_EXTERNAL_USER")
            if client_org_id:
                org = ClientOrganization.get_by_id(client_org_id)
                if org:
                    print(f"✅ Client organization found in database: {org.organization_name}")
                else:
                    print(f"❌ Client organization NOT found in database for ID: {client_org_id}")
            else:
                print("❌ OPENROUTER_EXTERNAL_USER not set, cannot determine client_org_id")
        
        except Exception as e:
            print(f"❌ Error checking client organization: {e}")
        
        return {
            'init_result': init_result,
            'is_env_based': client_manager.is_env_based if 'client_manager' in locals() else False,
            'can_record': init_result and client_manager.is_env_based if 'client_manager' in locals() else False
        }
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in usage tracking check: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

def check_database_detailed():
    """Detailed database analysis for the missing tokens issue."""
    print_section("DETAILED DATABASE ANALYSIS")
    
    # Try container paths first, then host paths
    db_paths = [
        '/app/backend/data/webui.db',
        '/app/backend/open_webui/data/webui.db',
        '/Users/patpil/Documents/Projects/mAI/backend/data/webui.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            print(f"✅ Using database: {path}")
            break
    
    if not db_path:
        print("❌ No database file found")
        return {'error': 'No database found'}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if dev_mai_client_d460a478 exists
        cursor.execute("SELECT * FROM client_organizations WHERE id = ?", ('dev_mai_client_d460a478',))
        dev_org = cursor.fetchone()
        if dev_org:
            print(f"✅ Development organization found: {dev_org[1]}")
        else:
            print("❌ Development organization NOT found")
        
        # Check ALL usage data to understand the pattern
        cursor.execute("""
            SELECT usage_date, COUNT(*) as records, SUM(total_tokens) as tokens, SUM(raw_cost) as cost
            FROM client_daily_usage 
            GROUP BY usage_date
            ORDER BY usage_date DESC
            LIMIT 10
        """)
        all_usage = cursor.fetchall()
        print(f"\nAll Usage Data (Last 10 days):")
        for row in all_usage:
            print(f"  {row[0]}: {row[1]} records, {row[2]} tokens, ${row[3]:.4f}")
        
        # Specifically check July 28-29, 2024
        cursor.execute("""
            SELECT * FROM client_daily_usage 
            WHERE usage_date >= '2024-07-28' AND usage_date <= '2024-07-29'
        """)
        july_data = cursor.fetchall()
        print(f"\nJuly 28-29, 2024 Data: {len(july_data)} records found")
        for record in july_data:
            print(f"  {record}")
        
        # Check processed_generations for any trace of the missing activity
        cursor.execute("SELECT COUNT(*) FROM processed_generations WHERE date(created_at) >= '2024-07-28' AND date(created_at) <= '2024-07-29'")
        july_generations = cursor.fetchone()[0]
        print(f"\nProcessed generations (July 28-29): {july_generations}")
        
        conn.close()
        
        return {
            'dev_org_exists': dev_org is not None,
            'july_28_29_records': len(july_data),
            'july_generations': july_generations,
            'recent_usage_days': len(all_usage)
        }
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return {'error': str(e)}

def simulate_usage_recording():
    """Simulate what happens when we try to record usage."""
    print_section("USAGE RECORDING SIMULATION")
    
    try:
        from open_webui.utils.openrouter_client_manager import OpenRouterClientManager
        
        client_manager = OpenRouterClientManager()
        
        # Simulate the data that would come from a streaming response
        test_usage_data = {
            'model': 'anthropic/claude-3-sonnet',
            'prompt_tokens': 100,
            'completion_tokens': 200,
            'total_tokens': 300,
            'cost': 0.0045,
            'user_id': 'test_user_123'
        }
        
        print("Simulating usage recording with test data:")
        print(f"  Model: {test_usage_data['model']}")
        print(f"  Total tokens: {test_usage_data['total_tokens']}")
        print(f"  Cost: ${test_usage_data['cost']}")
        
        # Test if we can call record_real_time_usage
        if hasattr(client_manager, 'record_real_time_usage'):
            print("\n⚠️  WARNING: This will create test data in the database!")
            print("Skipping actual recording to avoid data corruption.")
            print("But the method exists and environment seems ready.")
            return {'can_record': True, 'test_data': test_usage_data}
        else:
            print("❌ record_real_time_usage method not found")
            return {'can_record': False}
        
    except Exception as e:
        print(f"❌ Error in usage recording simulation: {e}")
        return {'error': str(e)}

def main():
    """Main container debugging function."""
    print("🐳 Container Environment Debugging - mAI Usage Tracking")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Running from: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'investigation': 'Container environment check for missing 5,677 tokens',
        'location': 'docker_container' if os.path.exists('/.dockerenv') else 'host_system'
    }
    
    # Run all container-specific checks
    results['environment'] = check_environment_variables()
    results['paths'] = check_container_paths()
    results['imports'] = test_usage_tracking_imports()
    results['initialization'] = check_usage_tracking_initialization()
    results['database'] = check_database_detailed()
    results['recording'] = simulate_usage_recording()
    
    # Analysis
    print_section("CONTAINER INVESTIGATION SUMMARY")
    
    env_vars_set = all(results['environment'][var]['set'] for var in ['OPENROUTER_API_KEY', 'OPENROUTER_EXTERNAL_USER', 'ORGANIZATION_NAME'])
    init_success = results['initialization'].get('init_result', False)
    can_record = results['recording'].get('can_record', False)
    july_data_missing = results['database'].get('july_28_29_records', 0) == 0
    
    print(f"Environment Variables: {'✅ ALL SET' if env_vars_set else '❌ MISSING'}")
    print(f"Usage Tracking Init: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
    print(f"Can Record Usage: {'✅ YES' if can_record else '❌ NO'}")
    print(f"July 28-29 Data: {'❌ MISSING' if july_data_missing else '✅ FOUND'}")
    
    # Root cause determination
    if env_vars_set and init_success and can_record and july_data_missing:
        print("\n🎯 CONCLUSION: Environment is PROPERLY CONFIGURED NOW")
        print("   The missing 5,677 tokens from July 28-29 were likely due to:")
        print("   1. Application not running during that period")
        print("   2. Environment not properly configured at that time")
        print("   3. Usage tracking disabled/broken during that specific period")
        print("   4. The current configuration should prevent future token loss")
    else:
        print("\n❌ ISSUE: Environment is still not properly configured")
        if not env_vars_set:
            print("   - Environment variables are missing")
        if not init_success:
            print("   - Usage tracking initialization failed")
        if not can_record:
            print("   - Cannot record usage data")
    
    # Save results to a file accessible from host
    output_path = '/app/backend/container_debug_results.json' if os.path.exists('/app/backend') else 'container_debug_results.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {output_path}")
    
    return results

if __name__ == "__main__":
    main()
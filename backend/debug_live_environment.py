#!/usr/bin/env python3
"""
Live Environment Debugging Script

This script investigates the current state of the usage tracking system
in the running development environment to identify why 5,677 tokens
from July 28-29 were not captured despite .env.dev being configured.

Focus Areas:
1. Environment variable verification in live container
2. Usage tracking initialization status
3. Database state examination
4. API call flow testing
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path

# Add the open_webui module to the path
sys.path.insert(0, '/Users/patpil/Documents/Projects/mAI/backend')

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def check_environment_variables():
    """Check critical environment variables."""
    print_section("ENVIRONMENT VARIABLES CHECK")
    
    required_vars = [
        'OPENROUTER_API_KEY',
        'OPENROUTER_EXTERNAL_USER', 
        'ORGANIZATION_NAME'
    ]
    
    env_status = {}
    
    for var in required_vars:
        value = os.getenv(var)
        env_status[var] = {
            'set': value is not None,
            'value': value[:20] + '...' if value and len(value) > 20 else value,
            'length': len(value) if value else 0
        }
        
        print(f"{var:25}: {'✅' if value else '❌'} {'SET' if value else 'NOT SET'}")
        if value:
            print(f"{'':25}  Value: {value[:30]}{'...' if len(value) > 30 else ''}")
    
    return env_status

def check_usage_tracking_initialization():
    """Check if usage tracking was initialized properly."""
    print_section("USAGE TRACKING INITIALIZATION")
    
    try:
        from open_webui.utils.usage_tracking_init import initialize_usage_tracking_from_environment
        from open_webui.utils.openrouter_client_manager import OpenRouterClientManager
        
        # Test initialization
        print("Testing initialize_usage_tracking_from_environment()...")
        init_result = initialize_usage_tracking_from_environment()
        print(f"Initialization result: {'✅ SUCCESS' if init_result else '❌ FAILED'}")
        
        # Check client manager state
        print("\nChecking OpenRouterClientManager state...")
        client_manager = OpenRouterClientManager()
        
        print(f"is_env_based: {'✅' if client_manager.is_env_based else '❌'} {client_manager.is_env_based}")
        print(f"client_org_id: {getattr(client_manager, 'client_org_id', 'NOT SET')}")
        
        return {
            'init_result': init_result,
            'is_env_based': client_manager.is_env_based,
            'client_org_id': getattr(client_manager, 'client_org_id', None)
        }
        
    except Exception as e:
        print(f"❌ ERROR checking initialization: {e}")
        return {'error': str(e)}

def check_database_state():
    """Check current database state."""
    print_section("DATABASE STATE ANALYSIS")
    
    db_paths = [
        '/Users/patpil/Documents/Projects/mAI/backend/data/webui.db',
        '/Users/patpil/Documents/Projects/mAI/backend/open_webui/data/webui.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ No database file found")
        return None
    
    print(f"Database found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check client organizations
        cursor.execute("SELECT * FROM client_organizations")
        orgs = cursor.fetchall()
        print(f"\nClient Organizations: {len(orgs)} found")
        for org in orgs:
            print(f"  - {org}")
        
        # Check usage data for July 28-29
        cursor.execute("""
            SELECT usage_date, COUNT(*) as records, SUM(total_tokens) as tokens, SUM(raw_cost) as cost
            FROM client_daily_usage 
            WHERE usage_date >= '2024-07-28' AND usage_date <= '2024-07-29'
            GROUP BY usage_date
            ORDER BY usage_date
        """)
        usage_data = cursor.fetchall()
        print(f"\nUsage Data (July 28-29): {len(usage_data)} days with data")
        for row in usage_data:
            print(f"  - {row[0]}: {row[1]} records, {row[2]} tokens, ${row[3]:.4f} cost")
        
        # Check recent usage (last 7 days)
        cursor.execute("""
            SELECT usage_date, COUNT(*) as records, SUM(total_tokens) as tokens
            FROM client_daily_usage 
            WHERE usage_date >= date('now', '-7 days')
            GROUP BY usage_date
            ORDER BY usage_date DESC
        """)
        recent_usage = cursor.fetchall()
        print(f"\nRecent Usage (Last 7 Days): {len(recent_usage)} days")
        for row in recent_usage:
            print(f"  - {row[0]}: {row[1]} records, {row[2]} tokens")
        
        # Check processed_generations table
        cursor.execute("SELECT COUNT(*) FROM processed_generations")
        gen_count = cursor.fetchone()[0]
        print(f"\nProcessed Generations: {gen_count} records")
        
        conn.close()
        
        return {
            'organizations': len(orgs),
            'july_28_29_usage': usage_data,
            'recent_usage': recent_usage,
            'processed_generations': gen_count
        }
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return {'error': str(e)}

def test_api_endpoint():
    """Test if we can access the health endpoint to verify container is responsive."""
    print_section("API ENDPOINT TEST")
    
    try:
        import requests
        
        # Test health endpoint 
        print("Testing health endpoint...")
        response = requests.get("http://localhost:8080/health", timeout=5)
        print(f"Health endpoint: {'✅ ACCESSIBLE' if response.status_code == 200 else '❌ ERROR'}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                health_data = response.json()
                print(f"Health data: {health_data}")
            except:
                print(f"Health response: {response.text[:200]}")
        
        return {'accessible': response.status_code == 200}
        
    except Exception as e:
        print(f"❌ Cannot test API endpoint: {e}")
        return {'error': str(e)}

def check_container_environment():
    """Check if we're running inside the container vs host system."""
    print_section("RUNTIME ENVIRONMENT")
    
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"Running as user: {os.getenv('USER', 'unknown')}")
    
    # Check if container files exist
    container_indicators = [
        '/app/backend',
        '/app/backend/data', 
        '/.dockerenv'
    ]
    
    in_container = False
    for indicator in container_indicators:
        exists = os.path.exists(indicator)
        print(f"{indicator}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        if exists:
            in_container = True
    
    print(f"\nEnvironment: {'🐳 CONTAINER' if in_container else '🖥️  HOST SYSTEM'}")
    
    return {'in_container': in_container}

def investigate_missing_tokens():
    """Specific investigation for the missing 5,677 tokens."""
    print_section("MISSING TOKENS INVESTIGATION")
    
    print("Analyzing the specific issue: 5,677 tokens from July 28-29")
    
    # Check if there are any logs or traces
    log_paths = [
        '/Users/patpil/Documents/Projects/mAI/backend/backend.log',
        '/Users/patpil/Documents/Projects/mAI/backend.log',
        '/app/backend/logs'
    ]
    
    print("\nChecking for logs...")
    for log_path in log_paths:
        if os.path.exists(log_path):
            print(f"✅ Found log: {log_path}")
            if os.path.isfile(log_path):
                try:
                    with open(log_path, 'r') as f:
                        # Get last 10 lines
                        lines = f.readlines()[-10:]
                        print("Last 10 log lines:")
                        for line in lines:
                            print(f"  {line.strip()}")
                except Exception as e:
                    print(f"❌ Cannot read log: {e}")
        else:
            print(f"❌ No log found: {log_path}")
    
    # Check if there are any webhook records or API call traces
    print("\nLooking for API call traces...")
    
    # This would require checking application logs or webhook data
    # For now, document what we need to investigate
    investigation_points = [
        "Check OpenRouter dashboard for actual usage during July 28-29",
        "Verify if streaming responses were created but not saved",
        "Check for any errors during real-time usage recording",
        "Verify timing of usage tracking initialization vs API calls"
    ]
    
    for point in investigation_points:
        print(f"📋 TODO: {point}")
    
    return {'investigation_points': investigation_points}

def main():
    """Main investigation function."""
    print("🔍 Live Environment Debugging - mAI Usage Tracking")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'investigation': 'Missing 5,677 tokens from July 28-29'
    }
    
    # Run all checks
    results['environment'] = check_environment_variables()
    results['runtime'] = check_container_environment()
    results['initialization'] = check_usage_tracking_initialization()
    results['database'] = check_database_state()
    results['api'] = test_api_endpoint()
    results['missing_tokens'] = investigate_missing_tokens()
    
    # Summary
    print_section("INVESTIGATION SUMMARY")
    
    # Check if environment is properly configured
    env_ok = all(results['environment'][var]['set'] for var in ['OPENROUTER_API_KEY', 'OPENROUTER_EXTERNAL_USER', 'ORGANIZATION_NAME'])
    init_ok = results['initialization'].get('init_result', False)
    db_has_july_data = len(results['database'].get('july_28_29_usage', [])) > 0 if results.get('database') else False
    
    print(f"Environment Variables: {'✅ ALL SET' if env_ok else '❌ MISSING'}")
    print(f"Usage Tracking Init: {'✅ SUCCESS' if init_ok else '❌ FAILED'}")
    print(f"July 28-29 Data: {'✅ FOUND' if db_has_july_data else '❌ MISSING'}")
    
    # Root cause analysis
    if env_ok and init_ok and not db_has_july_data:
        print("\n🎯 ROOT CAUSE: Environment is configured and initialized, but July 28-29 data is missing")
        print("   This suggests the issue occurred during that specific time period")
        print("   Possible causes:")
        print("   1. Application was not running during July 28-29")
        print("   2. Usage tracking was disabled/broken during that period")
        print("   3. API calls didn't go through the streaming capture system")
        print("   4. Database writes failed for that period")
    elif not env_ok:
        print("\n🎯 ROOT CAUSE: Environment variables are not properly set")
    elif not init_ok:
        print("\n🎯 ROOT CAUSE: Usage tracking initialization failed")
    
    # Save results
    with open('/Users/patpil/Documents/Projects/mAI/backend/live_environment_debug_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: live_environment_debug_results.json")
    
    return results

if __name__ == "__main__":
    main()
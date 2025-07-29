#!/usr/bin/env python3
"""
Critical Usage Capture Failure Investigation Script

Investigates why 5,677 tokens from July 28-29 API calls were not captured
by the real-time usage tracking system.

Investigation Points:
1. Startup initialization logs - "✅ Usage tracking initialized"
2. Environment variables - OPENROUTER_EXTERNAL_USER, ORGANIZATION_NAME  
3. Client organization setup in database
4. Streaming capture - UsageCapturingStreamingResponse implementation
5. Real-time recording - openrouter_client_manager.record_real_time_usage()
6. Generation ID tracking - processed_generations table
7. Database path verification
"""

import os
import sys
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup comprehensive logging for debugging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('debug_usage_capture.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def check_environment_variables(logger):
    """Investigation Point #2: Verify critical environment variables"""
    logger.info("🔍 INVESTIGATION POINT #2: Checking environment variables")
    
    critical_vars = [
        'OPENROUTER_EXTERNAL_USER',
        'ORGANIZATION_NAME', 
        'OPENROUTER_API_KEY',
        'DATABASE_URL',
        'DATA_DIR'
    ]
    
    results = {}
    for var in critical_vars:
        value = os.getenv(var)
        results[var] = {
            'set': value is not None,
            'value': value if value else 'NOT SET',
            'masked_value': f"{value[:10]}..." if value and len(value) > 10 else value
        }
        
        if value:
            logger.info(f"  ✅ {var}: {results[var]['masked_value']}")
        else:
            logger.error(f"  ❌ {var}: NOT SET")
    
    return results

def find_database_files(logger):
    """Investigation Point #7: Find and verify database paths"""
    logger.info("🔍 INVESTIGATION POINT #7: Finding database files")
    
    possible_paths = [
        'data/webui.db',
        '../data/webui.db', 
        'backend/data/webui.db',
        '/app/backend/data/webui.db',
        os.path.expanduser('~/Documents/Projects/mAI/backend/data/webui.db'),
        './open_webui/database/database.db'
    ]
    
    # Also check DATA_DIR environment variable
    data_dir = os.getenv('DATA_DIR')
    if data_dir:
        possible_paths.append(os.path.join(data_dir, 'webui.db'))
    
    found_databases = []
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            stat = os.stat(abs_path)
            found_databases.append({
                'path': abs_path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'readable': os.access(abs_path, os.R_OK),
                'writable': os.access(abs_path, os.W_OK)
            })
            logger.info(f"  ✅ Found database: {abs_path}")
            logger.info(f"     Size: {stat.st_size} bytes, Modified: {datetime.fromtimestamp(stat.st_mtime)}")
    
    if not found_databases:
        logger.error("  ❌ No database files found!")
    
    return found_databases

def check_client_organization_setup(logger, db_path: str):
    """Investigation Point #3: Check client organization setup"""
    logger.info("🔍 INVESTIGATION POINT #3: Checking client organization setup")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if client_organizations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='client_organizations'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            logger.error("  ❌ client_organizations table does not exist!")
            return None
            
        # Get all client organizations
        cursor.execute("SELECT * FROM client_organizations")
        organizations = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"  Found {len(organizations)} client organizations:")
        for org in organizations:
            logger.info(f"    - ID: {org.get('id')}, Name: {org.get('name')}, External User: {org.get('external_user_id')}")
        
        # Check current environment organization
        current_org = os.getenv('ORGANIZATION_NAME')
        current_external_user = os.getenv('OPENROUTER_EXTERNAL_USER') 
        
        if current_org:
            cursor.execute("SELECT * FROM client_organizations WHERE name = ?", (current_org,))
            current_org_record = cursor.fetchone()
            if current_org_record:
                logger.info(f"  ✅ Current organization '{current_org}' found in database")
                current_org_record = dict(current_org_record)
            else:
                logger.error(f"  ❌ Current organization '{current_org}' NOT found in database!")
        
        conn.close()
        return {
            'organizations': organizations,
            'current_org_record': current_org_record if current_org else None,
            'environment_org': current_org,
            'environment_external_user': current_external_user
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error checking client organizations: {e}")
        return None

def check_processed_generations(logger, db_path: str):
    """Investigation Point #6: Check generation_id tracking"""
    logger.info("🔍 INVESTIGATION POINT #6: Checking processed_generations table")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if processed_generations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='processed_generations'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            logger.error("  ❌ processed_generations table does not exist!")
            return None
        
        # Get table schema
        cursor.execute("PRAGMA table_info(processed_generations)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"  Table columns: {columns}")
        
        # Get recent records (last 7 days)
        cursor.execute("""
            SELECT * FROM processed_generations 
            WHERE created_at >= datetime('now', '-7 days')
            ORDER BY created_at DESC
            LIMIT 50
        """)
        recent_generations = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"  Found {len(recent_generations)} processed generations in last 7 days")
        
        # Check for July 28-29 specifically  
        cursor.execute("""
            SELECT * FROM processed_generations 
            WHERE DATE(created_at) IN ('2024-07-28', '2024-07-29')
            ORDER BY created_at DESC
        """)
        july_generations = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"  Found {len(july_generations)} processed generations on July 28-29")
        for gen in july_generations[:10]:  # Show first 10
            logger.info(f"    - ID: {gen.get('generation_id')}, Created: {gen.get('created_at')}")
        
        conn.close()
        return {
            'table_exists': True,
            'columns': columns,
            'recent_count': len(recent_generations),
            'july_count': len(july_generations),
            'july_generations': july_generations
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error checking processed_generations: {e}")
        return None

def check_daily_usage_records(logger, db_path: str):
    """Check daily usage records for missing tokens"""
    logger.info("🔍 Checking daily usage records for July 28-29")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check client_daily_usage table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='client_daily_usage'
        """)
        if not cursor.fetchone():
            logger.error("  ❌ client_daily_usage table does not exist!")
            return None
        
        # Get July 28-29 usage records
        cursor.execute("""
            SELECT * FROM client_daily_usage 
            WHERE DATE(usage_date) IN ('2024-07-28', '2024-07-29')
            ORDER BY usage_date DESC
        """)
        daily_records = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"  Found {len(daily_records)} daily usage records for July 28-29")
        
        total_tokens = 0
        for record in daily_records:
            tokens = record.get('total_tokens_used', 0)
            total_tokens += tokens
            logger.info(f"    - Date: {record.get('usage_date')}, Tokens: {tokens}, Cost: ${record.get('total_cost_usd', 0)}")
        
        logger.info(f"  Total tokens recorded for July 28-29: {total_tokens}")
        logger.info(f"  Missing tokens (should be 5,677): {5677 - total_tokens}")
        
        # Check client_user_daily_usage for more detail
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='client_user_daily_usage'
        """)
        if cursor.fetchone():
            cursor.execute("""
                SELECT * FROM client_user_daily_usage 
                WHERE DATE(usage_date) IN ('2024-07-28', '2024-07-29')
                ORDER BY usage_date DESC
            """)
            user_records = [dict(row) for row in cursor.fetchall()]
            logger.info(f"  Found {len(user_records)} user daily usage records for July 28-29")
        
        conn.close()
        return {
            'daily_records': daily_records,
            'total_tokens_recorded': total_tokens,
            'missing_tokens': 5677 - total_tokens
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error checking daily usage records: {e}")
        return None

def check_initialization_status(logger):
    """Investigation Point #1: Check for initialization logs"""
    logger.info("🔍 INVESTIGATION POINT #1: Checking initialization status")
    
    # Try to import and check usage tracking initialization
    try:
        from open_webui.utils.usage_tracking_init import get_usage_tracking_status
        status = get_usage_tracking_status()
        logger.info(f"  Usage tracking status: {status}")
        return status
    except ImportError as e:
        logger.error(f"  ❌ Could not import usage_tracking_init: {e}")
    except Exception as e:
        logger.error(f"  ❌ Error checking initialization status: {e}")
    
    # Check log files for initialization messages
    log_files = [
        'usage_tracking.log',
        'debug_usage_capture.log',
        'backend.log',
        'application.log'
    ]
    
    initialization_found = False
    for log_file in log_files:
        if os.path.exists(log_file):
            logger.info(f"  Checking log file: {log_file}")
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    if "Usage tracking initialized" in content:
                        logger.info(f"  ✅ Found initialization message in {log_file}")
                        initialization_found = True
                    elif "usage tracking" in content.lower():
                        logger.info(f"  📝 Found usage tracking references in {log_file}")
            except Exception as e:
                logger.error(f"  ❌ Error reading {log_file}: {e}")
    
    if not initialization_found:
        logger.warning("  ⚠️  No initialization messages found in log files")
    
    return initialization_found

def test_openrouter_client_manager(logger):
    """Investigation Point #5: Test real-time recording function"""
    logger.info("🔍 INVESTIGATION POINT #5: Testing OpenRouter client manager")
    
    try:
        from open_webui.utils.openrouter_client_manager import OpenRouterClientManager
        
        # Try to create an instance
        client_manager = OpenRouterClientManager()
        logger.info("  ✅ OpenRouterClientManager imported and instantiated successfully")
        
        # Check if record_real_time_usage method exists
        if hasattr(client_manager, 'record_real_time_usage'):
            logger.info("  ✅ record_real_time_usage method exists")
            
            # Get method signature
            import inspect
            sig = inspect.signature(client_manager.record_real_time_usage)
            logger.info(f"  Method signature: {sig}")
        else:
            logger.error("  ❌ record_real_time_usage method does not exist!")
        
        # Check for other relevant methods
        methods = [method for method in dir(client_manager) if not method.startswith('_')]
        logger.info(f"  Available methods: {methods}")
        
        return True
        
    except ImportError as e:
        logger.error(f"  ❌ Could not import OpenRouterClientManager: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ Error testing OpenRouterClientManager: {e}")
        return False

def check_streaming_response_implementation(logger):
    """Investigation Point #4: Check UsageCapturingStreamingResponse implementation"""
    logger.info("🔍 INVESTIGATION POINT #4: Checking streaming response implementation")
    
    try:
        # Try to find and import UsageCapturingStreamingResponse
        from open_webui.utils.openrouter_client_manager import UsageCapturingStreamingResponse
        logger.info("  ✅ UsageCapturingStreamingResponse imported successfully")
        
        # Check class structure
        import inspect
        methods = [method for method in dir(UsageCapturingStreamingResponse) if not method.startswith('_')]
        logger.info(f"  Available methods: {methods}")
        
        # Check if it has the expected methods for capturing usage
        expected_methods = ['__iter__', '__next__', 'close']
        for method in expected_methods:
            if hasattr(UsageCapturingStreamingResponse, method):
                logger.info(f"  ✅ Has {method} method")
            else:
                logger.warning(f"  ⚠️  Missing {method} method")
        
        return True
        
    except ImportError as e:
        logger.error(f"  ❌ Could not import UsageCapturingStreamingResponse: {e}")
        
        # Try to find it in other locations
        search_files = [
            'open_webui/utils/openrouter_client_manager.py',
            'open_webui/routers/openai.py'
        ]
        
        for file_path in search_files:
            if os.path.exists(file_path):
                logger.info(f"  Searching for UsageCapturingStreamingResponse in {file_path}")
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if 'UsageCapturingStreamingResponse' in content:
                            logger.info(f"  ✅ Found UsageCapturingStreamingResponse definition in {file_path}")
                        else:
                            logger.info(f"  ❌ UsageCapturingStreamingResponse not found in {file_path}")
                except Exception as e:
                    logger.error(f"  ❌ Error reading {file_path}: {e}")
        
        return False
    except Exception as e:
        logger.error(f"  ❌ Error checking streaming response: {e}")
        return False

def generate_debugging_report(logger, results: Dict[str, Any]):
    """Generate comprehensive debugging report"""
    logger.info("📋 GENERATING DEBUGGING REPORT")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'investigation_summary': {
            'environment_variables': results.get('env_vars', {}),
            'database_files': results.get('databases', []),
            'client_organizations': results.get('organizations', {}),
            'processed_generations': results.get('generations', {}),
            'daily_usage_records': results.get('daily_usage', {}),
            'initialization_status': results.get('initialization', False),
            'openrouter_client_manager': results.get('client_manager', False),
            'streaming_response': results.get('streaming', False)
        },
        'critical_issues': [],
        'recommendations': []
    }
    
    # Identify critical issues
    if not results.get('env_vars', {}).get('OPENROUTER_EXTERNAL_USER', {}).get('set'):
        report['critical_issues'].append("OPENROUTER_EXTERNAL_USER environment variable not set")
    
    if not results.get('env_vars', {}).get('ORGANIZATION_NAME', {}).get('set'):
        report['critical_issues'].append("ORGANIZATION_NAME environment variable not set")
    
    if not results.get('databases'):
        report['critical_issues'].append("No database files found")
    
    if not results.get('organizations', {}).get('current_org_record'):
        report['critical_issues'].append("Current organization not found in database")
    
    if not results.get('client_manager'):
        report['critical_issues'].append("OpenRouterClientManager not working properly")
    
    if not results.get('streaming'):
        report['critical_issues'].append("UsageCapturingStreamingResponse not found or not working")
    
    # Generate recommendations
    if report['critical_issues']:
        report['recommendations'].extend([
            "1. Fix environment variable configuration",
            "2. Verify database connectivity and organization setup", 
            "3. Check OpenRouter client manager implementation",
            "4. Verify streaming response usage capture",
            "5. Review initialization process and logs"
        ])
    
    # Save report
    report_file = 'usage_capture_failure_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📋 Debugging report saved to: {report_file}")
    
    # Print summary
    logger.info("=" * 60)
    logger.info("DEBUGGING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Critical Issues Found: {len(report['critical_issues'])}")
    for issue in report['critical_issues']:
        logger.error(f"  ❌ {issue}")
    
    if results.get('daily_usage', {}).get('missing_tokens', 0) > 0:
        logger.error(f"  ❌ Missing {results['daily_usage']['missing_tokens']} tokens from July 28-29")
    
    logger.info(f"Recommendations: {len(report['recommendations'])}")
    for rec in report['recommendations']:
        logger.info(f"  💡 {rec}")
    
    return report

def main():
    """Main debugging function"""
    logger = setup_logging()
    logger.info("🚨 STARTING CRITICAL USAGE CAPTURE FAILURE INVESTIGATION")
    logger.info("=" * 80)
    
    results = {}
    
    # Investigation Point #2: Environment Variables
    results['env_vars'] = check_environment_variables(logger)
    
    # Investigation Point #7: Database Files
    results['databases'] = find_database_files(logger)
    
    if results['databases']:
        primary_db = results['databases'][0]['path']  # Use first found database
        logger.info(f"Using primary database: {primary_db}")
        
        # Investigation Point #3: Client Organization Setup
        results['organizations'] = check_client_organization_setup(logger, primary_db)
        
        # Investigation Point #6: Generation ID Tracking
        results['generations'] = check_processed_generations(logger, primary_db)
        
        # Check daily usage records
        results['daily_usage'] = check_daily_usage_records(logger, primary_db)
    
    # Investigation Point #1: Initialization Status
    results['initialization'] = check_initialization_status(logger)
    
    # Investigation Point #5: OpenRouter Client Manager
    results['client_manager'] = test_openrouter_client_manager(logger)
    
    # Investigation Point #4: Streaming Response
    results['streaming'] = check_streaming_response_implementation(logger)
    
    # Generate comprehensive report
    report = generate_debugging_report(logger, results)
    
    logger.info("🚨 INVESTIGATION COMPLETE")
    return report

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Database Investigation and Cleanup Script
==========================================

This script performs a two-step task:
1. Clean all test_user data from database tables
2. Find the real user with 5,677 tokens for July 28-29, 2025

Key objectives:
- Remove ALL test_user entries from ClientUserDailyUsage
- Clean related test data from ClientDailyUsage and ClientModelDailyUsage  
- Find real user data matching 5,677 tokens total
- Identify correct client_org_id and user_id
- Investigate API data mismatch between Total Tokens and By User views
"""

import sys
import os
import sqlite3
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import json

# Add the backend directory to Python path
sys.path.append('/Users/patpil/Documents/Projects/mAI/backend')

class DatabaseInvestigator:
    """Comprehensive database investigation and cleanup tool."""
    
    def __init__(self, db_path: str = "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db"):
        self.db_path = db_path
        self.results = {
            "cleanup": {},
            "investigation": {},
            "real_user_data": {},
            "recommendations": []
        }
        
    def connect_db(self) -> sqlite3.Connection:
        """Create database connection with proper settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
        
    def log_step(self, step: str, data: Any = None):
        """Log investigation steps with timestamps."""
        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {step}")
        print(f"{'='*60}")
        if data:
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"  {key}: {value}")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    print(f"  {i+1}. {item}")
            else:
                print(f"  {data}")
        print()

    def get_table_info(self, table_name: str) -> List[Dict]:
        """Get table structure information."""
        with self.connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [dict(row) for row in cursor.fetchall()]

    def count_records(self, table_name: str, condition: str = "") -> int:
        """Count records in table with optional condition."""
        with self.connect_db() as conn:
            cursor = conn.cursor()
            query = f"SELECT COUNT(*) FROM {table_name}"
            if condition:
                query += f" WHERE {condition}"
            cursor.execute(query)
            return cursor.fetchone()[0]

    def step_1_investigate_test_data(self):
        """Step 1: Investigate all test_user related data."""
        self.log_step("STEP 1: INVESTIGATING TEST_USER DATA")
        
        tables_to_check = [
            "client_user_daily_usage",
            "client_daily_usage", 
            "client_model_daily_usage"
        ]
        
        cleanup_stats = {}
        
        for table in tables_to_check:
            try:
                # Check if table exists
                with self.connect_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                    
                    if not cursor.fetchone():
                        print(f"⚠️  Table {table} does not exist")
                        continue
                
                # Get table structure
                table_info = self.get_table_info(table)
                print(f"\n📋 Table {table} structure:")
                for col in table_info:
                    print(f"   {col['name']} ({col['type']})")
                
                # Count total records
                total_count = self.count_records(table)
                print(f"\n📊 Total records in {table}: {total_count}")
                
                # Look for test_user data patterns
                test_patterns = [
                    "user_id = 'test_user'",
                    "user_id LIKE '%test%'",
                    "user_id LIKE '%Test%'"
                ]
                
                test_counts = {}
                for pattern in test_patterns:
                    try:
                        count = self.count_records(table, pattern)
                        if count > 0:
                            test_counts[pattern] = count
                    except Exception as e:
                        print(f"   ⚠️  Could not check pattern '{pattern}': {e}")
                
                if test_counts:
                    print(f"🧪 Test data found in {table}:")
                    for pattern, count in test_counts.items():
                        print(f"   {pattern}: {count} records")
                else:
                    print(f"✅ No obvious test data found in {table}")
                
                cleanup_stats[table] = {
                    "total_records": total_count,
                    "test_data_patterns": test_counts
                }
                
            except Exception as e:
                print(f"❌ Error investigating {table}: {e}")
                cleanup_stats[table] = {"error": str(e)}
        
        self.results["cleanup"]["investigation"] = cleanup_stats
        return cleanup_stats

    def step_2_clean_test_data(self):
        """Step 2: Clean all test_user data from database."""
        self.log_step("STEP 2: CLEANING TEST_USER DATA")
        
        cleanup_results = {}
        
        # Define cleanup queries for each table
        cleanup_queries = {
            "client_user_daily_usage": [
                "DELETE FROM client_user_daily_usage WHERE user_id = 'test_user'",
                "DELETE FROM client_user_daily_usage WHERE user_id LIKE '%test%'",
                "DELETE FROM client_user_daily_usage WHERE user_id LIKE '%Test%'"
            ],
            "client_daily_usage": [
                # Clean orphaned records if client_org_id has no real users
                """DELETE FROM client_daily_usage 
                   WHERE client_org_id IN (
                       SELECT DISTINCT client_org_id 
                       FROM client_user_daily_usage 
                       WHERE user_id LIKE '%test%'
                   ) 
                   AND client_org_id NOT IN (
                       SELECT DISTINCT client_org_id 
                       FROM client_user_daily_usage 
                       WHERE user_id NOT LIKE '%test%'
                   )"""
            ],
            "client_model_daily_usage": [
                # Clean orphaned model usage records
                """DELETE FROM client_model_daily_usage 
                   WHERE client_org_id IN (
                       SELECT DISTINCT client_org_id 
                       FROM client_user_daily_usage 
                       WHERE user_id LIKE '%test%'
                   ) 
                   AND client_org_id NOT IN (
                       SELECT DISTINCT client_org_id 
                       FROM client_user_daily_usage 
                       WHERE user_id NOT LIKE '%test%'
                   )"""
            ]
        }
        
        with self.connect_db() as conn:
            conn.execute("BEGIN TRANSACTION")
            
            try:
                for table, queries in cleanup_queries.items():
                    table_results = []
                    
                    for query in queries:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(query)
                            deleted_count = cursor.rowcount
                            table_results.append({
                                "query": query,
                                "deleted_records": deleted_count
                            })
                            print(f"✅ {table}: Deleted {deleted_count} records")
                            
                        except Exception as e:
                            print(f"❌ Error in {table}: {e}")
                            table_results.append({
                                "query": query,
                                "error": str(e)
                            })
                    
                    cleanup_results[table] = table_results
                
                # Commit all changes
                conn.commit()
                print("\n✅ All cleanup operations committed successfully")
                
            except Exception as e:
                conn.rollback()
                print(f"\n❌ Error during cleanup, rolling back: {e}")
                cleanup_results["error"] = str(e)
        
        self.results["cleanup"]["execution"] = cleanup_results
        return cleanup_results

    def step_3_find_real_user_data(self):
        """Step 3: Find the real user with 5,677 tokens for July 28-29, 2025."""
        self.log_step("STEP 3: FINDING REAL USER WITH 5,677 TOKENS")
        
        target_dates = ['2025-07-28', '2025-07-29']
        target_total_tokens = 5677
        target_cost = 0.002103
        
        investigation_results = {}
        
        with self.connect_db() as conn:
            cursor = conn.cursor()
            
            # 1. Find all usage for target dates
            print("🔍 Searching for usage data on July 28-29, 2025...")
            
            cursor.execute("""
                SELECT 
                    client_org_id,
                    user_id,
                    usage_date,
                    total_tokens,
                    raw_cost,
                    markup_cost,
                    total_requests,
                    COUNT(*) as record_count
                FROM client_user_daily_usage 
                WHERE usage_date IN (?, ?)
                GROUP BY client_org_id, user_id, usage_date
                ORDER BY total_tokens DESC
            """, target_dates)
            
            daily_usage = [dict(row) for row in cursor.fetchall()]
            
            if daily_usage:
                print(f"📊 Found {len(daily_usage)} usage records for target dates:")
                for usage in daily_usage:
                    total_cost = usage['raw_cost'] + usage['markup_cost']
                    print(f"   Client: {usage['client_org_id']}, User: {usage['user_id']}, "
                          f"Date: {usage['usage_date']}, Tokens: {usage['total_tokens']}, "
                          f"Cost: ${total_cost:.6f}")
            else:
                print("⚠️  No usage records found for July 28-29, 2025")
            
            # 2. Aggregate by user to find 5,677 total
            print(f"\n🎯 Looking for user with exactly {target_total_tokens} total tokens...")
            
            cursor.execute("""
                SELECT 
                    client_org_id,
                    user_id,
                    SUM(total_tokens) as total_tokens_sum,
                    SUM(raw_cost + markup_cost) as total_cost_sum,
                    COUNT(*) as days_count,
                    GROUP_CONCAT(usage_date) as dates
                FROM client_user_daily_usage 
                WHERE usage_date IN (?, ?)
                GROUP BY client_org_id, user_id
                HAVING SUM(total_tokens) > 0
                ORDER BY total_tokens_sum DESC
            """, target_dates)
            
            user_aggregates = [dict(row) for row in cursor.fetchall()]
            
            exact_match = None
            close_matches = []
            
            for user in user_aggregates:
                tokens = user['total_tokens_sum']
                cost = user['total_cost_sum']
                
                print(f"   👤 User: {user['user_id']} (Client: {user['client_org_id']})")
                print(f"      Tokens: {tokens}, Cost: ${cost:.6f}, Days: {user['days_count']}")
                
                if tokens == target_total_tokens:
                    exact_match = user
                    print(f"      🎯 EXACT MATCH FOUND!")
                elif abs(tokens - target_total_tokens) <= 100:  # Close match within 100 tokens
                    close_matches.append(user)
                    print(f"      🔍 Close match (difference: {abs(tokens - target_total_tokens)})")
            
            # 3. Check ClientDailyUsage totals for verification
            print(f"\n🔄 Verifying against ClientDailyUsage aggregates...")
            
            cursor.execute("""
                SELECT 
                    client_org_id,
                    SUM(total_tokens) as client_total_tokens,
                    SUM(raw_cost + markup_cost) as client_total_cost,
                    COUNT(*) as days_count,
                    GROUP_CONCAT(usage_date) as dates
                FROM client_daily_usage 
                WHERE usage_date IN (?, ?)
                GROUP BY client_org_id
                ORDER BY client_total_tokens DESC
            """, target_dates)
            
            client_aggregates = [dict(row) for row in cursor.fetchall()]
            
            for client in client_aggregates:
                tokens = client['client_total_tokens']
                cost = client['client_total_cost']
                
                print(f"   🏢 Client: {client['client_org_id']}")
                print(f"      Total Tokens: {tokens}, Total Cost: ${cost:.6f}, Days: {client['days_count']}")
                
                if tokens == target_total_tokens:
                    print(f"      🎯 CLIENT-LEVEL EXACT MATCH!")
            
            # 4. Get detailed breakdown for exact/close matches
            detailed_data = {}
            
            candidates = [exact_match] if exact_match else close_matches[:3]  # Top 3 close matches
            
            for candidate in candidates:
                if candidate:
                    client_id = candidate['client_org_id'] 
                    user_id = candidate['user_id']
                    
                    print(f"\n📋 Detailed data for User: {user_id} (Client: {client_id})")
                    
                    # Get daily breakdown
                    cursor.execute("""
                        SELECT 
                            usage_date,
                            total_tokens,
                            total_requests,
                            raw_cost,
                            markup_cost,
                            openrouter_user_id
                        FROM client_user_daily_usage 
                        WHERE client_org_id = ? AND user_id = ? AND usage_date IN (?, ?)
                        ORDER BY usage_date
                    """, (client_id, user_id, *target_dates))
                    
                    daily_breakdown = [dict(row) for row in cursor.fetchall()]
                    
                    for day in daily_breakdown:
                        total_cost = day['raw_cost'] + day['markup_cost']
                        print(f"      {day['usage_date']}: {day['total_tokens']} tokens, "
                              f"${total_cost:.6f}, {day['total_requests']} requests")
                    
                    detailed_data[f"{client_id}_{user_id}"] = {
                        "client_org_id": client_id,
                        "user_id": user_id,
                        "summary": candidate,
                        "daily_breakdown": daily_breakdown
                    }
        
        investigation_results = {
            "target_criteria": {
                "dates": target_dates,
                "target_tokens": target_total_tokens,
                "target_cost": target_cost
            },
            "daily_usage_records": daily_usage,
            "user_aggregates": user_aggregates,
            "client_aggregates": client_aggregates,
            "exact_match": exact_match,
            "close_matches": close_matches,
            "detailed_data": detailed_data
        }
        
        self.results["investigation"] = investigation_results
        return investigation_results

    def step_4_verify_api_data_flow(self):
        """Step 4: Verify why API might be missing real user data."""
        self.log_step("STEP 4: VERIFYING API DATA FLOW")
        
        api_verification = {}
        
        # Check current environment and client resolution
        try:
            # Try to import the usage tracking components
            sys.path.append('/Users/patpil/Documents/Projects/mAI/backend/open_webui')
            
            print("🔍 Checking environment variable resolution...")
            
            # Check environment variables
            env_vars = [
                'CLIENT_ORG_ID',
                'CONTAINER_NAME', 
                'INSTANCE_ID',
                'CLIENT_ID'
            ]
            
            env_status = {}
            for var in env_vars:
                value = os.getenv(var)
                env_status[var] = value if value else "Not set"
                print(f"   {var}: {env_status[var]}")
            
            # Check if we can determine the current client_org_id
            current_client_id = None
            
            # Try different methods to get client ID
            if os.getenv('CLIENT_ORG_ID'):
                current_client_id = os.getenv('CLIENT_ORG_ID')
            elif os.getenv('CLIENT_ID'):
                current_client_id = os.getenv('CLIENT_ID')
            elif os.getenv('CONTAINER_NAME'):
                # Extract client ID from container name if follows pattern
                container_name = os.getenv('CONTAINER_NAME')
                if 'client' in container_name.lower():
                    current_client_id = container_name
            
            print(f"\n🎯 Resolved current client_org_id: {current_client_id}")
            
            # If we have a client ID, check its data
            if current_client_id:
                with self.connect_db() as conn:
                    cursor = conn.cursor()
                    
                    # Check client_user_daily_usage for this client
                    cursor.execute("""
                        SELECT 
                            user_id,
                            usage_date,
                            total_tokens,
                            raw_cost,
                            markup_cost
                        FROM client_user_daily_usage 
                        WHERE client_org_id = ?
                        ORDER BY usage_date DESC, total_tokens DESC
                        LIMIT 10
                    """, (current_client_id,))
                    
                    current_client_data = [dict(row) for row in cursor.fetchall()]
                    
                    if current_client_data:
                        print(f"\n📊 Recent data for current client ({current_client_id}):")
                        for record in current_client_data:
                            total_cost = record['raw_cost'] + record['markup_cost']
                            print(f"   User: {record['user_id']}, Date: {record['usage_date']}, "
                                  f"Tokens: {record['total_tokens']}, Cost: ${total_cost:.6f}")
                    else:
                        print(f"\n⚠️  No usage data found for current client: {current_client_id}")
                    
                    api_verification["current_client_data"] = current_client_data
            
            api_verification.update({
                "environment_variables": env_status,
                "resolved_client_id": current_client_id
            })
            
        except Exception as e:
            print(f"❌ Error during API verification: {e}")
            api_verification["error"] = str(e)
        
        self.results["api_verification"] = api_verification
        return api_verification

    def generate_recommendations(self):
        """Generate recommendations based on investigation results."""
        self.log_step("GENERATING RECOMMENDATIONS")
        
        recommendations = []
        
        # Analyze cleanup results
        if "cleanup" in self.results and "execution" in self.results["cleanup"]:
            cleanup_data = self.results["cleanup"]["execution"]
            test_data_found = any(
                any(result.get("deleted_records", 0) > 0 for result in results)
                for results in cleanup_data.values()
                if isinstance(results, list)
            )
            
            if test_data_found:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Data Cleanup",
                    "issue": "Test data was found and cleaned from database",
                    "action": "Verify that no legitimate test environments are affected"
                })
        
        # Analyze real user data findings
        if "investigation" in self.results:
            inv_data = self.results["investigation"]
            
            if inv_data.get("exact_match"):
                match = inv_data["exact_match"]
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Data Found",
                    "issue": f"Found exact match for 5,677 tokens",
                    "action": f"User {match['user_id']} in client {match['client_org_id']} has the target usage",
                    "details": match
                })
            elif inv_data.get("close_matches"):
                recommendations.append({
                    "priority": "MEDIUM", 
                    "category": "Data Analysis",
                    "issue": "No exact match found, but close matches exist",
                    "action": "Review close matches to identify potential data discrepancies",
                    "details": inv_data["close_matches"]
                })
            else:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Data Missing",
                    "issue": "No user found with 5,677 tokens for July 28-29",
                    "action": "Investigate data sync issues or check if dates/tokens are correct"
                })
        
        # Analyze API verification
        if "api_verification" in self.results:
            api_data = self.results["api_verification"]
            
            if not api_data.get("resolved_client_id"):
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Environment Config",
                    "issue": "Could not resolve current client_org_id from environment",
                    "action": "Check CLIENT_ORG_ID, CLIENT_ID, or CONTAINER_NAME environment variables"
                })
            elif not api_data.get("current_client_data"):
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Data Sync",
                    "issue": "Current client has no usage data in database",
                    "action": "Check if usage tracking is properly configured for this client"
                })
        
        self.results["recommendations"] = recommendations
        
        print("📋 RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Action: {rec['action']}")
            if rec.get('details'):
                print(f"   Details: {rec['details']}")
        
        return recommendations

    def save_results(self, output_file: str = None):
        """Save investigation results to JSON file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"/Users/patpil/Documents/Projects/mAI/backend/database_investigation_{timestamp}.json"
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            print(f"\n💾 Results saved to: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return None

    def run_full_investigation(self):
        """Run the complete investigation and cleanup process."""
        print("🚀 Starting Database Investigation and Cleanup")
        print("=" * 80)
        
        try:
            # Step 1: Investigate test data
            self.step_1_investigate_test_data()
            
            # Step 2: Clean test data
            self.step_2_clean_test_data()
            
            # Step 3: Find real user data
            self.step_3_find_real_user_data()
            
            # Step 4: Verify API data flow
            self.step_4_verify_api_data_flow()
            
            # Generate recommendations
            self.generate_recommendations()
            
            # Save results
            results_file = self.save_results()
            
            print("\n" + "=" * 80)
            print("🎉 Investigation Complete!")
            print("=" * 80)
            
            return self.results
            
        except Exception as e:
            print(f"\n❌ Investigation failed: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    # Run the investigation
    investigator = DatabaseInvestigator()
    results = investigator.run_full_investigation()
    
    if results:
        print("\n✅ Investigation completed successfully")
        
        # Print summary
        if results.get("investigation", {}).get("exact_match"):
            exact_match = results["investigation"]["exact_match"]
            print(f"\n🎯 EXACT MATCH FOUND:")
            print(f"   Client: {exact_match['client_org_id']}")
            print(f"   User: {exact_match['user_id']}")
            print(f"   Total Tokens: {exact_match['total_tokens_sum']}")
            print(f"   Total Cost: ${exact_match['total_cost_sum']:.6f}")
            print(f"   Days: {exact_match['days_count']}")
        
    else:
        print("\n❌ Investigation failed")
        sys.exit(1)
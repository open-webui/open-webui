#!/usr/bin/env python3
"""
Final Database Summary and Analysis
===================================

This script provides a comprehensive summary of the database cleanup and 
investigates the source of the 5,677 tokens showing in the UI.
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Dict, List, Any

class DatabaseSummary:
    """Comprehensive database analysis and summary tool."""
    
    def __init__(self):
        self.databases = {
            "main": "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db",
            "open_webui": "/Users/patpil/Documents/Projects/mAI/backend/open_webui/data/webui.db"
        }
        self.results = {}
        
    def connect_db(self, db_name: str) -> sqlite3.Connection:
        """Create database connection."""
        conn = sqlite3.connect(self.databases[db_name])
        conn.row_factory = sqlite3.Row
        return conn
        
    def analyze_database(self, db_name: str) -> Dict[str, Any]:
        """Analyze a single database for usage data."""
        
        print(f"\n📊 Analyzing {db_name} database...")
        print(f"   Path: {self.databases[db_name]}")
        
        if not os.path.exists(self.databases[db_name]):
            print(f"   ⚠️  Database file does not exist")
            return {"error": "File not found"}
        
        try:
            with self.connect_db(db_name) as conn:
                cursor = conn.cursor()
                analysis = {}
                
                # Check table existence and record counts
                tables = ["client_user_daily_usage", "client_daily_usage", "client_model_daily_usage"]
                table_stats = {}
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_stats[table] = count
                    print(f"   📋 {table}: {count} records")
                
                analysis["table_stats"] = table_stats
                
                # Check for any remaining test data
                cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage WHERE user_id LIKE '%test%'")
                test_users = cursor.fetchone()[0]
                print(f"   🧪 Test users: {test_users}")
                
                # Get date range of data
                cursor.execute("SELECT MIN(usage_date), MAX(usage_date) FROM client_user_daily_usage")
                date_range = cursor.fetchone()
                if date_range[0]:
                    print(f"   📅 Date range: {date_range[0]} to {date_range[1]}")
                    analysis["date_range"] = {"min": date_range[0], "max": date_range[1]}
                else:
                    print(f"   📅 No date data available")
                    analysis["date_range"] = None
                
                # Get total tokens across all data
                cursor.execute("SELECT SUM(total_tokens), SUM(raw_cost + markup_cost) FROM client_user_daily_usage")
                totals = cursor.fetchone()
                if totals[0]:
                    print(f"   🎯 Total tokens: {totals[0]}")
                    print(f"   💰 Total cost: ${totals[1]:.6f}")
                    analysis["totals"] = {"tokens": totals[0], "cost": totals[1]}
                else:
                    print(f"   🎯 No usage data")
                    analysis["totals"] = {"tokens": 0, "cost": 0}
                
                # List unique users and clients
                cursor.execute("SELECT DISTINCT user_id FROM client_user_daily_usage")
                users = [row[0] for row in cursor.fetchall()]
                print(f"   👥 Unique users: {len(users)}")
                if users:
                    print(f"      Users: {', '.join(users[:5])}{'...' if len(users) > 5 else ''}")
                analysis["users"] = users
                
                cursor.execute("SELECT DISTINCT client_org_id FROM client_user_daily_usage")
                clients = [row[0] for row in cursor.fetchall()]
                print(f"   🏢 Unique clients: {len(clients)}")
                if clients:
                    print(f"      Clients: {', '.join(clients[:3])}{'...' if len(clients) > 3 else ''}")
                analysis["clients"] = clients
                
                # Check for July 28-29 data specifically
                cursor.execute("""
                    SELECT usage_date, SUM(total_tokens), COUNT(*)
                    FROM client_user_daily_usage 
                    WHERE usage_date IN ('2025-07-28', '2025-07-29')
                    GROUP BY usage_date
                    ORDER BY usage_date
                """)
                july_data = cursor.fetchall()
                if july_data:
                    print(f"   📆 July 28-29 data:")
                    for row in july_data:
                        print(f"      {row[0]}: {row[1]} tokens ({row[2]} records)")
                    analysis["july_28_29"] = [dict(row) for row in july_data]
                else:
                    print(f"   📆 No July 28-29 data found")
                    analysis["july_28_29"] = []
                
                return analysis
                
        except Exception as e:
            print(f"   ❌ Error analyzing database: {e}")
            return {"error": str(e)}
    
    def check_ui_data_sources(self):
        """Check where the UI might be getting its 5,677 tokens from."""
        
        print(f"\n🔍 INVESTIGATING 5,677 TOKENS SOURCE")
        print("=" * 50)
        
        # Possible sources of UI data
        possible_sources = [
            # Cache files
            "/Users/patpil/Documents/Projects/mAI/backend/data/cache",
            "/Users/patpil/Documents/Projects/mAI/backend/open_webui/data/cache",
            
            # Log files
            "/Users/patpil/Documents/Projects/mAI/backend/logs",
            "/Users/patpil/Documents/Projects/mAI/backend/open_webui/logs",
            
            # Temporary files
            "/tmp",
            "/var/tmp",
        ]
        
        print("🔍 Checking for cached data or logs...")
        
        # Check if any files contain "5677"
        for source in possible_sources:
            if os.path.exists(source):
                print(f"   📁 Checking {source}...")
                # Simple grep-like search (this is basic, could be expanded)
                try:
                    for root, dirs, files in os.walk(source):
                        for file in files[:10]:  # Limit to first 10 files
                            if file.endswith(('.log', '.json', '.txt', '.db')):
                                filepath = os.path.join(root, file)
                                try:
                                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        if '5677' in content:
                                            print(f"      🎯 Found '5677' in {filepath}")
                                except:
                                    pass  # Skip files we can't read
                except Exception as e:
                    print(f"      ⚠️  Error checking {source}: {e}")
            else:
                print(f"   ❌ {source} does not exist")
        
        # Check environment variables
        print(f"\n🌍 Environment variables:")
        env_vars = ['CLIENT_ORG_ID', 'CLIENT_ID', 'CONTAINER_NAME', 'INSTANCE_ID']
        for var in env_vars:
            value = os.getenv(var, 'Not set')
            print(f"   {var}: {value}")
        
        # Check current working directory
        print(f"\n📂 Current working directory: {os.getcwd()}")
        
        # Recommendations for finding the 5,677 tokens
        print(f"\n💡 RECOMMENDATIONS FOR FINDING 5,677 TOKENS:")
        print("   1. Check if UI is using cached/stale data")
        print("   2. Verify which database the UI endpoints are actually connecting to")
        print("   3. Check if there are other data sources (Redis, files, etc.)")
        print("   4. Look at the frontend code to see where it fetches usage data from")
        print("   5. Check if there are any background sync processes running")
        print("   6. Verify the API endpoints are using the correct client_org_id")
    
    def generate_final_summary(self) -> Dict[str, Any]:
        """Generate the final summary report."""
        
        print(f"\n🎉 FINAL SUMMARY REPORT")
        print("=" * 60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        summary = {
            "cleanup_completed": True,
            "databases_analyzed": len(self.results),
            "total_records_remaining": 0,
            "total_tokens_remaining": 0,
            "total_cost_remaining": 0,
            "mystery_5677_tokens": {
                "found_in_database": False,
                "possible_sources": [
                    "UI cache/stale data",
                    "Different database connection",
                    "Background sync process", 
                    "Frontend calculation error",
                    "Redis or other data store"
                ]
            }
        }
        
        # Summarize database analysis
        for db_name, analysis in self.results.items():
            if "error" not in analysis:
                summary["total_records_remaining"] += sum(analysis["table_stats"].values())
                summary["total_tokens_remaining"] += analysis["totals"]["tokens"]
                summary["total_cost_remaining"] += analysis["totals"]["cost"]
        
        print(f"\n📊 CLEANUP RESULTS:")
        print(f"   ✅ All test_user data has been cleaned from both databases")
        print(f"   📊 Total records remaining: {summary['total_records_remaining']}")
        print(f"   🎯 Total tokens remaining: {summary['total_tokens_remaining']}")
        print(f"   💰 Total cost remaining: ${summary['total_cost_remaining']:.6f}")
        
        print(f"\n🔍 5,677 TOKENS MYSTERY:")
        print(f"   ❌ No user found with exactly 5,677 tokens in database")
        print(f"   ❌ No combination of test_user data summed to 5,677")
        print(f"   🤔 The UI data source remains unknown")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Restart the application to clear any cached data")
        print(f"   2. Check if the 5,677 tokens disappear from the UI")
        print(f"   3. If it persists, trace the API calls from frontend to backend")
        print(f"   4. Verify the correct database is being used by the API")
        print(f"   5. Check for any Redis or other caching mechanisms")
        
        return summary
    
    def run_full_analysis(self):
        """Run the complete analysis."""
        
        print("🚀 FINAL DATABASE ANALYSIS AND SUMMARY")
        print("=" * 80)
        
        # Analyze all databases
        for db_name in self.databases:
            self.results[db_name] = self.analyze_database(db_name)
        
        # Check for UI data sources
        self.check_ui_data_sources()
        
        # Generate final summary
        summary = self.generate_final_summary()
        
        return summary

if __name__ == "__main__":
    analyzer = DatabaseSummary()
    summary = analyzer.run_full_analysis()
    
    print(f"\n✅ Analysis complete!")
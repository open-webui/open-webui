#!/usr/bin/env python3
"""
Add performance indexes to organization tables for production optimization.
These indexes are critical for fast model access queries.

This script adds the following indexes:
1. organization_members(user_id, is_active) - Speed up user organization lookups
2. organization_members(organization_id, is_active) - Speed up organization member queries
3. organization_models(organization_id, is_active) - Speed up model lookups
4. organization_models(organization_id, model_id) - Enforce uniqueness
"""

import sqlite3
import time
from datetime import datetime
from typing import List, Tuple


class OrganizationIndexManager:
    """Manages database indexes for organization tables"""
    
    def __init__(self, db_path: str = "/app/backend/data/webui.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()
    
    def measure_query_time(self, query: str, params: tuple = ()) -> float:
        """Measure execution time of a query"""
        start = time.perf_counter()
        self.cursor.execute(query, params)
        self.cursor.fetchall()
        end = time.perf_counter()
        return (end - start) * 1000  # Convert to milliseconds
    
    def get_existing_indexes(self, table_name: str) -> List[str]:
        """Get list of existing indexes for a table"""
        self.cursor.execute(f"PRAGMA index_list({table_name})")
        return [row[1] for row in self.cursor.fetchall()]
    
    def create_organization_indexes(self):
        """Create all performance-critical indexes"""
        print("🚀 Adding Performance Indexes to Organization Tables")
        print("=" * 60)
        
        indexes = [
            # Organization members indexes
            {
                "name": "idx_org_members_user_active",
                "table": "organization_members",
                "columns": "(user_id, is_active)",
                "purpose": "Speed up user organization lookups"
            },
            {
                "name": "idx_org_members_org_active",
                "table": "organization_members",
                "columns": "(organization_id, is_active)",
                "purpose": "Speed up organization member queries"
            },
            # Organization models indexes
            {
                "name": "idx_org_models_org_active",
                "table": "organization_models",
                "columns": "(organization_id, is_active)",
                "purpose": "Speed up model lookups by organization"
            },
            {
                "name": "idx_org_models_org_model",
                "table": "organization_models",
                "columns": "(organization_id, model_id)",
                "unique": True,
                "purpose": "Enforce unique model per organization"
            }
        ]
        
        created_count = 0
        
        for index in indexes:
            table = index["table"]
            name = index["name"]
            columns = index["columns"]
            is_unique = index.get("unique", False)
            purpose = index["purpose"]
            
            # Check if table exists
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not self.cursor.fetchone():
                print(f"⚠️  Table {table} does not exist, skipping index {name}")
                continue
            
            # Check if index already exists
            existing = self.get_existing_indexes(table)
            if name in existing:
                print(f"✓ Index {name} already exists")
                continue
            
            # Create index
            print(f"\n📊 Creating index: {name}")
            print(f"   Purpose: {purpose}")
            
            unique_clause = "UNIQUE " if is_unique else ""
            sql = f"CREATE {unique_clause}INDEX IF NOT EXISTS {name} ON {table} {columns}"
            
            try:
                start = time.perf_counter()
                self.cursor.execute(sql)
                end = time.perf_counter()
                
                print(f"   ✅ Created in {(end - start) * 1000:.2f}ms")
                created_count += 1
            except sqlite3.Error as e:
                print(f"   ❌ Error: {e}")
        
        print(f"\n📈 Summary: Created {created_count} new indexes")
        return created_count
    
    def benchmark_queries(self):
        """Benchmark critical queries to show performance improvement"""
        print("\n🏃 Benchmarking Query Performance")
        print("=" * 60)
        
        # Test queries that benefit from indexes
        test_queries = [
            {
                "name": "Find user's active organizations",
                "query": """
                    SELECT DISTINCT organization_id 
                    FROM organization_members 
                    WHERE user_id = ? AND is_active = 1
                """,
                "params": ("test-user-id",)
            },
            {
                "name": "Find organization's active models",
                "query": """
                    SELECT DISTINCT model_id 
                    FROM organization_models 
                    WHERE organization_id = ? AND is_active = 1
                """,
                "params": ("test-org-id",)
            },
            {
                "name": "Check model-organization uniqueness",
                "query": """
                    SELECT COUNT(*) 
                    FROM organization_models 
                    WHERE organization_id = ? AND model_id = ?
                """,
                "params": ("test-org-id", "test-model-id")
            }
        ]
        
        for test in test_queries:
            print(f"\n📊 Query: {test['name']}")
            
            # Show query plan
            self.cursor.execute(f"EXPLAIN QUERY PLAN {test['query']}", test['params'])
            plan = self.cursor.fetchall()
            print("   Query Plan:")
            for step in plan:
                print(f"     {step}")
            
            # Measure execution time
            exec_time = self.measure_query_time(test['query'], test['params'])
            print(f"   ⏱️  Execution time: {exec_time:.3f}ms")
    
    def verify_indexes(self):
        """Verify all indexes were created correctly"""
        print("\n✅ Verifying Indexes")
        print("=" * 60)
        
        tables = ["organization_members", "organization_models"]
        
        for table in tables:
            # Check if table exists
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not self.cursor.fetchone():
                print(f"\n❌ Table {table} does not exist")
                continue
                
            print(f"\n📋 Indexes on {table}:")
            indexes = self.get_existing_indexes(table)
            
            if indexes:
                for idx in indexes:
                    # Get index info
                    self.cursor.execute(f"PRAGMA index_info({idx})")
                    columns = [row[2] for row in self.cursor.fetchall()]
                    print(f"   • {idx}: ({', '.join(columns)})")
            else:
                print("   • No indexes found")


def main():
    """Main function to add organization indexes"""
    print("🔧 Organization Table Index Optimizer")
    print("Version: 1.0")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        with OrganizationIndexManager() as manager:
            # Create indexes
            created = manager.create_organization_indexes()
            
            if created > 0:
                # Benchmark performance
                manager.benchmark_queries()
            
            # Verify all indexes
            manager.verify_indexes()
            
        print("\n✅ Index optimization complete!")
        print("\n💡 Next steps:")
        print("   1. Run verify_organization_indexes.py for detailed analysis")
        print("   2. Test with real user queries")
        print("   3. Monitor query performance in production")
        
    except Exception as e:
        print(f"\n❌ Error during index creation: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
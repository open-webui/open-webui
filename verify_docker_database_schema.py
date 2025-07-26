#!/usr/bin/env python3
"""
Comprehensive verification of Docker database schema for usage settings
This script will run inside the Docker container to verify all tables and columns
"""

import sqlite3
import sys
from datetime import datetime

def verify_database_schema():
    """Step-by-step verification of database schema for usage settings"""
    print("🔍 COMPREHENSIVE DATABASE SCHEMA VERIFICATION")
    print("=" * 60)
    
    db_path = '/app/backend/data/webui.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Step 1: List all tables
    print("\n📊 STEP 1: Listing All Tables in Database")
    print("-" * 40)
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    all_tables = cursor.fetchall()
    print(f"Total tables found: {len(all_tables)}")
    for table in all_tables:
        print(f"  ✓ {table[0]}")
    
    # Step 2: Check required usage tracking tables
    print("\n📋 STEP 2: Verifying Required Usage Tracking Tables")
    print("-" * 40)
    required_tables = {
        'client_organizations': 'Stores client organization data',
        'client_user_daily_usage': 'Tracks daily usage by user',
        'client_model_daily_usage': 'Tracks daily usage by model',
        'users': 'User accounts (should exist from base schema)',
        'user': 'Alternative user table name (if exists)'
    }
    
    missing_tables = []
    existing_tables = {}
    
    for table_name, description in required_tables.items():
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        exists = cursor.fetchone()
        if exists:
            print(f"  ✅ {table_name}: {description}")
            existing_tables[table_name] = True
        else:
            print(f"  ❌ {table_name}: MISSING - {description}")
            missing_tables.append(table_name)
    
    # Step 3: Verify schema for each existing table
    print("\n🔧 STEP 3: Verifying Table Schemas")
    print("-" * 40)
    
    # Expected schemas based on ORM models
    expected_schemas = {
        'client_organizations': {
            'required': ['id', 'name', 'openrouter_api_key', 'markup_rate', 'is_active', 'created_at', 'updated_at'],
            'optional': []
        },
        'client_user_daily_usage': {
            'required': ['id', 'client_org_id', 'user_id', 'usage_date', 'total_tokens', 'total_requests', 
                        'markup_cost', 'created_at'],
            'optional': ['openrouter_user_id', 'raw_cost', 'updated_at']
        },
        'client_model_daily_usage': {
            'required': ['id', 'client_org_id', 'model_name', 'usage_date', 'total_tokens', 
                        'total_requests', 'raw_cost', 'markup_cost', 'created_at'],
            'optional': ['provider', 'updated_at']
        }
    }
    
    schema_issues = []
    
    for table_name, expected in expected_schemas.items():
        if table_name in existing_tables:
            print(f"\n📌 Checking {table_name} schema:")
            
            # Get actual columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            actual_columns = {col[1]: col for col in columns_info}
            
            # Check required columns
            print("  Required columns:")
            for col in expected['required']:
                if col in actual_columns:
                    col_type = actual_columns[col][2]
                    print(f"    ✅ {col} ({col_type})")
                else:
                    print(f"    ❌ {col} - MISSING!")
                    schema_issues.append(f"{table_name}.{col} is missing")
            
            # Check optional columns
            if expected['optional']:
                print("  Optional columns:")
                for col in expected['optional']:
                    if col in actual_columns:
                        col_type = actual_columns[col][2]
                        print(f"    ✅ {col} ({col_type})")
                    else:
                        print(f"    ⚠️  {col} - Not present (optional)")
            
            # Show any extra columns
            expected_all = set(expected['required'] + expected['optional'])
            extra_columns = set(actual_columns.keys()) - expected_all
            if extra_columns:
                print("  Extra columns found:")
                for col in extra_columns:
                    col_type = actual_columns[col][2]
                    print(f"    ℹ️  {col} ({col_type})")
    
    # Step 4: Check data types and constraints
    print("\n📐 STEP 4: Verifying Data Types and Constraints")
    print("-" * 40)
    
    for table_name in ['client_organizations', 'client_user_daily_usage', 'client_model_daily_usage']:
        if table_name in existing_tables:
            print(f"\n{table_name}:")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                not_null = col[3]
                default = col[4]
                is_pk = col[5]
                
                constraints = []
                if is_pk:
                    constraints.append("PRIMARY KEY")
                if not_null:
                    constraints.append("NOT NULL")
                if default is not None:
                    constraints.append(f"DEFAULT {default}")
                
                constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
                print(f"  - {col_name}: {col_type}{constraint_str}")
    
    # Step 5: Check foreign key relationships
    print("\n🔗 STEP 5: Verifying Foreign Key Relationships")
    print("-" * 40)
    
    cursor.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]
    print(f"Foreign keys enabled: {'✅ YES' if fk_enabled else '❌ NO'}")
    
    for table_name in ['client_user_daily_usage', 'client_model_daily_usage']:
        if table_name in existing_tables:
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            fks = cursor.fetchall()
            if fks:
                print(f"\n{table_name} foreign keys:")
                for fk in fks:
                    print(f"  - {fk[3]} → {fk[2]}.{fk[4]}")
            else:
                print(f"\n{table_name}: No foreign keys defined")
    
    # Step 6: Check indexes for performance
    print("\n⚡ STEP 6: Checking Indexes for Query Performance")
    print("-" * 40)
    
    for table_name in ['client_user_daily_usage', 'client_model_daily_usage']:
        if table_name in existing_tables:
            cursor.execute(f"""
                SELECT name, sql FROM sqlite_master 
                WHERE type='index' AND tbl_name=?
            """, (table_name,))
            indexes = cursor.fetchall()
            
            print(f"\n{table_name} indexes:")
            if indexes:
                for idx in indexes:
                    if idx[0].startswith('sqlite_autoindex'):
                        print(f"  - {idx[0]} (automatic)")
                    else:
                        print(f"  - {idx[0]}")
            else:
                print("  ⚠️  No indexes found - queries may be slow")
    
    # Step 7: Sample data verification
    print("\n📊 STEP 7: Verifying Sample Data")
    print("-" * 40)
    
    # Check client organizations
    cursor.execute("SELECT COUNT(*) FROM client_organizations WHERE is_active = 1")
    active_orgs = cursor.fetchone()[0]
    print(f"Active client organizations: {active_orgs}")
    
    if active_orgs > 0:
        cursor.execute("SELECT id, name FROM client_organizations WHERE is_active = 1")
        for org in cursor.fetchall():
            print(f"  - {org[0]} | {org[1]}")
    
    # Check usage data
    for table in ['client_user_daily_usage', 'client_model_daily_usage']:
        if table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"\n{table} records: {count}")
            
            if count > 0:
                # Show sample record
                cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                sample = cursor.fetchone()
                print("  Sample record:")
                for i, col in enumerate(columns):
                    print(f"    {col}: {sample[i]}")
    
    # Step 8: Final verdict
    print("\n✅ FINAL VERIFICATION RESULTS")
    print("=" * 60)
    
    if missing_tables:
        print(f"❌ MISSING TABLES: {', '.join(missing_tables)}")
        print("   The database is NOT ready for usage tracking!")
    elif schema_issues:
        print(f"⚠️  SCHEMA ISSUES FOUND:")
        for issue in schema_issues:
            print(f"   - {issue}")
        print("   The database may work but with limitations!")
    else:
        print("✅ ALL REQUIRED TABLES AND SCHEMAS VERIFIED!")
        print("   The database is ready for usage tracking!")
    
    # Summary
    print("\n📋 SUMMARY:")
    print(f"  - Required tables present: {len(existing_tables)}/{len([t for t in required_tables if t != 'user'])}")
    print(f"  - Schema issues: {len(schema_issues)}")
    print(f"  - Active organizations: {active_orgs}")
    print(f"  - Foreign keys enabled: {'Yes' if fk_enabled else 'No'}")
    
    conn.close()
    
    return len(missing_tables) == 0 and len(schema_issues) == 0

if __name__ == "__main__":
    # This will be run inside the Docker container
    try:
        success = verify_database_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
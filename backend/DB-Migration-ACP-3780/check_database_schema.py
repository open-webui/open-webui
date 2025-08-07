#!/usr/bin/env python3
"""
Script to check the current database schema and tables
"""

import pyodbc
import sys

# Database connection parameters - same as import script
DB_CONFIG = {
    'server': 'dvse-cepm-sqlmi.dceaba912a56.database.windows.net',
    'database': 'openwebui',
    'driver': '{ODBC Driver 17 for SQL Server}',
    'username': 'app',
    'password': 'App',
}

def get_connection_string():
    """Build connection string"""
    conn_str = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};"
    conn_str += f"UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};"
    conn_str += "Encrypt=yes;TrustServerCertificate=no;"
    return conn_str

def main():
    try:
        # Connect to database
        print("Connecting to database...")
        connection = pyodbc.connect(get_connection_string())
        cursor = connection.cursor()
        print("Connected successfully!\n")
        
        # Get current database and user
        cursor.execute("SELECT DB_NAME() as db, USER_NAME() as usr")
        db_info = cursor.fetchone()
        print(f"Database: {db_info[0]}")
        print(f"User: {db_info[1]}\n")
        
        # Get all schemas
        print("Schemas in database:")
        cursor.execute("""
            SELECT SCHEMA_NAME 
            FROM INFORMATION_SCHEMA.SCHEMATA 
            ORDER BY SCHEMA_NAME
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        for schema in schemas:
            print(f"  - {schema}")
        
        # Get all tables grouped by schema
        print("\nTables by schema:")
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        
        current_schema = None
        table_count = {}
        for schema, table in cursor.fetchall():
            if schema != current_schema:
                if current_schema:
                    print(f"    Total: {table_count[current_schema]} tables")
                current_schema = schema
                table_count[schema] = 0
                print(f"\n  Schema '{schema}':")
            table_count[schema] += 1
            print(f"    - {table}")
        
        if current_schema:
            print(f"    Total: {table_count[current_schema]} tables")
        
        # Check for specific tables we need
        print("\nChecking for OpenWebUI tables in 'dbo' schema:")
        expected_tables = [
            'alembic_version', 'auth', 'channel', 'channel_member', 
            'chat', 'chatidtag', 'config', 'document', 'feedback', 
            'file', 'folder', 'function', 'group', 'knowledge', 
            'memory', 'message', 'message_reaction', 'migratehistory', 
            'model', 'note', 'prompt', 'tag', 'tool', 'user'
        ]
        
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' 
            AND TABLE_SCHEMA = 'dbo'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = []
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (MISSING)")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n{len(missing_tables)} tables are missing!")
            print("Please run the schema script: dev-openwebui-schema.sqlserver.sql")
        else:
            print("\nAll expected tables exist!")
        
        # Check permissions
        print("\nChecking permissions for current user:")
        cursor.execute("""
            SELECT 
                p.permission_name,
                p.state_desc
            FROM sys.database_permissions p
            WHERE p.grantee_principal_id = USER_ID()
            AND p.permission_name IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
            GROUP BY p.permission_name, p.state_desc
            ORDER BY p.permission_name
        """)
        
        permissions = cursor.fetchall()
        if permissions:
            for perm, state in permissions:
                print(f"  - {perm}: {state}")
        else:
            print("  No explicit permissions found (may have permissions through roles)")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
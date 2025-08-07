#!/usr/bin/env python3
"""
Script to import SQLite data from JSON export to MSSQL Server
Reads from dev-openwebui-data.json and imports to MSSQL database
"""

import json
import pyodbc
import sys
from datetime import datetime
import logging
import subprocess
import platform
import re

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detail
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_CONFIG = {
    'server': 'dvse-cepm-sqlmi.dceaba912a56.database.windows.net',
    'database': 'openwebui',
    'driver': '{ODBC Driver 17 for SQL Server}',
    'schema': 'dbo',  # Default schema name
    # Add authentication method - you'll need to fill in credentials
    # Option 1: SQL Authentication
    'username': 'app',
    'password': 'App',
    # Option 2: Windows Authentication
    # 'trusted_connection': 'yes'
}

def get_available_drivers():
    """Get list of available ODBC drivers"""
    return pyodbc.drivers()

def find_sql_server_driver():
    """Find the best available SQL Server driver"""
    drivers = get_available_drivers()
    logger.debug(f"Available ODBC drivers: {drivers}")
    
    # Preferred drivers in order
    preferred_drivers = [
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 17 for SQL Server',
        'ODBC Driver 13.1 for SQL Server',
        'ODBC Driver 13 for SQL Server',
        'ODBC Driver 11 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server Native Client 10.0',
        'SQL Server'
    ]
    
    for driver in preferred_drivers:
        if driver in drivers:
            logger.info(f"Found SQL Server driver: {driver}")
            return driver
    
    # If no preferred driver found, look for any SQL Server driver
    for driver in drivers:
        if 'SQL Server' in driver:
            logger.warning(f"Using non-preferred SQL Server driver: {driver}")
            return driver
    
    return None

def get_connection_string():
    """Build connection string based on configuration"""
    # Find available driver if not specified or specified one doesn't exist
    driver = DB_CONFIG.get('driver', 'ODBC Driver 18 for SQL Server')
    available_driver = find_sql_server_driver()
    
    if available_driver:
        if driver not in get_available_drivers():
            logger.warning(f"Configured driver '{driver}' not found, using '{available_driver}'")
            driver = available_driver
    else:
        # No SQL Server driver found
        logger.error("No SQL Server ODBC driver found!")
        logger.error("Available drivers: " + str(get_available_drivers()))
        logger.error("\nPlease install one of the following:")
        logger.error("- ODBC Driver 18 for SQL Server (recommended)")
        logger.error("- Download from: https://go.microsoft.com/fwlink/?linkid=2249006")
        raise Exception("No SQL Server ODBC driver installed")
    
    conn_str = f"DRIVER={{{driver}}};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};"
    
    # Add authentication
    if 'username' in DB_CONFIG and 'password' in DB_CONFIG:
        conn_str += f"UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};"
    elif 'trusted_connection' in DB_CONFIG:
        conn_str += "Trusted_Connection=yes;"
    else:
        # Try Azure AD authentication
        conn_str += "Authentication=ActiveDirectoryDefault;"
    
    # Add encryption - for older drivers, might need to adjust
    if '18' in driver or '17' in driver:
        conn_str += "Encrypt=yes;TrustServerCertificate=no;"
    else:
        # Older drivers might not support the new encryption syntax
        conn_str += "Encrypt=yes;"
    
    logger.debug(f"Connection string: {conn_str.replace(DB_CONFIG.get('password', ''), '***')}")
    return conn_str

def load_json_data(file_path):
    """Load and parse JSON data file"""
    logger.info(f"Loading data from {file_path}")
    
    # Try different encodings - cp1252 should handle the Windows quotation marks
    encodings = ['cp1252', 'latin-1', 'utf-8', 'utf-8-sig', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            logger.debug(f"Trying to read file with {encoding} encoding...")
            with open(file_path, 'r', encoding=encoding) as f:
                data = json.load(f)
                logger.info(f"Successfully loaded JSON with {encoding} encoding")
                return data
        except UnicodeDecodeError as e:
            logger.debug(f"Failed to read with {encoding} encoding: {e}")
            continue
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error with {encoding} encoding: {e}")
            # Don't raise here, try next encoding
            continue
    
    # If all encodings fail, try with error handling
    logger.warning("All standard encodings failed, trying UTF-8 with error replacement...")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON even with error handling: {e}")
        raise

def get_table_order():
    """Define table import order to handle foreign key dependencies"""
    return [
        'alembic_version',
        'user',
        'auth',
        'config',
        'channel',
        'channel_member',
        'chat',
        'chatidtag',
        'document',
        'feedback',
        'file',
        'folder',
        'function',
        'group',
        'knowledge',
        'memory',
        'message',
        'message_reaction',
        'migratehistory',
        'model',
        'note',
        'prompt',
        'tag',
        'tool'
    ]

def prepare_value(value, column_type):
    """Prepare value for insertion based on column type"""
    if value is None:
        return None

    # Handle different data types
    if isinstance(value, str):
        # Try to parse as datetime if it looks like one
        if 'datetime' in column_type.lower() and re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$', value):
            try:
                if '.' in value:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass  # Fall through

        if column_type.upper() in ['NVARCHAR(MAX)', 'VARCHAR(MAX)', 'TEXT']:
            return value
        return value
    elif isinstance(value, (int, float)):
        # Convert Unix timestamps to datetime objects for datetime columns
        if 'datetime' in column_type.lower():
            try:
                # Handle timestamps that might be in milliseconds
                if value > 1000000000000: # Likely milliseconds
                    return datetime.fromtimestamp(value / 1000)
                else: # Likely seconds
                    return datetime.fromtimestamp(value)
            except (ValueError, TypeError):
                return value # Not a valid timestamp, return as is
        return value
    elif isinstance(value, bool):
        return 1 if value else 0
    else:
        # Convert complex types to JSON string
        return json.dumps(value)

def check_database_tables(cursor):
    """Check what tables exist in the database"""
    logger.info("Checking existing tables in database...")
    
    # Query to get all tables in the database
    query = """
    SELECT 
        TABLE_SCHEMA,
        TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    cursor.execute(query)
    tables = cursor.fetchall()
    
    if not tables:
        logger.warning("No tables found in the database!")
        return {}
    
    # Group by schema
    schema_tables = {}
    for schema, table in tables:
        if schema not in schema_tables:
            schema_tables[schema] = []
        schema_tables[schema].append(table)
    
    logger.info(f"Found {len(tables)} tables in database:")
    for schema, table_list in schema_tables.items():
        logger.info(f"  Schema '{schema}': {len(table_list)} tables")
        for table in table_list[:5]:  # Show first 5 tables
            logger.info(f"    - {table}")
        if len(table_list) > 5:
            logger.info(f"    ... and {len(table_list) - 5} more")
    
    return schema_tables

def get_table_reference(table_name):
    """Get the full table reference including schema"""
    schema = DB_CONFIG.get('schema', 'dbo')
    return f"[{schema}].[{table_name}]"

def disable_constraints(cursor):
    """Disable all foreign key constraints"""
    logger.info("Disabling foreign key constraints")
    schema = DB_CONFIG.get('schema', 'dbo')
    
    # Get all foreign key constraints
    query = """
    SELECT 
        OBJECT_SCHEMA_NAME(parent_object_id) AS SchemaName,
        OBJECT_NAME(parent_object_id) AS TableName,
        name AS ConstraintName
    FROM sys.foreign_keys
    WHERE is_disabled = 0
    AND OBJECT_SCHEMA_NAME(parent_object_id) = ?
    """
    
    cursor.execute(query, schema)
    constraints = cursor.fetchall()
    
    # Disable each constraint
    for schema_name, table_name, constraint_name in constraints:
        try:
            alter_query = f"ALTER TABLE [{schema_name}].[{table_name}] NOCHECK CONSTRAINT [{constraint_name}]"
            cursor.execute(alter_query)
            logger.debug(f"Disabled constraint: {constraint_name} on {schema_name}.{table_name}")
        except Exception as e:
            logger.warning(f"Could not disable constraint {constraint_name}: {e}")
    
    logger.info(f"Disabled {len(constraints)} foreign key constraints")

def enable_constraints(cursor):
    """Re-enable all foreign key constraints"""
    logger.info("Re-enabling foreign key constraints")
    schema = DB_CONFIG.get('schema', 'dbo')
    
    # Get all foreign key constraints
    query = """
    SELECT 
        OBJECT_SCHEMA_NAME(parent_object_id) AS SchemaName,
        OBJECT_NAME(parent_object_id) AS TableName,
        name AS ConstraintName
    FROM sys.foreign_keys
    WHERE OBJECT_SCHEMA_NAME(parent_object_id) = ?
    """
    
    cursor.execute(query, schema)
    constraints = cursor.fetchall()
    
    # Enable each constraint with check
    for schema_name, table_name, constraint_name in constraints:
        try:
            alter_query = f"ALTER TABLE [{schema_name}].[{table_name}] WITH CHECK CHECK CONSTRAINT [{constraint_name}]"
            cursor.execute(alter_query)
            logger.debug(f"Enabled constraint: {constraint_name} on {schema_name}.{table_name}")
        except Exception as e:
            logger.warning(f"Could not enable constraint {constraint_name}: {e}")
    
    logger.info(f"Enabled {len(constraints)} foreign key constraints")

def clear_table(cursor, table_name):
    """Clear existing data from table"""
    try:
        table_ref = get_table_reference(table_name)
        logger.info(f"Clearing table: {table_ref}")
        # Use DELETE instead of TRUNCATE to avoid foreign key issues
        cursor.execute(f"DELETE FROM {table_ref}")
    except Exception as e:
        logger.warning(f"Could not clear table {table_name}: {e}")
        raise

def import_table_data(cursor, table_data):
    """Import data for a single table"""
    table_name = table_data['name']
    columns = [col['name'] for col in table_data['columns']]
    rows = table_data.get('rows', [])
    
    if not rows:
        logger.info(f"No data to import for table: {table_name}")
        return
    
    logger.info(f"Importing {len(rows)} rows into table: {table_name}")
    
    # Clear existing data
    clear_table(cursor, table_name)
    
    # Prepare insert statement with schema
    table_ref = get_table_reference(table_name)
    placeholders = ', '.join(['?' for _ in columns])
    column_list = ', '.join([f'[{col}]' for col in columns])
    insert_query = f"INSERT INTO {table_ref} ({column_list}) VALUES ({placeholders})"
    
    # Get column types from the database schema, as JSON types are unreliable
    column_types = {}
    try:
        schema = DB_CONFIG.get('schema', 'dbo')
        query = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?"
        cursor.execute(query, schema, table_name)
        db_column_types = {row.COLUMN_NAME: row.DATA_TYPE for row in cursor.fetchall()}
        
        # Use the accurate DB types
        for col in columns:
            column_types[col] = db_column_types.get(col, 'VARCHAR') # Default to VARCHAR if not found
            
    except Exception as e:
        logger.warning(f"Could not fetch column types for table {table_name}, falling back to JSON types. Error: {e}")
        # Fallback to using types from JSON if DB query fails
        column_types = {col['name']: col.get('type', 'VARCHAR') for col in table_data['columns']}
    
    # Insert rows
    success_count = 0
    for i, row in enumerate(rows):
        try:
            # Prepare values
            prepared_values = []
            for j, value in enumerate(row):
                col_name = columns[j]
                col_type = column_types.get(col_name, 'VARCHAR')
                prepared_value = prepare_value(value, col_type)
                prepared_values.append(prepared_value)
            
            cursor.execute(insert_query, prepared_values)
            success_count += 1
            
            # Log progress every 1000 rows
            if (i + 1) % 1000 == 0:
                logger.info(f"  Processed {i + 1} rows...")
                
        except Exception as e:
            logger.error(f"Error inserting row {i + 1} into {table_name}: {e}")
            logger.debug(f"Row data: {row}")
            raise  # Re-raise to trigger rollback
    
    logger.info(f"Successfully imported {success_count}/{len(rows)} rows into {table_name}")

def main():
    """Main import function"""
    connection = None
    cursor = None
    
    try:
        # Load JSON data
        json_file = r'C:\AMD RPA\Github\open-webui\backend\DB-Migration-ACP-3780\dev-openwebui-data.json'
        data = load_json_data(json_file)
        
        # Extract tables
        tables = {obj['name']: obj for obj in data['objects'] if obj['type'] == 'table'}
        logger.info(f"Found {len(tables)} tables to import")
        
        # Connect to database
        logger.info("Connecting to MSSQL database...")
        conn_string = get_connection_string()
        connection = pyodbc.connect(conn_string, autocommit=False)
        connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
        connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
        connection.setencoding(encoding='utf-8')
        cursor = connection.cursor()
        logger.info("Connected successfully")
        
        logger.info("Starting transaction...")
        
        # Check existing tables
        schema_tables = check_database_tables(cursor)
        
        # Verify target schema exists
        target_schema = DB_CONFIG.get('schema', 'dbo')
        if target_schema not in schema_tables:
            logger.error(f"Schema '{target_schema}' not found in database!")
            logger.error(f"Available schemas: {list(schema_tables.keys())}")
            raise Exception(f"Target schema '{target_schema}' does not exist")
        
        # Check if our tables exist
        existing_tables = set(schema_tables.get(target_schema, []))
        json_tables = set(tables.keys())
        missing_tables = json_tables - existing_tables
        
        if missing_tables:
            logger.error(f"The following tables are missing from schema '{target_schema}':")
            for table in sorted(missing_tables):
                logger.error(f"  - {table}")
            logger.error("\nPlease ensure the schema script has been executed:")
            logger.error("  dev-openwebui-schema.sqlserver.sql")
            raise Exception(f"{len(missing_tables)} tables are missing from the database")
        
        # Test access to a table
        logger.info("Testing table access...")
        test_table = get_table_reference('feedback')
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {test_table}")
            row = cursor.fetchone()
            if row:
                count = row[0]
                logger.info(f"Successfully accessed {test_table}, current row count: {count}")
            else:
                logger.warning(f"Could not retrieve row count for {test_table}, assuming 0.")
                count = 0
        except Exception as e:
            logger.error(f"Cannot access {test_table}: {e}")
            logger.error("This might be a permissions issue")
            raise
        
        # Disable constraints for import
        disable_constraints(cursor)
        
        # Import tables in order
        table_order = get_table_order()
        imported_tables = set()
        
        # Import tables in specified order
        for table_name in table_order:
            if table_name in tables:
                import_table_data(cursor, tables[table_name])
                imported_tables.add(table_name)
        
        # Import any remaining tables not in the order list
        for table_name, table_data in tables.items():
            if table_name not in imported_tables:
                import_table_data(cursor, table_data)
        
        # Re-enable constraints
        enable_constraints(cursor)
        
        # Commit the transaction
        logger.info("Committing transaction...")
        connection.commit()
        logger.info("Transaction committed successfully!")
        
        # Close connection
        cursor.close()
        connection.close()
        
        logger.info("Import completed successfully!")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        
        # Rollback the transaction
        if connection:
            try:
                logger.info("Rolling back transaction...")
                connection.rollback()
                logger.info("Transaction rolled back successfully")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        
        # Clean up
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        
        sys.exit(1)

if __name__ == "__main__":
    # Print authentication reminder
    print("\n" + "="*60)
    print("IMPORTANT: Configure authentication in DB_CONFIG before running!")
    print("Options:")
    print("1. SQL Authentication: Set 'username' and 'password'")
    print("2. Windows Authentication: Set 'trusted_connection': 'yes'")
    print("3. Azure AD: Leave as is (uses ActiveDirectoryDefault)")
    print("="*60 + "\n")
    
    response = input("Have you configured the authentication? (yes/no): ")
    if response.lower() != 'yes':
        print("Please configure authentication in the script before running.")
        sys.exit(0)
    
    main()

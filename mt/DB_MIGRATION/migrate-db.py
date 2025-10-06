#!/usr/bin/env python3
"""
Non-interactive SQLite to PostgreSQL migration script
Usage: python3 migrate-db.py <sqlite_path> <postgres_url> [client_identifier]

client_identifier is typically the FQDN (e.g., chat.martins.net) to distinguish
between deployments with the same subdomain on different domains.
"""

import sys
import sqlite3
import psycopg2
import json
from datetime import datetime

# Log file path (will be set after parsing arguments)
LOG_FILE = None

def log(message, to_file_only=False):
    """Print timestamped log message to console and file"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"

    # Write to file
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + "\n")

    # Print to console unless file-only
    if not to_file_only:
        print(log_line, flush=True)

def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate a single table from SQLite to PostgreSQL"""
    log(f"Migrating table: {table_name}")

    # Skip metadata tables that are auto-managed
    if table_name in ['alembic_version', 'migratehistory']:
        log(f"  Skipping metadata table: {table_name}")
        return {"success": 0, "failed": 0, "errors": [], "skipped": True}

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Quote reserved keywords
    quoted_table = f'"{table_name}"'

    # Get all rows from SQLite
    try:
        sqlite_cursor.execute(f"SELECT * FROM {quoted_table}")
        rows = sqlite_cursor.fetchall()
    except Exception as e:
        log(f"  ✗ Error reading table: {e}")
        return {"success": 0, "failed": 0, "errors": [str(e)]}

    if not rows:
        log(f"  No data in {table_name}")
        return {"success": 0, "failed": 0, "errors": []}

    # Get column names and types from PostgreSQL
    pg_cursor.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    pg_columns = {row[0]: row[1] for row in pg_cursor.fetchall()}

    # Get column names from SQLite
    column_names = [desc[0] for desc in sqlite_cursor.description]

    # Prepare INSERT statement
    placeholders = ','.join(['%s'] * len(column_names))
    columns = ','.join([f'"{col}"' for col in column_names])
    insert_sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})'

    # Insert rows
    success_count = 0
    failed_count = 0
    errors = []

    for row_num, row in enumerate(rows, 1):
        try:
            # Convert Python types to PostgreSQL-compatible types
            processed_row = []
            for col_name, value in zip(column_names, row):
                if isinstance(value, str):
                    # Remove null bytes which PostgreSQL doesn't support
                    value = value.replace('\u0000', '')

                # Convert SQLite integers to PostgreSQL booleans
                if col_name in pg_columns and pg_columns[col_name] == 'boolean':
                    if isinstance(value, int):
                        value = bool(value)

                processed_row.append(value)

            # Use individual transaction per row to avoid cascade failures
            try:
                pg_cursor.execute(insert_sql, processed_row)
                pg_conn.commit()
                success_count += 1

                if success_count % 100 == 0:
                    log(f"  Migrated {success_count} rows...")
            except Exception as row_error:
                pg_conn.rollback()
                failed_count += 1
                error_msg = f"Row {row_num}: {str(row_error)}"
                errors.append(error_msg)
                log(f"  ⚠ Failed row {row_num}: {row_error}", to_file_only=True)

        except Exception as e:
            failed_count += 1
            error_msg = f"Row {row_num}: {str(e)}"
            errors.append(error_msg)
            log(f"  ⚠ Failed row {row_num}: {e}", to_file_only=True)
            continue

    if failed_count > 0:
        log(f"  ⚠ Migrated {success_count} rows from {table_name} ({failed_count} failed)")
    else:
        log(f"  ✓ Migrated {success_count} rows from {table_name}")

    return {"success": success_count, "failed": failed_count, "errors": errors}

def main():
    global LOG_FILE

    if len(sys.argv) < 3:
        print("Usage: python3 migrate-db.py <sqlite_path> <postgres_url> [client_identifier]")
        sys.exit(1)

    sqlite_path = sys.argv[1]
    postgres_url = sys.argv[2]
    client_identifier = sys.argv[3] if len(sys.argv) > 3 else "unknown"

    # Sanitize client_identifier for use in filename (replace invalid chars)
    safe_identifier = client_identifier.replace(':', '_').replace('/', '_').replace(' ', '_')

    # Set log file path with client identifier (FQDN)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    LOG_FILE = f"/tmp/migration-{safe_identifier}-{timestamp}.log"

    log("=" * 60)
    log("Starting database migration")
    log("=" * 60)
    log(f"Client: {client_identifier}")
    log(f"Source: {sqlite_path}")
    log(f"Target: {postgres_url.split('@')[1] if '@' in postgres_url else 'PostgreSQL'}")
    log(f"Log file: {LOG_FILE}")
    log("")

    try:
        # Connect to SQLite
        log("Connecting to SQLite database...")
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        log("✓ Connected to SQLite")

        # Connect to PostgreSQL
        log("Connecting to PostgreSQL database...")
        pg_conn = psycopg2.connect(postgres_url)
        log("✓ Connected to PostgreSQL")
        log("")

        # Get list of tables from SQLite
        sqlite_cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        all_tables = [row[0] for row in sqlite_cursor.fetchall()]

        # Define table dependencies - parent tables must be migrated before children
        # This ensures foreign key constraints are satisfied
        dependency_order = [
            'user',              # Must be first (referenced by many tables)
            'auth',              # References user
            'tag',
            'config',
            'chat',              # References user
            'oauth_session',     # References user
            'function',
            'model',
            'tool',
            'prompt',
            'document',
            'file',
            'folder',
            'knowledge',
            'memory',
            'message',           # References chat/user
            'message_reaction',
            'feedback',
            'chatidtag',         # References chat/tag
            'channel',
            'channel_member',
            'note',
            'group',
            # Metadata tables (will be skipped)
            'alembic_version',
            'migratehistory'
        ]

        # Sort tables by dependency order, then alphabetically for any not in list
        tables = []
        for table in dependency_order:
            if table in all_tables:
                tables.append(table)
        # Add any tables not in dependency list
        for table in sorted(all_tables):
            if table not in tables:
                tables.append(table)

        log(f"Found {len(tables)} tables to migrate")
        log("")

        # Migrate each table and track results
        total_success = 0
        total_failed = 0
        table_results = {}

        for table in tables:
            try:
                result = migrate_table(sqlite_conn, pg_conn, table)
                total_success += result["success"]
                total_failed += result["failed"]
                table_results[table] = result
            except Exception as e:
                log(f"✗ Error migrating {table}: {e}")
                table_results[table] = {"success": 0, "failed": 0, "errors": [str(e)]}
                continue

        log("")
        log("=" * 60)
        log("Migration Summary")
        log("=" * 60)
        log(f"Tables processed: {len(table_results)}/{len(tables)}")
        log(f"Total rows migrated: {total_success}")
        if total_failed > 0:
            log(f"Total rows failed: {total_failed}")
        log("")

        # Detailed table summary
        log("Table Details:")
        for table, result in table_results.items():
            if result["failed"] > 0:
                log(f"  ⚠ {table}: {result['success']} success, {result['failed']} failed")
            elif result["success"] > 0:
                log(f"  ✓ {table}: {result['success']} rows")
            else:
                log(f"  - {table}: empty")

        # Error details (file only)
        if total_failed > 0:
            log("")
            log("Detailed Error Report:", to_file_only=True)
            log("=" * 60, to_file_only=True)
            for table, result in table_results.items():
                if result["errors"]:
                    log(f"Table: {table}", to_file_only=True)
                    for error in result["errors"]:
                        log(f"  {error}", to_file_only=True)
                    log("", to_file_only=True)

        log("")
        log("=" * 60)
        if total_failed > 0:
            log(f"⚠ Migration completed with {total_failed} failures")
            log(f"Review log file for details: {LOG_FILE}")
        else:
            log("✓ Migration completed successfully")
        log("=" * 60)

        # Close connections
        sqlite_conn.close()
        pg_conn.close()

        sys.exit(0)

    except sqlite3.Error as e:
        log(f"✗ SQLite error: {e}")
        sys.exit(1)
    except psycopg2.Error as e:
        log(f"✗ PostgreSQL error: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"✗ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

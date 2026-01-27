#!/usr/bin/env python3
"""
Quick inspection of PostgreSQL dump file.

This script provides a quick overview of what's in a PostgreSQL dump
without requiring full parsing or database setup.

Usage:
    python inspect_dump.py [dump_file_path]
"""

import sys
import os
import subprocess
from pathlib import Path


def inspect_custom_format(dump_file: str):
    """Inspect PostgreSQL custom format dump using pg_restore --list."""
    print("PostgreSQL custom format dump detected.")
    print("Attempting to list contents using pg_restore --list...\n")
    
    try:
        result = subprocess.run(
            ['pg_restore', '--list', dump_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("Dump contents:")
            print("=" * 60)
            print(result.stdout)
            print("=" * 60)
            
            # Count tables
            table_count = result.stdout.count('TABLE DATA')
            print(f"\nFound {table_count} tables with data")
            
            # Extract table names
            import re
            table_pattern = r'TABLE DATA\s+public\s+(\w+)'
            tables = re.findall(table_pattern, result.stdout)
            if tables:
                print("\nTables found:")
                for table in sorted(set(tables)):
                    print(f"  - {table}")
        else:
            print("Error running pg_restore:")
            print(result.stderr)
            print("\nTo inspect this dump, you need:")
            print("  1. Install PostgreSQL client tools")
            print("  2. Or convert to SQL: pg_restore -f dump.sql", dump_file)
            
    except FileNotFoundError:
        print("Error: pg_restore is not installed.")
        print("\nTo inspect this dump, you can:")
        print("  1. Install PostgreSQL client tools:")
        print("     - macOS: brew install postgresql")
        print("     - Ubuntu: sudo apt-get install postgresql-client")
        print("  2. Or convert manually: pg_restore -f dump.sql", dump_file)
        print("     Then examine the SQL file directly")
    except subprocess.TimeoutExpired:
        print("Error: pg_restore timed out. The dump file may be very large.")


def inspect_sql_format(dump_file: str):
    """Inspect plain SQL dump file."""
    print("Plain SQL format dump detected.")
    print("Scanning for table definitions and data...\n")
    
    try:
        with open(dump_file, 'rb') as f:
            # Read first 1MB to find table definitions
            content = f.read(1024 * 1024).decode('utf-8', errors='ignore')
        
        import re
        
        # Find CREATE TABLE statements
        table_pattern = r'CREATE TABLE\s+"public"\.\"(\w+)"'
        tables = re.findall(table_pattern, content, re.IGNORECASE)
        
        # Find COPY statements (data)
        copy_pattern = r'COPY\s+"public"\.\"(\w+)"'
        copy_tables = re.findall(copy_pattern, content, re.IGNORECASE)
        
        print(f"Found {len(set(tables))} table definitions")
        print(f"Found {len(set(copy_tables))} tables with data\n")
        
        if tables:
            print("Tables defined:")
            for table in sorted(set(tables)):
                has_data = "✓" if table in copy_tables else " "
                print(f"  [{has_data}] {table}")
        
    except Exception as e:
        print(f"Error reading SQL file: {e}")


def is_custom_format(file_path: str) -> bool:
    """Check if file is PostgreSQL custom format."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            return header == b'PGDMP'
    except:
        return False


def find_dump_file() -> str:
    """Find dump file in common locations."""
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            return sys.argv[1]
    
    # Check Downloads folder
    downloads_path = Path.home() / "Downloads" / "b078-20260113-215725.dump"
    if downloads_path.exists():
        return str(downloads_path)
    
    # Check workspace root
    workspace_dump = Path("/workspace") / "heroku_psql_181025.dump"
    if workspace_dump.exists():
        return str(workspace_dump)
    
    # Check current directory
    current_dump = Path("heroku_psql_181025.dump")
    if current_dump.exists():
        return str(current_dump)
    
    return None


def main():
    dump_file = find_dump_file()
    
    if not dump_file:
        print("Error: Could not find dump file.")
        print("Please provide the path to the dump file as an argument.")
        sys.exit(1)
    
    print(f"Inspecting: {dump_file}\n")
    
    if is_custom_format(dump_file):
        inspect_custom_format(dump_file)
    else:
        inspect_sql_format(dump_file)
    
    print("\nTo extract and transform the data, run:")
    print("  python transform_dump_to_dataframes.py", dump_file)


if __name__ == "__main__":
    main()

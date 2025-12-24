#!/usr/bin/env python3

"""
Clear all tables in the SQLite backend database for testing purposes.

This script will delete all data from all tables in the SQLite database.
It only works with SQLite databases and will exit with an error if a PostgreSQL
database is detected.

Usage:
    python clear_db.py                           # Prompts for confirmation, uses DATABASE_URL
    python clear_db.py --yes                     # Skips confirmation prompt
    python clear_db.py --db-path /path/to/db.db  # Specify database path directly
    python clear_db.py --db-path /path/to/db.db --yes  # Specify path and skip confirmation
    
    # Alternative: Use DB_ABS environment variable to specify absolute database path
    DB_ABS="/path/to/webui.db" python clear_db.py
"""

import sys
import os
import argparse
import sqlite3

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.env import DATABASE_URL, DATA_DIR


def extract_sqlite_path(database_url: str) -> str:
    """
    Extract the file path from a SQLite database URL.
    
    Handles:
    - sqlite:///path/to/db.db
    - sqlite+sqlcipher:///path/to/db.db
    - sqlite:///./relative/path/db.db
    """
    # Remove sqlite:// or sqlite+sqlcipher:// prefix
    if database_url.startswith("sqlite+sqlcipher://"):
        path = database_url.replace("sqlite+sqlcipher://", "")
    elif database_url.startswith("sqlite://"):
        path = database_url.replace("sqlite://", "")
    else:
        raise ValueError(f"Invalid SQLite URL format: {database_url}")
    
    # Remove leading slashes for absolute paths
    if path.startswith("///"):
        path = path[3:]
    elif path.startswith("//"):
        path = path[2:]
    elif path.startswith("/"):
        path = path[1:]
    
    # Handle relative paths
    if not os.path.isabs(path):
        # If relative, it's relative to DATA_DIR
        path = os.path.join(DATA_DIR, path.lstrip("./"))
    
    return path


def get_all_tables(conn: sqlite3.Connection) -> list[str]:
    """
    Get all user tables from the SQLite database.
    
    Excludes system tables like sqlite_master, sqlite_sequence, etc.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    return tables


def clear_database(db_path: str, skip_confirmation: bool = False) -> bool:
    """
    Clear all tables in the SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
        skip_confirmation: If True, skip the confirmation prompt
        
    Returns:
        True if successful, False otherwise
    """
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Error: Database file not found: {db_path}")
        return False
    
    # Confirmation prompt
    if not skip_confirmation:
        print(f"Warning: This will delete ALL data from the database: {db_path}")
        print("This action cannot be undone!")
        response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        tables = get_all_tables(conn)
        
        if not tables:
            print("No tables found in the database.")
            conn.close()
            return True
        
        print(f"\nFound {len(tables)} table(s) to clear:")
        for table in tables:
            print(f"  - {table}")
        
        # Disable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Clear each table
        cleared_count = 0
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
                row_count = cursor.rowcount
                cleared_count += 1
                print(f"Cleared table '{table}' ({row_count} row(s) deleted)")
            except sqlite3.Error as e:
                print(f"Error clearing table '{table}': {e}")
                # Continue with other tables
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"\nSuccessfully cleared {cleared_count} table(s).")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clear all tables in the SQLite backend database for testing"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--db-path", "--database",
        dest="db_path",
        type=str,
        default=None,
        help="Path to the SQLite database file (overrides DB_ABS env var and DATABASE_URL)"
    )
    args = parser.parse_args()
    
    # Priority: command-line argument > environment variable > DATABASE_URL
    if args.db_path:
        # Use path from command-line argument
        db_path = os.path.abspath(args.db_path)
        print(f"Using --db-path argument: {db_path}")
    else:
        # Check for DB_ABS environment variable
        db_abs = os.environ.get("DB_ABS")
        if db_abs:
            # Use absolute path from environment variable
            db_path = os.path.abspath(db_abs)
            print(f"Using DB_ABS environment variable: {db_path}")
        else:
            # Fall back to DATABASE_URL parsing
            # Check if database URL is SQLite
            if "sqlite" not in DATABASE_URL.lower():
                print(f"Error: This script only works with SQLite databases.")
                print(f"Current DATABASE_URL: {DATABASE_URL}")
                print("If you're using PostgreSQL, this script cannot be used.")
                print("Use --db-path argument or set DB_ABS environment variable to specify the database path directly.")
                sys.exit(1)
            
            # Extract database path
            try:
                db_path = extract_sqlite_path(DATABASE_URL)
            except ValueError as e:
                print(f"Error parsing DATABASE_URL: {e}")
                sys.exit(1)
    
    print(f"Database path: {db_path}")
    
    # Clear the database
    success = clear_database(db_path, skip_confirmation=args.yes)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()


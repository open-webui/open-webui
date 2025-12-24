#!/usr/bin/env python3

"""
Remove the migratehistory table from SQLite database.

This table is created by peewee_migrate to track Peewee migrations.
Since we're using Alembic migrations and skipping Peewee migrations,
this table is no longer needed and can be safely removed.

Usage:
    DB_ABS="/path/to/webui.db" python remove_migratehistory.py
    DB_ABS="/path/to/webui.db" python remove_migratehistory.py --yes  # Skip confirmation
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
    """
    if database_url.startswith("sqlite+sqlcipher://"):
        path = database_url.replace("sqlite+sqlcipher://", "")
    elif database_url.startswith("sqlite://"):
        path = database_url.replace("sqlite://", "")
    else:
        raise ValueError(f"Invalid SQLite URL format: {database_url}")
    
    if path.startswith("///"):
        path = path[3:]
    elif path.startswith("//"):
        path = path[2:]
    elif path.startswith("/"):
        path = path[1:]
    
    if not os.path.isabs(path):
        path = os.path.join(DATA_DIR, path.lstrip("./"))
    
    return path


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def remove_migratehistory(db_path: str, skip_confirmation: bool = False) -> bool:
    """
    Remove the migratehistory table from the database.
    
    Args:
        db_path: Path to the SQLite database file
        skip_confirmation: If True, skip the confirmation prompt
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        if not table_exists(conn, "migratehistory"):
            print("migratehistory table does not exist in the database.")
            conn.close()
            return True
        
        # Show what's in the table before removing
        cursor.execute("SELECT COUNT(*) FROM migratehistory")
        row_count = cursor.fetchone()[0]
        
        if row_count > 0:
            cursor.execute("SELECT name FROM migratehistory ORDER BY id")
            migrations = [row[0] for row in cursor.fetchall()]
            print(f"\nmigratehistory table contains {row_count} migration(s):")
            for i, migration in enumerate(migrations, 1):
                print(f"  {i}. {migration}")
        
        # Confirmation prompt
        if not skip_confirmation:
            print(f"\nWarning: This will permanently delete the migratehistory table from: {db_path}")
            print("This table is only used by Peewee migrations, which are skipped when Alembic is detected.")
            response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print("Operation cancelled.")
                conn.close()
                return False
        
        # Drop the table
        cursor.execute("DROP TABLE IF EXISTS migratehistory")
        conn.commit()
        conn.close()
        
        print(f"\nSuccessfully removed migratehistory table from database.")
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
        description="Remove the migratehistory table from SQLite database"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    args = parser.parse_args()
    
    # Check for DB_ABS environment variable first
    db_abs = os.environ.get("DB_ABS")
    if db_abs:
        db_path = os.path.abspath(db_abs)
        print(f"Using DB_ABS environment variable: {db_path}")
    else:
        # Fall back to DATABASE_URL parsing
        if "sqlite" not in DATABASE_URL.lower():
            print(f"Error: This script only works with SQLite databases.")
            print(f"Current DATABASE_URL: {DATABASE_URL}")
            print("Set DB_ABS environment variable to specify the database path directly.")
            sys.exit(1)
        
        try:
            db_path = extract_sqlite_path(DATABASE_URL)
        except ValueError as e:
            print(f"Error parsing DATABASE_URL: {e}")
            sys.exit(1)
    
    print(f"Database path: {db_path}")
    
    # Remove the table
    success = remove_migratehistory(db_path, skip_confirmation=args.yes)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()




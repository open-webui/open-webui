#!/usr/bin/env python3

"""
Display all information from tables in the SQLite backend database.

This script displays all data from all tables in the SQLite database,
useful for reviewing test results and debugging.

Usage:
    python display_db.py                    # Display all tables
    python display_db.py --table user       # Display specific table
    python display_db.py --limit 10         # Limit rows per table
    python display_db.py --no-empty         # Skip empty tables
    python display_db.py --output file.txt  # Write output to file

    # Use DB_ABS environment variable to specify absolute database path
    DB_ABS="/path/to/webui.db" python display_db.py
"""

import sys
import os
import argparse
import sqlite3
import json
from typing import Optional

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
        # But first check if it's already an absolute path after stripping slashes
        path = path.lstrip("./")
        if not os.path.isabs(path):
            path = os.path.join(DATA_DIR, path)
        # If path is now absolute, normalize it
        if os.path.isabs(path):
            path = os.path.normpath(path)

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


def quote_table_name(table_name: str) -> str:
    """
    Quote table name to handle reserved keywords like 'group'.

    SQLite supports double quotes for identifiers.
    """
    return f'"{table_name}"'


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> list[tuple]:
    """
    Get column information for a table.

    Returns list of (column_name, data_type) tuples.
    """
    cursor = conn.cursor()
    quoted_name = quote_table_name(table_name)
    cursor.execute(f"PRAGMA table_info({quoted_name})")
    return [(row[1], row[2]) for row in cursor.fetchall()]


def format_value(value: any, max_length: int = 50) -> str:
    """
    Format a value for display, handling None, JSON, and long strings.
    """
    if value is None:
        return "NULL"

    # Handle JSON fields
    if isinstance(value, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(value)
            if isinstance(parsed, (dict, list)):
                json_str = json.dumps(parsed, indent=2)
                if len(json_str) > max_length:
                    return json_str[: max_length - 3] + "..."
                return json_str
        except (json.JSONDecodeError, TypeError):
            pass

        # Regular string - truncate if too long
        if len(value) > max_length:
            return value[: max_length - 3] + "..."
        return value

    # Convert to string and truncate if needed
    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[: max_length - 3] + "..."
    return str_value


def display_table(
    conn: sqlite3.Connection,
    table_name: str,
    limit: Optional[int] = None,
    show_empty: bool = True,
    output_file=None,
) -> bool:
    """
    Display all data from a table.

    Returns True if table has data, False if empty.
    """
    cursor = conn.cursor()

    def write_output(text):
        """Write to file if provided, otherwise to stdout."""
        if output_file:
            output_file.write(text + "\n")
        else:
            print(text)

    # Get table schema
    schema = get_table_schema(conn, table_name)
    if not schema:
        write_output(f"  No schema found for table '{table_name}'")
        return False

    column_names = [col[0] for col in schema]

    # Get row count - quote table name to handle reserved keywords
    quoted_name = quote_table_name(table_name)
    cursor.execute(f"SELECT COUNT(*) FROM {quoted_name}")
    total_rows = cursor.fetchone()[0]

    if total_rows == 0:
        if show_empty:
            write_output(f"\n{'='*80}")
            write_output(f"Table: {table_name}")
            write_output(f"{'='*80}")
            write_output("  (empty)")
        return False

    # Build query with optional limit - quote table name
    query = f"SELECT * FROM {quoted_name}"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = cursor.fetchall()

    # Display table header
    write_output(f"\n{'='*80}")
    write_output(f"Table: {table_name}")
    write_output(f"{'='*80}")
    write_output(
        f"Total rows: {total_rows}"
        + (f" (showing {len(rows)})" if limit and len(rows) < total_rows else "")
    )
    write_output("")

    # Calculate column widths
    col_widths = {}
    for col_name in column_names:
        col_widths[col_name] = max(len(col_name), 10)

    # Adjust widths based on data
    for row in rows:
        for i, value in enumerate(row):
            col_name = column_names[i]
            formatted = format_value(value, max_length=200)
            col_widths[col_name] = max(col_widths[col_name], len(formatted))

    # Limit column width to prevent excessive width
    max_col_width = 60
    for col_name in col_widths:
        col_widths[col_name] = min(col_widths[col_name], max_col_width)

    # Print header
    header = " | ".join(
        [col_name.ljust(col_widths[col_name]) for col_name in column_names]
    )
    write_output(header)
    write_output("-" * len(header))

    # Print rows
    for row in rows:
        formatted_row = []
        for i, value in enumerate(row):
            col_name = column_names[i]
            formatted = format_value(value, max_length=max_col_width)
            formatted_row.append(formatted.ljust(col_widths[col_name]))
        write_output(" | ".join(formatted_row))

    if limit and len(rows) < total_rows:
        write_output(f"\n  ... ({total_rows - len(rows)} more row(s) not shown)")

    return True


def display_database(
    db_path: str,
    table_filter: Optional[str] = None,
    limit: Optional[int] = None,
    show_empty: bool = True,
    output_file=None,
) -> bool:
    """
    Display all tables in the SQLite database.

    Args:
        db_path: Path to the SQLite database file
        table_filter: If provided, only display this table
        limit: Maximum number of rows to display per table
        show_empty: If True, show empty tables
        output_file: File object to write output to (None for stdout)

    Returns:
        True if successful, False otherwise
    """

    def write_output(text):
        """Write to file if provided, otherwise to stdout."""
        if output_file:
            output_file.write(text + "\n")
        else:
            print(text)

    # Check if database file exists
    if not os.path.exists(db_path):
        write_output(f"Error: Database file not found: {db_path}")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name

        # Get all tables
        all_tables = get_all_tables(conn)

        if not all_tables:
            write_output("No tables found in the database.")
            conn.close()
            return True

        # Filter tables if requested
        if table_filter:
            matching_tables = [
                t for t in all_tables if table_filter.lower() in t.lower()
            ]
            if not matching_tables:
                write_output(f"No tables found matching '{table_filter}'")
                write_output(f"Available tables: {', '.join(all_tables)}")
                conn.close()
                return False
            tables_to_display = matching_tables
        else:
            tables_to_display = all_tables

        write_output(f"Database: {db_path}")
        write_output(f"Found {len(tables_to_display)} table(s) to display")

        # Display each table
        displayed_count = 0
        for table in tables_to_display:
            has_data = display_table(
                conn, table, limit=limit, show_empty=show_empty, output_file=output_file
            )
            if has_data:
                displayed_count += 1

        conn.close()

        write_output(f"\n{'='*80}")
        write_output(f"Summary: Displayed {displayed_count} table(s) with data")
        write_output(f"{'='*80}")

        return True

    except sqlite3.Error as e:
        error_msg = f"Database error: {e}"
        if output_file:
            output_file.write(error_msg + "\n")
        else:
            print(error_msg)
        return False
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        if output_file:
            output_file.write(error_msg + "\n")
            import traceback

            output_file.write(traceback.format_exc())
        else:
            print(error_msg)
            import traceback

            traceback.print_exc()
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Display all data from tables in the SQLite backend database"
    )
    parser.add_argument(
        "--table",
        "-t",
        type=str,
        help="Display only tables matching this name (partial match)",
    )
    parser.add_argument(
        "--limit", "-l", type=int, help="Maximum number of rows to display per table"
    )
    parser.add_argument("--no-empty", action="store_true", help="Skip empty tables")
    parser.add_argument(
        "--output", "-o", type=str, help="Write output to file instead of stdout"
    )
    args = parser.parse_args()

    # Open output file if specified
    output_file = None
    if args.output:
        try:
            output_file = open(args.output, "w", encoding="utf-8")
        except Exception as e:
            print(f"Error opening output file: {e}")
            sys.exit(1)

    try:
        # Check for DB_ABS environment variable first
        db_abs = os.environ.get("DB_ABS")
        if db_abs:
            # Use absolute path from environment variable
            # Handle both absolute paths and SQLite URLs
            if db_abs.startswith("sqlite://") or db_abs.startswith(
                "sqlite+sqlcipher://"
            ):
                # If DB_ABS is a URL, extract the path (but don't join with DATA_DIR)
                # Temporarily store original DATA_DIR
                original_data_dir = DATA_DIR
                # Extract path from URL
                if db_abs.startswith("sqlite+sqlcipher://"):
                    path = db_abs.replace("sqlite+sqlcipher://", "")
                else:
                    path = db_abs.replace("sqlite://", "")

                # Remove leading slashes
                if path.startswith("///"):
                    path = path[3:]
                elif path.startswith("//"):
                    path = path[2:]
                elif path.startswith("/"):
                    path = path[1:]

                # If it's absolute, use it; otherwise resolve relative to current directory
                if os.path.isabs(path):
                    db_path = os.path.normpath(path)
                else:
                    db_path = os.path.abspath(path)
            elif os.path.isabs(db_abs):
                # Already absolute, normalize it
                db_path = os.path.normpath(db_abs)
            else:
                # Relative path, resolve it
                db_path = os.path.abspath(db_abs)

            msg = f"Using DB_ABS environment variable: {db_path}"
            if output_file:
                output_file.write(msg + "\n")
            else:
                print(msg)
        else:
            # Fall back to DATABASE_URL parsing
            # Check if database URL is SQLite
            if "sqlite" not in DATABASE_URL.lower():
                error_msg = (
                    f"Error: This script only works with SQLite databases.\n"
                    f"Current DATABASE_URL: {DATABASE_URL}\n"
                    "If you're using PostgreSQL, this script cannot be used.\n"
                    "Alternatively, set DB_ABS environment variable to specify the database path directly."
                )
                if output_file:
                    output_file.write(error_msg + "\n")
                else:
                    print(error_msg)
                sys.exit(1)

            # Extract database path
            try:
                db_path = extract_sqlite_path(DATABASE_URL)
            except ValueError as e:
                error_msg = f"Error parsing DATABASE_URL: {e}"
                if output_file:
                    output_file.write(error_msg + "\n")
                else:
                    print(error_msg)
                sys.exit(1)

        # Display the database
        success = display_database(
            db_path,
            table_filter=args.table,
            limit=args.limit,
            show_empty=not args.no_empty,
            output_file=output_file,
        )

        if not success:
            sys.exit(1)
    finally:
        if output_file:
            output_file.close()
            print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Transform PostgreSQL dump file to pandas DataFrames.

This script parses a PostgreSQL dump file and extracts relevant tables
into cleaned pandas DataFrames for analysis.

Supports both:
  - PostgreSQL custom format (.dump) - requires pg_restore
  - Plain SQL format (.sql)

Usage:
    python transform_dump_to_dataframes.py [dump_file_path]

If no dump file is provided, it will look for:
    - b078-20260113-215725.dump in ~/Downloads
    - heroku_psql_181025.dump in workspace root

For custom format dumps, the script will attempt to use pg_restore
to convert to SQL format first. If pg_restore is not available,
you can manually convert:
    pg_restore -f dump.sql your_dump.dump
"""

import re
import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import io

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is not installed. Please install it:")
    print("  pip install pandas")
    sys.exit(1)


class PostgresDumpParser:
    """Parse PostgreSQL dump files and extract table data."""

    def __init__(self, dump_file_path: str):
        self.dump_file_path = dump_file_path
        self.tables_data: Dict[str, List[Dict]] = {}
        self.table_columns: Dict[str, List[str]] = {}

    def _is_custom_format(self, file_path: str) -> bool:
        """Check if dump is PostgreSQL custom format."""
        with open(file_path, "rb") as f:
            header = f.read(5)
            return header == b"PGDMP"

    def _convert_custom_to_sql(self, dump_file: str) -> str:
        """Convert custom format dump to SQL using pg_restore."""
        print("Detected PostgreSQL custom format dump. Converting to SQL...")

        # Check if pg_restore is available
        try:
            subprocess.run(["pg_restore", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\nError: pg_restore is not available.")
            print(
                "Please install PostgreSQL client tools, or convert the dump manually:"
            )
            print(f"  pg_restore -f dump.sql {dump_file}")
            print("\nThen run this script with the SQL file.")
            sys.exit(1)

        # Create temporary SQL file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as tmp:
            sql_file = tmp.name

        try:
            # Convert custom format to SQL
            print(f"Running: pg_restore -f {sql_file} {dump_file}")
            result = subprocess.run(
                ["pg_restore", "-f", sql_file, dump_file],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"Warning: pg_restore had issues: {result.stderr}")
                # Try with --no-owner and --no-privileges
                result = subprocess.run(
                    [
                        "pg_restore",
                        "--no-owner",
                        "--no-privileges",
                        "-f",
                        sql_file,
                        dump_file,
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise Exception(f"pg_restore failed: {result.stderr}")

            print(f"Conversion successful. SQL file: {sql_file}")
            return sql_file
        except Exception as e:
            if os.path.exists(sql_file):
                os.unlink(sql_file)
            raise

    def parse_dump(self) -> Dict[str, pd.DataFrame]:
        """Parse the dump file and return DataFrames for each table."""
        dump_file = self.dump_file_path

        # Handle custom format
        if self._is_custom_format(dump_file):
            sql_file = self._convert_custom_to_sql(dump_file)
            dump_file = sql_file
            cleanup_sql = True
        else:
            cleanup_sql = False

        try:
            print(f"Reading dump file: {dump_file}")

            with open(dump_file, "rb") as f:
                content = f.read()

            # Try to decode as UTF-8, fallback to latin-1
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                print("Warning: UTF-8 decode failed, trying latin-1...")
                text_content = content.decode("latin-1", errors="ignore")

            # Find all table definitions and COPY statements
            self._extract_table_schemas(text_content)
            self._extract_table_data(text_content)

            # Convert to DataFrames
            dataframes = {}
            for table_name, rows in self.tables_data.items():
                if rows:
                    df = pd.DataFrame(rows)
                    dataframes[table_name] = df
                    print(f"  Extracted {len(df)} rows from '{table_name}' table")
                else:
                    print(f"  No data found in '{table_name}' table")

            return dataframes
        finally:
            # Clean up temporary SQL file
            if cleanup_sql and os.path.exists(sql_file):
                os.unlink(sql_file)

    def _extract_table_schemas(self, content: str):
        """Extract table schema information."""
        # Find CREATE TABLE statements
        pattern = r'CREATE TABLE "public"\.\"(\w+)"\s*\((.*?)\);'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            table_name = match.group(1)
            table_def = match.group(2)

            # Extract column names
            columns = []
            # Match column definitions: "column_name" type ...
            col_pattern = r'"(\w+)"\s+([^,]+?)(?:,|$)'
            col_matches = re.finditer(col_pattern, table_def, re.MULTILINE)

            for col_match in col_matches:
                col_name = col_match.group(1)
                columns.append(col_name)

            self.table_columns[table_name] = columns

    def _extract_table_data(self, content: str):
        """Extract data from COPY statements."""
        # Find COPY statements: COPY "public"."table_name" (columns) FROM stdin;
        copy_pattern = r'COPY "public"\.\"(\w+)"\s*\(([^)]+)\)\s+FROM stdin;'
        copy_matches = list(re.finditer(copy_pattern, content, re.MULTILINE))

        for i, copy_match in enumerate(copy_match):
            table_name = copy_match.group(1)
            columns_str = copy_match.group(2)

            # Parse column names
            columns = [col.strip().strip('"') for col in columns_str.split(",")]

            # Find the data section (between COPY ... FROM stdin; and \.)
            start_pos = copy_match.end()

            # Find the end marker (\. or next COPY statement)
            if i + 1 < len(copy_matches):
                end_pos = copy_matches[i + 1].start()
            else:
                # Look for \. marker
                end_marker = content.find("\\.\n", start_pos)
                if end_marker == -1:
                    end_marker = content.find("\\.", start_pos)
                end_pos = end_marker if end_marker != -1 else len(content)

            data_section = content[start_pos:end_pos]

            # Parse tab-separated values
            rows = self._parse_copy_data(data_section, columns)
            self.tables_data[table_name] = rows

    def _parse_copy_data(self, data_section: str, columns: List[str]) -> List[Dict]:
        """Parse PostgreSQL COPY data format (tab-separated with \\N for NULL)."""
        rows = []
        lines = data_section.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("\\"):
                continue

            # Split by tab
            values = line.split("\t")

            # Ensure we have the right number of values
            if len(values) != len(columns):
                # Try to handle escaped tabs and special characters
                # This is a simplified parser - may need enhancement for complex cases
                continue

            row = {}
            for col, val in zip(columns, values):
                # Handle NULL values (\N)
                if val == "\\N":
                    row[col] = None
                else:
                    # Try to parse JSON fields
                    if val.startswith("{") or val.startswith("["):
                        try:
                            row[col] = json.loads(val)
                        except:
                            row[col] = val
                    else:
                        row[col] = val

            rows.append(row)

        return rows


class DataTransformer:
    """Transform raw table data into cleaned DataFrames."""

    # Define relevant tables for analysis
    RELEVANT_TABLES = [
        "user",
        "chat",
        "message",
        "child_profile",
        "selection",
        "moderation_scenario",
        "moderation_session",
        "moderation_applied",
        "moderation_question_answer",
        "exit_quiz_response",
        "scenario_assignments",  # May not exist in older dumps
        "scenarios",  # May not exist in older dumps
        "attention_check_scenarios",  # May not exist in older dumps
        "assignment_session_activity",  # May not exist in older dumps
    ]

    def __init__(self, dataframes: Dict[str, pd.DataFrame]):
        self.dataframes = dataframes
        self.transformed = {}

    def transform_all(self) -> Dict[str, pd.DataFrame]:
        """Transform all relevant tables."""
        print("\nTransforming data...")

        for table_name in self.RELEVANT_TABLES:
            if table_name in self.dataframes:
                df = self.dataframes[table_name]
                transformed_df = self._transform_table(table_name, df)
                self.transformed[table_name] = transformed_df
            else:
                print(f"  Table '{table_name}' not found in dump")

        return self.transformed

    def _transform_table(self, table_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a specific table."""
        print(f"  Transforming '{table_name}'...")

        # Make a copy to avoid modifying original
        df = df.copy()

        # Common transformations for all tables
        df = self._convert_timestamps(df)
        df = self._clean_strings(df)

        # Table-specific transformations
        if table_name == "user":
            df = self._transform_user(df)
        elif table_name == "chat":
            df = self._transform_chat(df)
        elif table_name == "message":
            df = self._transform_message(df)
        elif table_name == "child_profile":
            df = self._transform_child_profile(df)
        elif table_name == "selection":
            df = self._transform_selection(df)
        elif table_name == "moderation_scenario":
            df = self._transform_moderation_scenario(df)
        elif table_name == "moderation_session":
            df = self._transform_moderation_session(df)
        elif table_name == "exit_quiz_response":
            df = self._transform_exit_quiz(df)

        return df

    def _convert_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert timestamp columns to datetime."""
        timestamp_cols = [
            col for col in df.columns if "at" in col.lower() or "time" in col.lower()
        ]

        for col in timestamp_cols:
            if col in df.columns:
                try:
                    # Try to convert if numeric (epoch timestamps)
                    if df[col].dtype in ["int64", "float64"]:
                        # Check if values are in milliseconds or seconds
                        sample_val = (
                            df[col].dropna().iloc[0]
                            if len(df[col].dropna()) > 0
                            else None
                        )
                        if sample_val:
                            # If > 1e12, likely nanoseconds; if > 1e9, likely milliseconds
                            if sample_val > 1e12:
                                df[f"{col}_datetime"] = pd.to_datetime(
                                    df[col] / 1e9, unit="s", errors="coerce"
                                )
                            elif sample_val > 1e9:
                                df[f"{col}_datetime"] = pd.to_datetime(
                                    df[col], unit="ms", errors="coerce"
                                )
                            else:
                                df[f"{col}_datetime"] = pd.to_datetime(
                                    df[col], unit="s", errors="coerce"
                                )
                except Exception as e:
                    print(f"    Warning: Could not convert {col} to datetime: {e}")

        return df

    def _clean_strings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean string columns."""
        for col in df.columns:
            if df[col].dtype == "object":
                # Remove null bytes
                df[col] = df[col].astype(str).str.replace("\x00", "", regex=False)
                # Replace 'None' strings with actual None
                df[col] = df[col].replace("None", None)
                df[col] = df[col].replace("nan", None)

        return df

    def _transform_user(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform user table."""
        # Parse JSON fields
        if "info" in df.columns:
            df["info_parsed"] = df["info"].apply(
                lambda x: (
                    x
                    if isinstance(x, dict)
                    else (
                        json.loads(x)
                        if isinstance(x, str) and x.startswith("{")
                        else None
                    )
                )
            )

        if "settings" in df.columns:
            df["settings_parsed"] = df["settings"].apply(
                lambda x: (
                    x
                    if isinstance(x, dict)
                    else (
                        json.loads(x)
                        if isinstance(x, str) and x.startswith("{")
                        else None
                    )
                )
            )

        return df

    def _transform_chat(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform chat table."""
        # Parse JSON chat field
        if "chat" in df.columns:
            df["chat_parsed"] = df["chat"].apply(
                lambda x: (
                    x
                    if isinstance(x, dict)
                    else (
                        json.loads(x)
                        if isinstance(x, str) and x.startswith("{")
                        else None
                    )
                )
            )

            # Extract message count if available
            if df["chat_parsed"].notna().any():
                df["message_count"] = df["chat_parsed"].apply(
                    lambda x: (
                        len(x.get("history", {}).get("messages", {}))
                        if isinstance(x, dict)
                        else 0
                    )
                )

        # Parse meta field
        if "meta" in df.columns:
            df["meta_parsed"] = df["meta"].apply(
                lambda x: (
                    x
                    if isinstance(x, dict)
                    else (
                        json.loads(x)
                        if isinstance(x, str) and x.startswith("{")
                        else None
                    )
                )
            )

        return df

    def _transform_message(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform message table."""
        # Parse JSON fields
        for col in ["data", "meta"]:
            if col in df.columns:
                df[f"{col}_parsed"] = df[col].apply(
                    lambda x: (
                        x
                        if isinstance(x, dict)
                        else (
                            json.loads(x)
                            if isinstance(x, str) and x.startswith("{")
                            else None
                        )
                    )
                )

        return df

    def _transform_child_profile(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform child_profile table."""
        # Parse JSON fields if any
        for col in df.columns:
            if (
                df[col].dtype == "object"
                and df[col].astype(str).str.startswith("{").any()
            ):
                df[f"{col}_parsed"] = df[col].apply(
                    lambda x: (
                        x
                        if isinstance(x, dict)
                        else (
                            json.loads(x)
                            if isinstance(x, str) and x.startswith("{")
                            else None
                        )
                    )
                )

        return df

    def _transform_selection(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform selection table."""
        # Parse JSON fields
        if "meta" in df.columns:
            df["meta_parsed"] = df["meta"].apply(
                lambda x: (
                    x
                    if isinstance(x, dict)
                    else (
                        json.loads(x)
                        if isinstance(x, str) and x.startswith("{")
                        else None
                    )
                )
            )

        return df

    def _transform_moderation_scenario(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform moderation_scenario table."""
        return df

    def _transform_moderation_session(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform moderation_session table."""
        # Parse JSON fields
        json_cols = [
            "strategies",
            "custom_instructions",
            "highlighted_texts",
            "refactored_response",
            "session_metadata",
        ]
        for col in json_cols:
            if col in df.columns:
                df[f"{col}_parsed"] = df[col].apply(
                    lambda x: (
                        x
                        if isinstance(x, dict) or isinstance(x, list)
                        else (
                            json.loads(x)
                            if isinstance(x, str)
                            and (x.startswith("{") or x.startswith("["))
                            else None
                        )
                    )
                )

        return df

    def _transform_exit_quiz(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform exit_quiz_response table."""
        # Parse JSON fields
        for col in ["answers", "score", "meta"]:
            if col in df.columns:
                df[f"{col}_parsed"] = df[col].apply(
                    lambda x: (
                        x
                        if isinstance(x, dict)
                        else (
                            json.loads(x)
                            if isinstance(x, str) and x.startswith("{")
                            else None
                        )
                    )
                )

        return df


def find_dump_file() -> Optional[str]:
    """Find the dump file in common locations."""
    # Check command line argument
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            return sys.argv[1]

    # Check Downloads folder for the specific file
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
    """Main function."""
    dump_file = find_dump_file()

    if not dump_file:
        print("Error: Could not find dump file.")
        print("Please provide the path to the dump file as an argument, or")
        print("place it in one of these locations:")
        print("  - ~/Downloads/b078-20260113-215725.dump")
        print("  - /workspace/heroku_psql_181025.dump")
        print("  - ./heroku_psql_181025.dump")
        sys.exit(1)

    print(f"Using dump file: {dump_file}\n")

    # Parse dump
    parser = PostgresDumpParser(dump_file)
    raw_dataframes = parser.parse_dump()

    print(f"\nFound {len(raw_dataframes)} tables with data")

    # Transform data
    transformer = DataTransformer(raw_dataframes)
    transformed_dataframes = transformer.transform_all()

    # Save to files
    output_dir = Path("data_exports")
    output_dir.mkdir(exist_ok=True)

    print(f"\nSaving transformed DataFrames to {output_dir}/...")

    for table_name, df in transformed_dataframes.items():
        output_file = output_dir / f"{table_name}.csv"
        df.to_csv(output_file, index=False)
        print(f"  Saved {table_name}: {len(df)} rows -> {output_file}")

        # Also save as pickle for faster loading
        pickle_file = output_dir / f"{table_name}.pkl"
        df.to_pickle(pickle_file)

    # Create summary
    summary = {
        "dump_file": dump_file,
        "extraction_date": datetime.now().isoformat(),
        "tables": {},
    }

    for table_name, df in transformed_dataframes.items():
        summary["tables"][table_name] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        }

    summary_file = output_dir / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to {summary_file}")
    print("\nDone! You can now load the DataFrames using:")
    print("  import pandas as pd")
    print("  df = pd.read_pickle('data_exports/table_name.pkl')")

    return transformed_dataframes


if __name__ == "__main__":
    main()

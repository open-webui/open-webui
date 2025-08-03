#!/usr/bin/env python3
"""
Database Analysis Script for mAI Usage Tracking
Connects to both InfluxDB and SQLite to extract usage data after OpenRouter query.
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

# Try to import InfluxDB client
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.query_api import QueryApi
    INFLUXDB_AVAILABLE = True
except ImportError:
    print("InfluxDB client not available. Install with: pip install influxdb-client")
    INFLUXDB_AVAILABLE = False

class DatabaseAnalyzer:
    def __init__(self):
        # InfluxDB configuration from .env.dev
        self.influxdb_url = "http://localhost:8086"
        self.influxdb_token = "dev-token-for-testing-only"
        self.influxdb_org = "mAI-dev"
        self.influxdb_bucket = "mai_usage_raw_dev"
        self.influxdb_measurement = "usage_tracking"
        
        # SQLite configuration
        self.sqlite_path = "/app/backend/data/webui.db"  # Container path
        # Try to find the actual SQLite file in Docker volumes
        possible_sqlite_paths = [
            "/Users/patpil/Documents/Projects/mAI/backend/data/webui.db",
            "./backend/data/webui.db",
            "backend/data/webui.db"
        ]
        
        for path in possible_sqlite_paths:
            if os.path.exists(path):
                self.sqlite_path = path
                break
    
    def connect_to_influxdb(self) -> QueryApi:
        """Connect to InfluxDB and return query API"""
        if not INFLUXDB_AVAILABLE:
            return None
            
        try:
            client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            return client.query_api()
        except Exception as e:
            print(f"Failed to connect to InfluxDB: {e}")
            return None
    
    def query_influxdb_data(self) -> List[Dict[str, Any]]:
        """Query InfluxDB for usage tracking data from the last 2 hours"""
        query_api = self.connect_to_influxdb()
        if not query_api:
            return []
        
        # Query for data from the last 2 hours
        query = f'''
        from(bucket: "{self.influxdb_bucket}")
        |> range(start: -2h)
        |> filter(fn: (r) => r["_measurement"] == "{self.influxdb_measurement}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        try:
            result = query_api.query(query)
            data = []
            
            for table in result:
                for record in table.records:
                    row = {
                        'time': record.get_time(),
                        'measurement': record.get_measurement()
                    }
                    # Add all field values
                    for key, value in record.values.items():
                        if not key.startswith('_') and key not in ['result', 'table']:
                            row[key] = value
                    data.append(row)
            
            return data
        except Exception as e:
            print(f"Failed to query InfluxDB: {e}")
            return []
    
    def connect_to_sqlite(self) -> sqlite3.Connection:
        """Connect to SQLite database"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            return conn
        except Exception as e:
            print(f"Failed to connect to SQLite at {self.sqlite_path}: {e}")
            return None
    
    def query_sqlite_usage_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Query SQLite for usage tracking data from the last 2 hours"""
        conn = self.connect_to_sqlite()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            
            # Get data from the last 2 hours
            two_hours_ago = datetime.now() - timedelta(hours=2)
            timestamp_filter = two_hours_ago.strftime('%Y-%m-%d %H:%M:%S')
            
            # Query different usage tracking tables
            tables_and_queries = {
                'client_daily_usage': f"""
                    SELECT * FROM client_daily_usage 
                    WHERE date >= date('{timestamp_filter}')
                    ORDER BY date DESC, total_cost DESC
                """,
                'client_user_daily_usage': f"""
                    SELECT * FROM client_user_daily_usage 
                    WHERE date >= date('{timestamp_filter}')
                    ORDER BY date DESC, total_cost DESC
                """,
                'usage_logs': f"""
                    SELECT * FROM usage_logs 
                    WHERE created_at >= '{timestamp_filter}'
                    ORDER BY created_at DESC
                """ if self._table_exists(cursor, 'usage_logs') else None,
                'organizations': """
                    SELECT id, name, created_at, updated_at 
                    FROM organizations 
                    ORDER BY created_at DESC
                """ if self._table_exists(cursor, 'organizations') else None
            }
            
            results = {}
            for table_name, query in tables_and_queries.items():
                if query:
                    try:
                        cursor.execute(query)
                        rows = cursor.fetchall()
                        results[table_name] = [dict(row) for row in rows]
                    except Exception as e:
                        print(f"Error querying {table_name}: {e}")
                        results[table_name] = []
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Failed to query SQLite: {e}")
            if conn:
                conn.close()
            return {}
    
    def _table_exists(self, cursor: sqlite3.Cursor, table_name: str) -> bool:
        """Check if table exists in SQLite database"""
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    
    def get_sqlite_schema(self) -> Dict[str, List[str]]:
        """Get schema information for all tables"""
        conn = self.connect_to_sqlite()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                schema[table] = [f"{col[1]} ({col[2]})" for col in columns]
            
            conn.close()
            return schema
            
        except Exception as e:
            print(f"Failed to get SQLite schema: {e}")
            if conn:
                conn.close()
            return {}

def main():
    analyzer = DatabaseAnalyzer()
    
    print("=== mAI Database Analysis Report ===")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Analysis window: Last 2 hours")
    print()
    
    # Query InfluxDB
    print("🔍 Querying InfluxDB...")
    influxdb_data = analyzer.query_influxdb_data()
    print(f"Found {len(influxdb_data)} records in InfluxDB")
    
    # Query SQLite
    print("🔍 Querying SQLite...")
    sqlite_data = analyzer.query_sqlite_usage_data()
    sqlite_schema = analyzer.get_sqlite_schema()
    
    # Display results
    print("\n" + "="*80)
    print("INFLUXDB DATA")
    print("="*80)
    
    if influxdb_data:
        df_influx = pd.DataFrame(influxdb_data)
        print(df_influx.to_string(index=False))
    else:
        print("No data found in InfluxDB")
    
    print("\n" + "="*80)
    print("SQLITE DATA")
    print("="*80)
    
    for table_name, data in sqlite_data.items():
        print(f"\n--- {table_name.upper()} ---")
        if data:
            df_sqlite = pd.DataFrame(data)
            print(df_sqlite.to_string(index=False))
        else:
            print(f"No recent data found in {table_name}")
    
    print("\n" + "="*80)
    print("SQLITE SCHEMA")
    print("="*80)
    
    for table, columns in sqlite_schema.items():
        print(f"\n{table}:")
        for col in columns:
            print(f"  - {col}")
    
    # Create summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"InfluxDB records: {len(influxdb_data)}")
    total_sqlite_records = sum(len(data) for data in sqlite_data.values())
    print(f"SQLite records: {total_sqlite_records}")
    print(f"SQLite tables examined: {len(sqlite_data)}")

if __name__ == "__main__":
    main()
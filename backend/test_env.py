#!/usr/bin/env python3
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Environment Variable Check ===")
print(f"BACKEND_MSSQL_SERVER: {os.environ.get('BACKEND_MSSQL_SERVER', 'NOT SET')}")
print(f"BACKEND_MSSQL_DATABASE: {os.environ.get('BACKEND_MSSQL_DATABASE', 'NOT SET')}")
print(f"BACKEND_MSSQL_USERNAME: {os.environ.get('BACKEND_MSSQL_USERNAME', 'NOT SET')}")
print(f"BACKEND_MSSQL_PASSWORD: {'***' if os.environ.get('BACKEND_MSSQL_PASSWORD') else 'NOT SET'}")
print(f"DISABLE_MIGRATIONS: {os.environ.get('DISABLE_MIGRATIONS', 'NOT SET')}")

print("\n=== Testing Database URL Construction ===")
try:
    from open_webui.env import DATABASE_URL, BACKEND_MSSQL_SERVER, BACKEND_MSSQL_DATABASE
    print(f"DATABASE_URL constructed: {DATABASE_URL}")
    print(f"Is MS SQL URL: {'mssql' in DATABASE_URL}")
except Exception as e:
    print(f"Error importing env: {e}")

print("\n=== Testing Database Connection ===")
try:
    from open_webui.internal.db import engine
    print(f"Engine dialect: {engine.dialect.name}")
    
    # Try to connect
    from sqlalchemy import text
    with engine.connect() as conn:
        if 'mssql' in DATABASE_URL:
            result = conn.execute(text("SELECT @@VERSION"))
            print(f"SQL Server Version: {result.scalar()}")
        else:
            print("Not using MS SQL Server")
except Exception as e:
    print(f"Connection error: {e}")
#!/usr/bin/env python3
import os
import pyodbc
import urllib.parse

# Get credentials from environment
server = os.environ.get('BACKEND_MSSQL_SERVER', '')
database = os.environ.get('BACKEND_MSSQL_DATABASE', '')
username = os.environ.get('BACKEND_MSSQL_USERNAME', '')
password = os.environ.get('BACKEND_MSSQL_PASSWORD', '')

print(f"Testing connection to: {server}/{database}")

# Method 1: Direct pyodbc connection
try:
    print("\n=== Testing direct pyodbc connection ===")
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no"
    )
    
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    result = cursor.fetchone()
    print(f"Success! SQL Server Version: {result[0][:50]}...")
    
    # Test JSON support
    cursor.execute("""
        SELECT * FROM OPENJSON('["test1", "test2"]')
    """)
    print("JSON support confirmed")
    
    conn.close()
    
except Exception as e:
    print(f"Direct connection error: {e}")

# Method 2: SQLAlchemy connection
try:
    print("\n=== Testing SQLAlchemy connection ===")
    from sqlalchemy import create_engine, text
    
    # URL encode the password
    password_encoded = urllib.parse.quote_plus(password)
    
    # Try different connection string formats
    urls = [
        # Format 1: With URL encoding
        f"mssql+pyodbc://{username}:{password_encoded}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no",
        
        # Format 2: Without some options
        f"mssql+pyodbc://{username}:{password_encoded}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server",
    ]
    
    for i, url in enumerate(urls):
        try:
            print(f"\nTrying format {i+1}...")
            engine = create_engine(url, echo=False)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT @@VERSION"))
                print(f"Success with format {i+1}!")
                print(f"SQL Server Version: {result.scalar()[:50]}...")
                break
        except Exception as e:
            print(f"Format {i+1} error: {e}")
            
except Exception as e:
    print(f"SQLAlchemy error: {e}")

print("\n=== ODBC Drivers Available ===")
try:
    drivers = [x for x in pyodbc.drivers() if 'SQL Server' in x]
    for driver in drivers:
        print(f"  - {driver}")
except Exception as e:
    print(f"Error listing drivers: {e}")
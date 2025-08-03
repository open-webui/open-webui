#!/usr/bin/env python3
"""Test InfluxDB query to see if data is being written"""

import os
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta

# InfluxDB configuration from environment
INFLUXDB_URL = "http://mai-influxdb-dev:8086"
INFLUXDB_TOKEN = "dev-token-for-testing-only"
INFLUXDB_ORG = "mAI-dev"
INFLUXDB_BUCKET = "mai_usage_raw_dev"

# Create client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

# Query for recent data (last 24 hours)
query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "usage_tracking")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 10)
'''

print(f"Querying InfluxDB for recent usage data...")
print(f"URL: {INFLUXDB_URL}")
print(f"Bucket: {INFLUXDB_BUCKET}")
print(f"Measurement: usage_tracking")
print("-" * 50)

try:
    result = query_api.query(query)
    
    record_count = 0
    for table in result:
        for record in table.records:
            record_count += 1
            print(f"\nRecord {record_count}:")
            print(f"  Time: {record.get_time()}")
            print(f"  Model: {record.values.get('model', 'N/A')}")
            print(f"  Tokens: {record.get_value()}")
            print(f"  Field: {record.get_field()}")
            print(f"  Client: {record.values.get('client_org_id', 'N/A')}")
            print(f"  User: {record.values.get('user_email', 'N/A')}")
    
    if record_count == 0:
        print("\nNo records found in the last 24 hours.")
        print("\nTrying to query all data...")
        
        # Try without time filter
        query_all = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: 0)
          |> filter(fn: (r) => r._measurement == "usage_tracking")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 5)
        '''
        
        result_all = query_api.query(query_all)
        for table in result_all:
            for record in table.records:
                record_count += 1
                print(f"\nAll-time Record:")
                print(f"  Time: {record.get_time()}")
                print(f"  Field: {record.get_field()}")
                print(f"  Value: {record.get_value()}")
        
        if record_count == 0:
            print("\nNo records found in InfluxDB at all.")
    else:
        print(f"\n\nTotal records found: {record_count}")
        
except Exception as e:
    print(f"\nError querying InfluxDB: {e}")
    print(f"Error type: {type(e).__name__}")
    
finally:
    client.close()
#!/usr/bin/env python3
"""Simple test for webhook processing with InfluxDB-First"""

import requests
import json
import time

# Test webhook payload
webhook_payload = {
    "model": "gpt-4o-mini",
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150,
    "cost": 0.0015,
    "user_email": "test@example.com",
    "client_org_id": "Org_succes_C",
    "request_id": f"test_request_{int(time.time())}"
}

print("Testing webhook processing with InfluxDB-First...")
print(f"Payload: {json.dumps(webhook_payload, indent=2)}")
print("-" * 50)

try:
    # Test webhook endpoint (without authentication for simplicity)
    response = requests.post(
        "http://localhost:8080/api/v1/webhooks/openrouter",
        json=webhook_payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("✅ Webhook processing successful!")
    else:
        print(f"❌ Webhook failed with status {response.status_code}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")

print("\nNow checking if data was written to InfluxDB...")

# Wait a moment for data to be written
time.sleep(2)

# Check InfluxDB for the data
try:
    from influxdb_client import InfluxDBClient
    from datetime import datetime, timedelta
    
    client = InfluxDBClient(
        url="http://localhost:8086",
        token="dev-token-for-testing-only",
        org="mAI-dev"
    )
    query_api = client.query_api()
    
    # Query for the test data
    query = f'''
    from(bucket: "mai_usage_raw_dev")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "usage_tracking")
    |> filter(fn: (r) => r.client_org_id == "Org_succes_C")
    |> filter(fn: (r) => r.request_id == "{webhook_payload['request_id']}")
    '''
    
    result = query_api.query(query)
    
    if result:
        print("✅ Data found in InfluxDB!")
        for table in result:
            for record in table.records:
                print(f"   {record.get_field()}: {record.get_value()}")
    else:
        print("❌ No data found in InfluxDB")
        
except Exception as e:
    print(f"❌ InfluxDB query failed: {e}")

print("-" * 50)
print("Webhook test complete!")
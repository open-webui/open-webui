#!/usr/bin/env python3
import httpx
import json

try:
    with httpx.Client() as client:
        response = client.get('http://localhost:8080/api/v1/usage-tracking/service-status')
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: Status code {response.status_code}")
            print(response.text)
except Exception as e:
    print(f"Error: {e}")
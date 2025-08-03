#!/usr/bin/env python3
"""Test NBP service API"""

import requests
import json

# Test the NBP service
response = requests.get("http://localhost:8001/api/usd-pln-rate")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Also test health endpoint
health = requests.get("http://localhost:8001/health")
print(f"\nHealth status: {health.json()}")
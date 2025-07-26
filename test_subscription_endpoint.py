#!/usr/bin/env python3
import requests
import json

# Test the subscription billing endpoint
url = "http://localhost:3002/api/v1/usage-tracking/my-organization/subscription-billing"

# You need to get a valid token first - this is just for testing
# In production, this would come from the authenticated user session
headers = {
    "Content-Type": "application/json"
}

print("Testing subscription billing endpoint...")
print(f"URL: {url}")

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
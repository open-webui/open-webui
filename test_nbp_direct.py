#!/usr/bin/env python3
"""
Direct test of NBP API using Python requests
"""

import requests
import json
from datetime import date, timedelta

def test_nbp_api_direct():
    """Test NBP API directly with HTTP requests"""
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    print("=" * 60)
    print("🔍 Direct NBP API HTTP Test")
    print("=" * 60)
    
    base_url = "https://api.nbp.pl/api/exchangerates/tables/a"
    headers = {
        "Accept": "application/json",
        "User-Agent": "mAI/1.0"
    }
    
    # Test today's rate
    print(f"\n📅 Testing today ({today}):")
    today_url = f"{base_url}/{today.isoformat()}/"
    try:
        response = requests.get(today_url, headers=headers, timeout=10)
        print(f"  URL: {today_url}")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                table = data[0]
                rates = table.get('rates', [])
                for rate in rates:
                    if rate.get('code') == 'USD':
                        print(f"  ✅ USD Rate: {rate.get('mid')}")
                        print(f"  Effective Date: {table.get('effectiveDate')}")
                        print(f"  Table No: {table.get('no')}")
                        break
            else:
                print(f"  ❌ Empty response data")
        elif response.status_code == 404:
            print(f"  ❌ No data available (404)")
        else:
            print(f"  ❌ Error: HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
    
    # Test yesterday's rate
    print(f"\n📅 Testing yesterday ({yesterday}):")
    yesterday_url = f"{base_url}/{yesterday.isoformat()}/"
    try:
        response = requests.get(yesterday_url, headers=headers, timeout=10)
        print(f"  URL: {yesterday_url}")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                table = data[0]
                rates = table.get('rates', [])
                for rate in rates:
                    if rate.get('code') == 'USD':
                        print(f"  ✅ USD Rate: {rate.get('mid')}")
                        print(f"  Effective Date: {table.get('effectiveDate')}")
                        print(f"  Table No: {table.get('no')}")
                        break
            else:
                print(f"  ❌ Empty response data")
        elif response.status_code == 404:
            print(f"  ❌ No data available (404)")
        else:
            print(f"  ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
    
    # Test current rate (no date specified)
    print(f"\n📅 Testing current rate (no date):")
    current_url = f"{base_url}/"
    try:
        response = requests.get(current_url, headers=headers, timeout=10)
        print(f"  URL: {current_url}")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                table = data[0]
                rates = table.get('rates', [])
                for rate in rates:
                    if rate.get('code') == 'USD':
                        print(f"  ✅ USD Rate: {rate.get('mid')}")
                        print(f"  Effective Date: {table.get('effectiveDate')}")
                        print(f"  Table No: {table.get('no')}")
                        break
            else:
                print(f"  ❌ Empty response data")
        else:
            print(f"  ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ❌ Request failed: {e}")

if __name__ == "__main__":
    test_nbp_api_direct()
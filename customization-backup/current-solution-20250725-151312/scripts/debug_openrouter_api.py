#!/usr/bin/env python3
"""
Debug OpenRouter API connectivity and endpoints
Tests different endpoints and methods to find the correct API structure
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

# Your Org_B Provisioning Key
ORG_B_PROVISIONING_KEY = "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"

def test_api_endpoint(method, endpoint, data=None, description=""):
    """Test a specific API endpoint"""
    print(f"\n🔍 Testing: {description}")
    print(f"   Method: {method}")
    print(f"   Endpoint: {endpoint}")
    
    headers = {
        "Authorization": f"Bearer {ORG_B_PROVISIONING_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "mAI-Client/1.0"
    }
    
    try:
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(endpoint, data=json_data, headers=headers, method=method)
        else:
            req = urllib.request.Request(endpoint, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            response_text = response.read().decode('utf-8')
            status_code = response.getcode()
            
            print(f"   ✅ Status: {status_code}")
            if status_code in [200, 201]:
                try:
                    response_data = json.loads(response_text)
                    print(f"   📄 Response: {json.dumps(response_data, indent=2)[:500]}...")
                    return True, response_data
                except:
                    print(f"   📄 Response (raw): {response_text[:200]}...")
                    return True, response_text
            else:
                print(f"   ⚠️ Unexpected status: {status_code}")
                print(f"   📄 Response: {response_text}")
                return False, response_text
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"   ❌ HTTP Error {e.code}: {error_body}")
        return False, f"HTTP {e.code}: {error_body}"
    except urllib.error.URLError as e:
        print(f"   ❌ URL Error: {e}")
        return False, str(e)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, str(e)

def main():
    print("=" * 70)
    print("🔍 OPENROUTER API DIAGNOSTIC TOOL")
    print("=" * 70)
    print(f"Provisioning Key: {ORG_B_PROVISIONING_KEY[:20]}...{ORG_B_PROVISIONING_KEY[-10:]}")
    
    # Test 1: Basic connectivity to OpenRouter
    print(f"\n" + "=" * 50)
    print("PHASE 1: BASIC CONNECTIVITY")
    print("=" * 50)
    
    success, _ = test_api_endpoint(
        "GET", 
        "https://openrouter.ai/api/v1/models",
        description="Public models endpoint (no auth required)"
    )
    
    if not success:
        print("\n❌ BASIC CONNECTIVITY FAILED")
        print("Network or OpenRouter service might be down")
        return
    
    # Test 2: Authentication test
    print(f"\n" + "=" * 50)
    print("PHASE 2: AUTHENTICATION TESTS")
    print("=" * 50)
    
    # Try the standard keys endpoint
    test_api_endpoint(
        "GET",
        "https://openrouter.ai/api/v1/keys",
        description="List existing keys (standard endpoint)"
    )
    
    # Try without trailing slash
    test_api_endpoint(
        "GET",
        "https://openrouter.ai/api/v1/keys/",
        description="List existing keys (with trailing slash)"
    )
    
    # Try generation endpoint
    test_api_endpoint(
        "GET",
        "https://openrouter.ai/api/v1/generation",
        description="Generation stats endpoint"
    )
    
    # Test 3: Different possible key creation endpoints
    print(f"\n" + "=" * 50)
    print("PHASE 3: KEY CREATION ENDPOINT TESTS")
    print("=" * 50)
    
    test_data = {
        "name": "Test API Key",
        "label": "test-diagnostic",
        "limit": 1.0
    }
    
    endpoints_to_test = [
        "https://openrouter.ai/api/v1/keys",
        "https://openrouter.ai/api/v1/keys/",
        "https://openrouter.ai/api/v1/keys/create",
        "https://openrouter.ai/api/v1/auth/keys",
        "https://openrouter.ai/api/v1/auth/keys/",
        "https://openrouter.ai/api/v1/user/keys",
        "https://openrouter.ai/api/v1/admin/keys",
    ]
    
    for endpoint in endpoints_to_test:
        test_api_endpoint(
            "POST",
            endpoint,
            data=test_data,
            description=f"Create key via {endpoint}"
        )
    
    # Test 4: Check account info
    print(f"\n" + "=" * 50)
    print("PHASE 4: ACCOUNT INFORMATION")
    print("=" * 50)
    
    test_api_endpoint(
        "GET",
        "https://openrouter.ai/api/v1/auth/key",
        description="Get current key info"
    )
    
    test_api_endpoint(
        "GET",
        "https://openrouter.ai/api/v1/credits",
        description="Get account credits"
    )
    
    print(f"\n" + "=" * 70)
    print("🎯 DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print("Check the results above to identify the correct endpoint and method.")
    print("Look for any successful responses that show the correct API structure.")

if __name__ == "__main__":
    main()
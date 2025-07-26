#!/usr/bin/env python3
"""
Test the actual API endpoints that the frontend calls
"""

import requests
import json

def test_usage_api_endpoints():
    """Test the usage API endpoints directly"""
    print("🧪 Testing Usage API Endpoints Directly")
    print("=" * 50)
    
    base_url = "http://localhost:3002"
    
    # Note: These endpoints require authentication, so we'll test basic connectivity first
    endpoints = [
        "/api/v1/usage-tracking/my-organization/usage-by-user",
        "/api/v1/usage-tracking/my-organization/usage-by-model", 
        "/api/v1/usage-tracking/model-pricing"
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n🔗 Testing: {endpoint}")
        
        try:
            # Test without authentication first to see if endpoint exists
            response = requests.get(url, timeout=10)
            
            if response.status_code == 401:
                print(f"   ✅ Endpoint exists (401 Unauthorized - expected without auth)")
            elif response.status_code == 200:
                print(f"   ✅ Endpoint accessible (200 OK)")
                try:
                    data = response.json()
                    print(f"   📊 Response preview: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   📊 Response length: {len(response.text)} chars")
            elif response.status_code == 404:
                print(f"   ❌ Endpoint not found (404)")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                print(f"   📝 Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - Docker container not accessible")
        except requests.exceptions.Timeout:
            print(f"   ❌ Request timeout")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_docker_container_health():
    """Test if Docker container is healthy and accessible"""
    print(f"\n🐳 Docker Container Health Check")
    print("-" * 40)
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:3002/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Container is healthy and accessible")
        else:
            print(f"   ⚠️  Health check returned: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Container not accessible: {e}")
    
    # Test basic web interface
    try:
        response = requests.get("http://localhost:3002/", timeout=5)
        if response.status_code == 200:
            print("   ✅ Web interface accessible")
        else:
            print(f"   ⚠️  Web interface status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Web interface not accessible: {e}")

def debug_backend_logs():
    """Show recent backend logs for debugging"""
    print(f"\n📋 Recent Backend Logs")
    print("-" * 40)
    print("   💡 Run this command to see live logs:")
    print("   docker logs open-webui-customization --tail=50 -f")
    print()
    print("   🔍 Look for:")
    print("   - API request logs for /usage-tracking/ endpoints")
    print("   - Database connection errors")  
    print("   - Client organization lookup errors")
    print("   - Any Python exceptions or errors")

if __name__ == "__main__":
    test_docker_container_health()
    test_usage_api_endpoints()
    debug_backend_logs()
    
    print(f"\n💡 NEXT STEPS:")
    print("1. Check Docker logs: docker logs open-webui-customization --tail=20")
    print("2. Test endpoints with authentication (login to web interface first)")
    print("3. Check browser Network tab when accessing Usage Settings")
    print("4. Verify backend is processing the API requests correctly")
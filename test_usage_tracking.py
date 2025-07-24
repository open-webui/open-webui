#!/usr/bin/env python3
"""
Test script for the new usage tracking system
"""

import requests
import json
import time

# Configuration
CONTAINER_NAME = "open-webui-customization"
BASE_URL = "http://localhost:3000"  # Adjust if your container uses different port

def test_manual_sync():
    """Test manual usage sync"""
    print("🧪 Testing manual usage sync...")
    
    # First, record some test usage
    response = requests.post(
        f"{BASE_URL}/api/v1/usage-tracking/usage/manual-record",
        json={
            "model": "deepseeka-ai/deepseek-v3",
            "tokens": 1751,
            "cost": 0.00118698
        },
        headers={"Authorization": "Bearer your-admin-token"}  # You'll need real token
    )
    
    if response.status_code == 200:
        print("✅ Manual usage recording successful")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Manual usage recording failed: {response.status_code}")
        print(response.text)

def test_sync_endpoint():
    """Test the sync endpoint"""
    print("\n🧪 Testing OpenRouter sync endpoint...")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/usage-tracking/sync/openrouter-usage",
        json={"days_back": 1},
        headers={"Authorization": "Bearer your-admin-token"}  # You'll need real token
    )
    
    if response.status_code == 200:
        print("✅ OpenRouter sync successful")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ OpenRouter sync failed: {response.status_code}")
        print(response.text)

def test_real_time_usage():
    """Test real-time usage retrieval"""
    print("\n🧪 Testing real-time usage retrieval...")
    
    # You'll need to get the actual client_org_id from your database
    client_org_id = "your-org-id"  # Replace with actual org ID
    
    response = requests.get(
        f"{BASE_URL}/api/v1/usage-tracking/usage/real-time/{client_org_id}",
        headers={"Authorization": "Bearer your-admin-token"}  # You'll need real token
    )
    
    if response.status_code == 200:
        print("✅ Real-time usage retrieval successful")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Real-time usage retrieval failed: {response.status_code}")
        print(response.text)

def check_container_status():
    """Check if the container is running"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "table {{.Names}}\\t{{.Status}}"],
            capture_output=True,
            text=True
        )
        
        if CONTAINER_NAME in result.stdout:
            print(f"✅ Container {CONTAINER_NAME} is running")
            return True
        else:
            print(f"❌ Container {CONTAINER_NAME} is not running")
            return False
    except Exception as e:
        print(f"❌ Error checking container status: {e}")
        return False

if __name__ == "__main__":
    print("🚀 mAI Usage Tracking Test Suite")
    print("=" * 50)
    
    # Check container status first
    if not check_container_status():
        print("\n💡 To start the container:")
        print(f"   docker start {CONTAINER_NAME}")
        exit(1)
    
    print(f"\n🔗 Testing against: {BASE_URL}")
    print("📝 Note: You'll need to update the admin token and org ID in this script")
    
    # Run tests
    test_manual_sync()
    test_sync_endpoint() 
    test_real_time_usage()
    
    print("\n✅ Test suite completed!")
    print("\n📋 Next steps:")
    print("1. Update this script with your actual admin token")
    print("2. Get your organization ID from the database")
    print("3. Check the Usage tab in mAI Admin Panel")
    print("4. Verify background sync is working in Docker logs")
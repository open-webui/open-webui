#!/usr/bin/env python3
"""
Test script for govGpt-file-search-service integration
"""

import requests
import json
import sys

def test_govgpt_service():
    """
    Test the govGpt-file-search-service integration
    """
    
    print("🧪 Testing GovGPT File Search Service Integration")
    print("=" * 50)
    
    # Test 1: Check if the external service is accessible
    print("\n1. Testing external service connectivity...")
    try:
        response = requests.post(
            "http://40.119.184.8:8102/query",
            headers={"Content-Type": "application/json"},
            json={
                "user_query": "test query",
                "user_id": "test_user",
                "user_name": "Test User",
                "session_id": "test_session",
                "chat_history": [],
                "document_text": "This is a test document for integration testing."
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ External service is accessible")
            print(f"   Response: {result.get('response', 'No response')}")
        else:
            print(f"❌ External service returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ External service not accessible: {e}")
        return False
    
    # Test 2: Check if the Open WebUI backend is running
    print("\n2. Testing Open WebUI backend...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ Open WebUI backend is running")
        else:
            print(f"❌ Open WebUI backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Open WebUI backend not accessible: {e}")
        return False
    
    # Test 3: Check environment configuration
    print("\n3. Checking environment configuration...")
    try:
        response = requests.get("http://localhost:8080/api/v1/custom-qa/config", timeout=5)
        if response.status_code == 200:
            config = response.json()
            print(f"✅ Custom QA config endpoint accessible")
            print(f"   Enabled: {config.get('enabled', 'Unknown')}")
        else:
            print(f"⚠️  Custom QA config endpoint returned status {response.status_code}")
            print("   (This is normal if you don't have admin access)")
    except Exception as e:
        print(f"⚠️  Custom QA config endpoint not accessible: {e}")
        print("   (This is normal if you don't have admin access)")
    
    print("\n🎉 Integration test completed!")
    print("\nNext steps:")
    print("1. Upload a document to the chat interface")
    print("2. Ask a question about the document")
    print("3. Check the backend logs for messages like:")
    print("   'govGpt-file-search-service response integrated for user [user_id]'")
    
    return True

if __name__ == "__main__":
    success = test_govgpt_service()
    sys.exit(0 if success else 1) 
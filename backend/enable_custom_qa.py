#!/usr/bin/env python3
"""
Script to enable the custom QA API integration
"""

import requests
import json
import sys

def enable_custom_qa_api(base_url="http://localhost:8080", admin_token=None):
    """
    Enable the govGpt-file-search-service integration
    
    Note: You can also enable this service by setting ENABLE_GOVGPT_FILE_SEARCH=true
    in your .env file and restarting the backend.
    
    Args:
        base_url: The base URL of the Open WebUI API
        admin_token: Admin token for authentication
    """
    
    if not admin_token:
        print("Error: Admin token is required")
        print("Please provide your admin token:")
        admin_token = input().strip()
    
    if not admin_token:
        print("Error: No admin token provided")
        sys.exit(1)
    
    # Enable the custom QA API
    url = f"{base_url}/api/v1/custom-qa/config"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    }
    data = {"enabled": True}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ govGpt-file-search-service enabled successfully!")
            print(f"Status: {result.get('enabled', 'Unknown')}")
        else:
            print(f"❌ Failed to enable govGpt-file-search-service")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to API: {e}")
        sys.exit(1)

def check_custom_qa_status(base_url="http://localhost:8080", admin_token=None):
    """
    Check the current status of the govGpt-file-search-service
    
    Note: The service can also be enabled via ENABLE_GOVGPT_FILE_SEARCH=true
    in your .env file.
    """
    
    if not admin_token:
        print("Error: Admin token is required")
        print("Please provide your admin token:")
        admin_token = input().strip()
    
    url = f"{base_url}/api/v1/custom-qa/config"
    headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            status = "✅ Enabled" if result.get('enabled') else "❌ Disabled"
            print(f"govGpt-file-search-service Status: {status}")
        else:
            print(f"❌ Failed to check status")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to API: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GovGPT File Search Service Management")
    parser.add_argument("--base-url", default="http://localhost:8080", 
                       help="Base URL of the Open WebUI API")
    parser.add_argument("--token", help="Admin token for authentication")
    parser.add_argument("--check", action="store_true", 
                       help="Check current status instead of enabling")
    
    args = parser.parse_args()
    
    if args.check:
        check_custom_qa_status(args.base_url, args.token)
    else:
        enable_custom_qa_api(args.base_url, args.token) 
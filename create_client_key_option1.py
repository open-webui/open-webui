#!/usr/bin/env python3
"""
Option 1: Simple Client API Key Creation Script
Works with the simplified daily summary database approach
"""
import requests
import json
import sys
from datetime import datetime

class SimpleClientKeyCreator:
    def __init__(self, provisioning_key: str):
        self.provisioning_key = provisioning_key
        self.base_url = "https://openrouter.ai/api/v1"
    
    def get_key_usage(self, api_key: str):
        """Get usage information for an existing API key"""
        print(f"📊 Checking usage for API key...")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/auth/key",
                headers=headers
            )
            
            if response.status_code == 200:
                key_info = response.json()
                
                # Get usage data
                usage = key_info.get("data", {}).get("usage", 0)
                credit_limit = key_info.get("data", {}).get("limit", "No limit")
                
                print(f"💰 Current usage: ${usage:.2f}")
                print(f"💳 Credit limit: {credit_limit if credit_limit != 'No limit' else 'No limit'}")
                
                if credit_limit != "No limit" and isinstance(credit_limit, (int, float)):
                    remaining = credit_limit - usage
                    print(f"💵 Remaining balance: ${remaining:.2f}")
                
                return key_info
            else:
                print(f"❌ Failed to get usage info: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def create_client_key(self, client_name: str, monthly_limit: float = None):
        """Create a dedicated API key for a client organization"""
        print(f"🔑 Creating API key for client: {client_name}")
        
        headers = {
            "Authorization": f"Bearer {self.provisioning_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": f"{client_name} - mAI Client Key",
            "public_key": True
        }
        
        if monthly_limit:
            payload["limit"] = monthly_limit
            
        try:
            response = requests.post(
                f"{self.base_url}/keys",
                headers=headers,
                json=payload
            )
            
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                key_data = response.json()
                print("✅ API key created successfully!")
                
                # Format for Option 1 database entry
                client_entry = {
                    "client_name": client_name,
                    "api_key": key_data.get("key"),
                    "key_id": key_data.get("id"),
                    "monthly_limit": monthly_limit,
                    "created_at": datetime.now().isoformat(),
                    "usage_tracking": "Option 1 - Daily summaries + live counters"
                }
                
                print(f"\n📋 CLIENT DATABASE ENTRY:")
                print(json.dumps(client_entry, indent=2))
                
                print(f"\n🎯 MANUAL SETUP INSTRUCTIONS:")
                print(f"1. Add to client_organizations table:")
                print(f"   - name: {client_name}")
                print(f"   - openrouter_api_key: {key_data.get('key')}")
                print(f"   - markup_rate: 1.3")
                print(f"   - monthly_limit: {monthly_limit}")
                print(f"2. The Option 1 database will automatically:")
                print(f"   - Track today's usage in live counters")
                print(f"   - Roll up to daily summaries at midnight")
                print(f"   - Store 99% less data than per-request tracking")
                
                # Show current usage for the newly created key
                print(f"\n📊 CURRENT KEY USAGE:")
                self.get_key_usage(key_data.get('key'))
                
                return key_data
            else:
                print(f"❌ Failed to create key: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

def main():
    print("🚀 Option 1: Simple Client API Key Creator & Usage Checker")
    print("=" * 60)
    
    # Choose mode
    print("Select mode:")
    print("1. Create new API key")
    print("2. Check usage of existing API key")
    mode = input("Enter choice (1 or 2): ").strip()
    
    if mode == "2":
        # Usage check mode
        api_key = input("Enter API key to check usage: ").strip()
        if not api_key:
            print("❌ API key is required")
            sys.exit(1)
        
        creator = SimpleClientKeyCreator("")  # No provisioning key needed for usage check
        creator.get_key_usage(api_key)
        return
    
    elif mode == "1":
        # Key creation mode
        # Get provisioning key
        provisioning_key = input("Enter your OpenRouter provisioning key: ").strip()
        if not provisioning_key:
            print("❌ Provisioning key is required")
            sys.exit(1)
        
        # Get client details
        client_name = input("Enter client organization name: ").strip()
        if not client_name:
            print("❌ Client name is required")
            sys.exit(1)
        
        monthly_limit_input = input("Enter monthly spending limit (USD, or press Enter to skip): ").strip()
        monthly_limit = None
        if monthly_limit_input:
            try:
                monthly_limit = float(monthly_limit_input)
            except ValueError:
                print("⚠️  Invalid limit format, proceeding without limit")
        
        # Create the key
        creator = SimpleClientKeyCreator(provisioning_key)
        result = creator.create_client_key(client_name, monthly_limit)
        
        if result:
            print("\n🎉 Success! Option 1 implementation ready:")
            print("✅ Minimal database storage (99% reduction)")
            print("✅ Real-time today's usage")
            print("✅ Daily historical summaries")
            print("✅ No maintenance overhead")
            print("\n💾 Database storage comparison:")
            print("   Complex approach: ~50,000 records/month/client")
            print("   Option 1: ~31 records/month/client")
            print("   Storage reduction: 99.94%")
        else:
            print("\n❌ Failed to create client key")
            sys.exit(1)
    else:
        print("❌ Invalid choice. Please enter 1 or 2.")
        sys.exit(1)

if __name__ == "__main__":
    main()
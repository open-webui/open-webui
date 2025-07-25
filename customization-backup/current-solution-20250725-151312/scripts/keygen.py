#!/usr/bin/env python3
"""
Simple Interactive API Key Generator
Just run it and answer the questions
"""

import sys
import json
import urllib.request
from datetime import datetime

def create_api_key(provisioning_key, org_name, limit):
    """Create API key via OpenRouter"""
    headers = {
        "Authorization": f"Bearer {provisioning_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": f"mAI Client: {org_name}",
        "label": f"client-{org_name.lower().replace(' ', '-')}"
    }
    
    if limit > 0:
        data["limit"] = limit
    
    try:
        url = "https://openrouter.ai/api/v1/keys"
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.getcode() in [200, 201]:
                response_data = json.loads(response.read().decode('utf-8'))
                if "data" in response_data and "key" in response_data:
                    return response_data["key"], response_data["data"]["hash"]
    except:
        pass
    
    return None, None

def main():
    print("🔑 mAI API Key Generator")
    print("=" * 30)
    
    # Get provisioning key
    while True:
        provisioning_key = input("Provisioning API Key: ").strip()
        if provisioning_key and provisioning_key.startswith("sk-or-v1-"):
            break
        print("❌ Enter valid provisioning key (starts with sk-or-v1-)")
    
    # Get organization name
    while True:
        org_name = input("Organization name: ").strip()
        if org_name and len(org_name) >= 2:
            break
        print("❌ Name must be at least 2 characters")
    
    # Get spending limit
    while True:
        limit_input = input("Monthly limit ($ or 'unlimited'): ").strip().lower()
        
        if limit_input in ['unlimited', 'none', '0', '']:
            limit = 0
            limit_text = "Unlimited"
            break
        else:
            try:
                # Remove $ symbol if present
                limit_input = limit_input.replace('$', '').replace(',', '')
                limit = float(limit_input)
                if limit > 0:
                    limit_text = f"${limit:,.0f}/month"
                    break
                else:
                    limit = 0
                    limit_text = "Unlimited"
                    break
            except ValueError:
                print("❌ Enter a number, $ amount, or 'unlimited'")
    
    # Confirm
    print(f"\n📋 Summary:")
    print(f"   Provisioning Key: {provisioning_key[:20]}...{provisioning_key[-10:]}")
    print(f"   Organization: {org_name}")
    print(f"   Limit: {limit_text}")
    
    confirm = input("\nGenerate API key? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Cancelled")
        return
    
    # Generate key
    print("\n🔄 Generating API key...")
    api_key, key_hash = create_api_key(provisioning_key, org_name, limit)
    
    if api_key:
        print(f"\n✅ Success!")
        print(f"Organization: {org_name}")
        print(f"API Key: {api_key}")
        print(f"Limit: {limit_text}")
        print(f"\n📋 Instructions for client:")
        print(f"1. Open mAI → Settings → Connections")
        print(f"2. Add OpenRouter connection:")
        print(f"   URL: https://openrouter.ai/api/v1")
        print(f"   API Key: {api_key}")
        print(f"3. Click Save")
        print(f"4. Done! Tracking starts automatically")
        
        # Save to file
        filename = f"client_{org_name.replace(' ', '_').lower()}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(f"Organization: {org_name}\n")
                f.write(f"API Key: {api_key}\n")
                f.write(f"Limit: {limit_text}\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"\nClient Setup:\n")
                f.write(f"1. mAI → Settings → Connections\n")
                f.write(f"2. Add OpenRouter: https://openrouter.ai/api/v1\n")
                f.write(f"3. API Key: {api_key}\n")
                f.write(f"4. Save\n")
            print(f"\n💾 Saved to: {filename}")
        except:
            print(f"\n⚠️ Could not save file")
    else:
        print(f"\n❌ Failed to generate API key")
        print(f"Check your internet connection and try again")

if __name__ == "__main__":
    main()
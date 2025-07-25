#!/usr/bin/env python3
"""
Simple Client API Key Generator
Uses only standard library - no external dependencies required
"""

import sys
import json
import urllib.request
import urllib.parse
import argparse
from datetime import datetime

# Your Org_B Provisioning Key
ORG_B_PROVISIONING_KEY = "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"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

def create_client_api_key(client_name: str, monthly_limit: float = 1000.0):
    """Create API key for client organization using OpenRouter Provisioning API"""
    
    print(f"🏢 Creating API key for: {client_name}")
    print(f"💰 Monthly limit: ${monthly_limit}")
    
    headers = {
        "Authorization": f"Bearer {ORG_B_PROVISIONING_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": f"Client: {client_name}",
        "label": f"client-{client_name.lower().replace(' ', '-').replace('_', '-')}",
        "limit": monthly_limit
    }
    
    try:
        print("📞 Calling OpenRouter API...")
        print(f"   Request: Create key for '{client_name}' with ${monthly_limit} limit")
        
        # Prepare the request
        url = f"{OPENROUTER_API_BASE}/keys"
        json_data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        # Make the request
        with urllib.request.urlopen(req, timeout=30) as response:
            response_text = response.read().decode('utf-8')
            status_code = response.getcode()
            
            if status_code in [200, 201]:
                try:
                    response_data = json.loads(response_text)
                except Exception as json_error:
                    print(f"❌ Failed to parse JSON response: {json_error}")
                    print(f"   Response: {response_text}")
                    return None
                
                print(f"✅ Received response from OpenRouter")
                
                # Handle OpenRouter response format
                # Response format: {"data": {...}, "key": "sk-or-v1-..."}
                if "data" in response_data and "key" in response_data:
                    key_data = response_data["data"]
                    api_key = response_data["key"]  # The actual API key is at root level
                    print(f"   Response fields: {list(key_data.keys())}")
                    print(f"   Found API key: {api_key[:20]}...{api_key[-10:]}")
                    
                    key_hash = key_data.get("hash")
                    key_name = key_data.get("name")
                    
                    print(f"✅ API key generated successfully!")
                    print(f"   API Key: {api_key[:20]}...{api_key[-10:]}")
                    print(f"   Key Hash: {key_hash}")
                    
                    return {
                        "client_name": client_name,
                        "api_key": api_key,
                        "key_hash": key_hash,
                        "key_name": key_name,
                        "monthly_limit": monthly_limit
                    }
                else:
                    print(f"❌ Unexpected response format: {response_data}")
                    return None
                    
            else:
                print(f"❌ OpenRouter API error: {status_code} - {response_text}")
                return None
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ HTTP Error {e.code}: {error_body}")
        return None
    except urllib.error.URLError as e:
        print(f"❌ URL Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Create OpenRouter API key for client (Simple)")
    parser.add_argument("client_name", help="Name of the client organization")
    parser.add_argument("--limit", type=float, default=1000.0, help="Monthly limit in USD (default: 1000)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔑 SIMPLE CLIENT API KEY GENERATOR")
    print("=" * 60)
    print(f"📋 Provisioning Key: {ORG_B_PROVISIONING_KEY[:20]}...{ORG_B_PROVISIONING_KEY[-10:]}")
    print(f"🏢 Client: {args.client_name}")
    print(f"💰 Monthly Limit: ${args.limit}")
    
    result = create_client_api_key(args.client_name, args.limit)
    
    if result:
        print(f"\n" + "=" * 60)
        print(f"🎉 SUCCESS - API KEY GENERATED")
        print(f"=" * 60)
        print(f"")
        print(f"📋 CLIENT INFORMATION:")
        print(f"   Name: {result['client_name']}")
        print(f"   Monthly Limit: ${result['monthly_limit']}")
        print(f"   OpenRouter Key Name: {result['key_name']}")
        print(f"")
        print(f"🔑 GENERATED API KEY:")
        print(f"   {result['api_key']}")
        print(f"")
        print(f"📝 KEY DETAILS:")
        print(f"   Hash: {result['key_hash']}")
        print(f"   Type: OpenRouter API Key")
        print(f"   Generated from: Org_B Provisioning Key")
        print(f"")
        print(f"🎯 INSTRUCTIONS FOR CLIENT:")
        print(f"   1. Give them this API key: {result['api_key']}")
        print(f"   2. Client opens mAI → Settings → Connections")
        print(f"   3. Client adds OpenRouter connection:")
        print(f"      URL: https://openrouter.ai/api/v1")
        print(f"      API Key: {result['api_key']}")
        print(f"   4. Client clicks Save")
        print(f"   5. Automatic mapping handles everything else!")
        print(f"")
        print(f"✅ Usage tracking will start automatically with 1.3x markup")
        
        # Save to simple text file
        filename = f"client_key_{args.client_name.replace(' ', '_').lower()}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(f"Client: {result['client_name']}\n")
                f.write(f"API Key: {result['api_key']}\n")
                f.write(f"Monthly Limit: ${result['monthly_limit']}\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"Instructions: Give this key to client to enter in Settings → Connections\n")
            
            print(f"💾 Key saved to: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save to file: {e}")
        
    else:
        print(f"\n❌ FAILED to generate API key for {args.client_name}")
        print(f"Possible issues:")
        print(f"• Provisioning key may be invalid")
        print(f"• Network connection issue")  
        print(f"• OpenRouter API may be down")
        print(f"• Account may not have permission to create keys")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python3 simple_create_client_key.py 'Client Name' [--limit 1000]")
        print("")
        print("Examples:")
        print("  python3 simple_create_client_key.py 'Polish Company ABC'")
        print("  python3 simple_create_client_key.py 'Warsaw Tech Ltd' --limit 500")
        print("  python3 simple_create_client_key.py 'Krakow Digital' --limit 2000")
    else:
        main()
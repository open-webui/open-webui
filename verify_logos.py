#!/usr/bin/env python3
"""
Quick script to verify mAI logos are accessible from the backend API
"""
import requests
import sys

def check_logo_endpoint(url, name):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name}: OK ({len(response.content)} bytes)")
            return True
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False

def main():
    base_url = "http://localhost:8080/static"
    
    logos_to_check = [
        ("favicon.png", "Favicon"),
        ("logo.png", "Logo"),
        ("splash.png", "Splash Screen"),
        ("favicon.svg", "SVG Favicon")
    ]
    
    print("🔍 Verifying mAI logos are accessible...")
    print()
    
    all_ok = True
    for filename, display_name in logos_to_check:
        url = f"{base_url}/{filename}"
        if not check_logo_endpoint(url, display_name):
            all_ok = False
    
    print()
    if all_ok:
        print("🎉 All logos are properly served!")
        sys.exit(0)
    else:
        print("⚠️  Some logos are not accessible")
        sys.exit(1)

if __name__ == "__main__":
    main()
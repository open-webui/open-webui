#!/usr/bin/env python3
"""
Test the usage tracking API endpoints directly
"""

import json
import sqlite3

def test_api_endpoints():
    """Test the API endpoints that the frontend calls"""
    print("🌐 Testing Usage Tracking API Endpoints")
    print("=" * 60)
    
    # You'll need to get these from your browser
    print("\n⚠️  To test the API, I need your session token.")
    print("How to get it:")
    print("1. Open mAI in your browser")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application/Storage > Local Storage")
    print("4. Find 'token' and copy its value")
    print("5. Or check Network tab for Authorization header")
    
    # For now, let's create a curl command you can run
    print("\n📋 Run these commands to test the API:")
    
    base_url = "http://localhost:3000"  # Adjust if different
    
    commands = [
        {
            "desc": "Test my-organization endpoint",
            "cmd": f"""curl -X GET "{base_url}/api/v1/client-organizations/usage/my-organization" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -H "Content-Type: application/json" | python3 -m json.tool"""
        },
        {
            "desc": "Test today's usage endpoint",
            "cmd": f"""curl -X GET "{base_url}/api/v1/client-organizations/usage/my-organization/today" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -H "Content-Type: application/json" | python3 -m json.tool"""
        }
    ]
    
    for i, cmd_info in enumerate(commands, 1):
        print(f"\n{i}. {cmd_info['desc']}:")
        print(cmd_info['cmd'])
    
    print("\n💡 Replace YOUR_TOKEN_HERE with your actual token from the browser")
    
    # Also create a simpler direct database check
    print("\n" + "=" * 60)
    print("📊 Alternative: Direct Database Query")
    print("=" * 60)
    
    import sqlite3
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the exact data structure the API should return
    cursor.execute("""
        SELECT 
            co.id as client_id,
            co.name as client_name,
            clc.today_tokens,
            clc.today_requests,
            clc.today_markup_cost,
            clc.last_updated
        FROM client_organizations co
        LEFT JOIN client_live_counters clc ON co.id = clc.client_org_id
        WHERE co.is_active = 1
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if result:
        print("\n✅ Expected API Response Structure:")
        expected = {
            "success": True,
            "stats": {
                "today": {
                    "tokens": result[2] or 0,
                    "cost": result[4] or 0.0,
                    "requests": result[3] or 0,
                    "last_updated": f"Last updated at {result[5]}" if result[5] else "No usage today"
                },
                "this_month": {
                    "tokens": result[2] or 0,  # Would aggregate from daily_usage
                    "cost": result[4] or 0.0,
                    "requests": result[3] or 0,
                    "days_active": 1
                },
                "daily_history": [],  # Would include historical data
                "client_org_name": result[1]
            },
            "client_id": result[0]
        }
        print(json.dumps(expected, indent=2))
    
    conn.close()

def check_frontend_api_calls():
    """Show what the frontend is trying to call"""
    print("\n🔍 Frontend API Call Analysis")
    print("=" * 60)
    
    print("\nThe frontend (MyOrganizationUsage.svelte) makes these calls:")
    print("\n1. On mount:")
    print("   - getClientUsageSummary() → GET /api/v1/client-organizations/usage/my-organization")
    print("\n2. Every 30 seconds:")
    print("   - getTodayUsage() → GET /api/v1/client-organizations/usage/my-organization/today")
    print("\n3. On tab switch:")
    print("   - getUsageByUser() → GET /api/v1/client-organizations/usage/by-user/{client_id}")
    print("   - getUsageByModel() → GET /api/v1/client-organizations/usage/by-model/{client_id}")
    
    print("\n⚠️  Common Issues:")
    print("1. ❌ 401 Unauthorized - Token is missing or invalid")
    print("2. ❌ 404 Not Found - API route not registered")
    print("3. ❌ 500 Server Error - Backend error (check server logs)")
    print("4. ❌ CORS Error - Frontend/backend URL mismatch")

def check_browser_steps():
    """Provide browser debugging steps"""
    print("\n🌐 Browser Debugging Steps")
    print("=" * 60)
    
    print("\n1. Open Browser Developer Tools (F12)")
    print("\n2. Go to Network Tab")
    print("   - Clear existing requests")
    print("   - Navigate to Admin Settings > Usage")
    print("   - Look for requests to 'my-organization'")
    print("   - Check status code and response")
    
    print("\n3. Go to Console Tab")
    print("   - Look for any red error messages")
    print("   - Check for 'Failed to load usage statistics'")
    
    print("\n4. Check the Response:")
    print("   - If 200 OK but no data: Backend returns empty stats")
    print("   - If 401: Authentication issue")
    print("   - If 404: Router not properly configured")
    print("   - If 500: Check Docker logs: docker logs mai-container-name")

if __name__ == "__main__":
    test_api_endpoints()
    check_frontend_api_calls()
    check_browser_steps()
    
    print("\n" + "=" * 60)
    print("📋 Quick Fix Checklist:")
    print("1. ✅ Database has data (confirmed)")
    print("2. ✅ User mapping exists (confirmed)")
    print("3. ❓ API endpoints responding correctly")
    print("4. ❓ Frontend receiving data")
    print("5. ❓ No JavaScript errors in console")
    
    print("\n🚀 Next: Run the curl commands above with your token!")
    print("     Or check the browser console/network tab directly")
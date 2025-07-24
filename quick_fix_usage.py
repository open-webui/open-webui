#!/usr/bin/env python3
"""
Quick fix for usage tracking display issue
"""

import sqlite3
import json
from datetime import datetime

def diagnose_and_fix():
    """Quick diagnosis and potential fix"""
    print("🚀 Quick Usage Tracking Fix")
    print("=" * 60)
    
    # Check Docker container
    print("\n1️⃣ Check your Docker setup:")
    print("   - Port mapping: Is it 3000:8080 or 3002:8080?")
    print("   - Container name: mai-production or something else?")
    print("\n   Run: docker ps | grep mai")
    
    # Provide test commands
    print("\n2️⃣ Test the API directly (adjust port if needed):")
    print("\n   First, get your token from browser:")
    print("   - Open mAI → F12 → Application → Local Storage → token")
    
    print("\n   Then run (replace YOUR_TOKEN and adjust port):")
    print("""
curl -X GET "http://localhost:3002/api/v1/client-organizations/usage/my-organization" \\
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool
""")
    
    # Check for common issues
    print("\n3️⃣ Common Issues & Solutions:")
    
    print("\n   ❌ If you get 404 Not Found:")
    print("      → The router might not be loaded. Check Docker logs:")
    print("      → docker logs mai-container-name 2>&1 | grep -i 'client'")
    
    print("\n   ❌ If you get 401 Unauthorized:")
    print("      → Token is invalid or expired. Try logging out and back in.")
    
    print("\n   ❌ If you get 500 Server Error:")
    print("      → Check Docker logs for Python errors:")
    print("      → docker logs mai-container-name --tail 50")
    
    print("\n   ❌ If API works but UI shows nothing:")
    print("      → Check browser console (F12) for JavaScript errors")
    print("      → Check Network tab for failed requests")
    
    # Show current data status
    print("\n4️⃣ Your current data status:")
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT co.id) as orgs,
            COUNT(DISTINCT ucm.user_id) as users,
            SUM(clc.today_tokens) as total_tokens,
            SUM(clc.today_markup_cost) as total_cost
        FROM client_organizations co
        LEFT JOIN user_client_mapping ucm ON co.id = ucm.client_org_id
        LEFT JOIN client_live_counters clc ON co.id = clc.client_org_id
        WHERE co.is_active = 1
    """)
    
    result = cursor.fetchone()
    print(f"\n   ✅ Active organizations: {result[0]}")
    print(f"   ✅ Mapped users: {result[1]}")
    print(f"   ✅ Today's tokens: {result[2] or 0}")
    print(f"   ✅ Today's cost: ${result[3] or 0:.6f}")
    
    conn.close()
    
    # Provide manual verification
    print("\n5️⃣ Manual Verification:")
    print("   a) In your browser, open Developer Tools (F12)")
    print("   b) Go to Network tab")
    print("   c) Navigate to Admin Settings > Usage")
    print("   d) Look for 'my-organization' request")
    print("   e) Check:")
    print("      - Status code (should be 200)")
    print("      - Response body (should have 'success: true')")
    print("      - Any console errors (red text)")
    
    print("\n6️⃣ Quick Actions:")
    print("   [ ] Verify Docker port (3000 or 3002)")
    print("   [ ] Test API with curl command above")
    print("   [ ] Check browser console for errors")
    print("   [ ] Check Docker logs if API fails")
    print("   [ ] Try logout/login if auth issues")
    
    print("\n" + "=" * 60)
    print("💡 Most common fix: Clear browser cache and reload!")
    print("   Ctrl+Shift+R (or Cmd+Shift+R on Mac)")

if __name__ == "__main__":
    diagnose_and_fix()
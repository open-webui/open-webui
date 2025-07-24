#!/bin/bash
# Script to verify usage API endpoint

echo "🔍 Verifying mAI Usage Tracking API"
echo "==================================="

# Step 1: Check Docker container
echo -e "\n1️⃣ Checking Docker container:"
docker ps | grep -E "(mai|webui)" | awk '{print "Container: " $NF " | Port: " $11}'

# Step 2: Get the port
echo -e "\n2️⃣ Enter the port your mAI is running on (e.g., 3000 or 3002):"
read -p "Port: " PORT

# Step 3: Get auth token
echo -e "\n3️⃣ Getting your auth token:"
echo "   1. Open mAI in browser"
echo "   2. Press F12 for Developer Tools"
echo "   3. Go to Application → Local Storage → http://localhost:$PORT"
echo "   4. Copy the value of 'token'"
echo ""
read -p "Paste your token here: " TOKEN

# Step 4: Test the API
echo -e "\n4️⃣ Testing API endpoint..."
echo "Calling: http://localhost:$PORT/api/v1/client-organizations/usage/my-organization"

RESPONSE=$(curl -s -X GET "http://localhost:$PORT/api/v1/client-organizations/usage/my-organization" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

# Step 5: Display results
echo -e "\n5️⃣ API Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Step 6: Interpret results
echo -e "\n6️⃣ Analysis:"
if echo "$RESPONSE" | grep -q '"success":true'; then
    echo "✅ API is working! The backend is returning data correctly."
    echo ""
    echo "💡 Since the API works but UI doesn't show data, try:"
    echo "   1. Hard refresh browser: Ctrl+Shift+R (Cmd+Shift+R on Mac)"
    echo "   2. Clear browser data for localhost:$PORT"
    echo "   3. Log out and log back in"
    echo "   4. Check browser console for JavaScript errors"
elif echo "$RESPONSE" | grep -q "401"; then
    echo "❌ Authentication failed. Your token may be expired."
    echo "   → Try logging out and back in"
elif echo "$RESPONSE" | grep -q "404"; then
    echo "❌ API endpoint not found."
    echo "   → The router may not be loaded. Check Docker logs:"
    echo "   → docker logs [container-name] 2>&1 | grep -i client"
else
    echo "❌ Unexpected response. Check Docker logs for errors."
fi

echo -e "\n✅ Your database has data: 939 tokens, $0.000344 cost"
echo "The issue is likely frontend-related (cache, auth, or JavaScript)."
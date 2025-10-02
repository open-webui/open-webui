#!/bin/bash

echo "Testing Moderation Endpoint..."
echo "================================"
echo ""

# Test without auth (should get 401)
echo "Test 1: Without authentication (should return 401)"
curl -s -X POST http://localhost:8080/api/v1/moderation/apply \
  -H "Content-Type: application/json" \
  -d '{"moderation_type": "Defer to Parents"}' | jq '.'

echo ""
echo ""

# You'll need to get a real token from localStorage in your browser
# For now, this shows the endpoint exists
echo "To test with real authentication:"
echo "1. Open your browser"
echo "2. Open Developer Tools (F12)"
echo "3. Go to Console tab"
echo "4. Run: localStorage.token"
echo "5. Copy the token value"
echo "6. Run this command with your token:"
echo ""
echo 'curl -X POST http://localhost:8080/api/v1/moderation/apply \\'
echo '  -H "Content-Type: application/json" \\'
echo '  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\'
echo '  -d '"'"'{"moderation_type": "Defer to Parents"}'"'"' | jq'"'"'.'"'"



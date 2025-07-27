#!/bin/bash
# Test script for dynamic pricing API

echo "🧪 Testing Dynamic Model Pricing API"
echo "===================================="

# Test 1: Normal fetch (may use cache)
echo -e "\n1️⃣ Testing normal fetch..."
response=$(curl -s http://localhost:3001/api/v1/usage-tracking/model-pricing)

if [ $? -eq 0 ]; then
    echo "✅ API responded successfully"
    
    # Parse response with jq if available
    if command -v jq &> /dev/null; then
        success=$(echo "$response" | jq -r '.success')
        source=$(echo "$response" | jq -r '.source')
        model_count=$(echo "$response" | jq '.models | length')
        last_updated=$(echo "$response" | jq -r '.last_updated // "N/A"')
        
        echo "📍 Source: $source"
        echo "📊 Models: $model_count"
        echo "🕐 Last updated: $last_updated"
        
        # Show first model as example
        echo -e "\nSample model:"
        echo "$response" | jq '.models[0] | "- \(.name) (\(.provider))\n  Input: $\(.price_per_million_input)/M tokens\n  Output: $\(.price_per_million_output)/M tokens"' -r
    else
        # Fallback without jq
        echo "Response received (install jq for better output):"
        echo "$response" | head -c 200
        echo "..."
    fi
else
    echo "❌ API request failed"
fi

# Test 2: Force refresh
echo -e "\n2️⃣ Testing force refresh..."
response_fresh=$(curl -s "http://localhost:3001/api/v1/usage-tracking/model-pricing?force_refresh=true")

if [ $? -eq 0 ]; then
    echo "✅ Force refresh completed"
    
    if command -v jq &> /dev/null; then
        source=$(echo "$response_fresh" | jq -r '.source')
        echo "📍 Source: $source"
        
        if [ "$source" = "openrouter_api" ]; then
            echo "✅ Successfully fetched fresh data from OpenRouter"
        else
            echo "⚠️  Using fallback data: $source"
        fi
    fi
else
    echo "❌ Force refresh failed"
fi

echo -e "\n===================================="
echo "✅ Test completed!"
#!/bin/bash

echo "🧪 Testing mAI Production Container"
echo "=================================="

# Test container status
echo "📋 Container Status:"
docker ps | grep mai-production-test

echo ""
echo "🌐 Testing HTTP accessibility..."
sleep 2

# Test if port is accessible
if nc -z localhost 3000; then
    echo "✅ Port 3000 is accessible"
else
    echo "❌ Port 3000 is not accessible"
    exit 1
fi

echo ""
echo "📊 Container Resource Usage:"
docker stats mai-production-test --no-stream

echo ""
echo "🔍 Recent Logs:"
docker logs mai-production-test --tail 5

echo ""
echo "✅ mAI Production Container Test Complete!"
echo "🌐 Access your mAI instance at: http://localhost:3000"
echo ""
echo "🧪 Manual Testing Steps:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Verify page title shows 'mAI'"
echo "3. Check that main logo displays mAI branding"
echo "4. Test Settings > General for custom themes"
echo "5. Test Ollama model connection"
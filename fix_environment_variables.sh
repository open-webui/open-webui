#!/bin/bash
# Fix environment variables for mAI Docker container

echo "🔧 Fixing Environment Variables for mAI Container"
echo "================================================="

echo "1. Stopping Docker container to reload environment variables..."
docker-compose -f docker-compose-customization.yaml down

echo ""
echo "2. Verifying .env file contains correct values..."
if grep -q "OPENROUTER_EXTERNAL_USER=mai_client_63a4eb6d" .env; then
    echo "   ✅ OPENROUTER_EXTERNAL_USER: mai_client_63a4eb6d"
else
    echo "   ❌ OPENROUTER_EXTERNAL_USER not found in .env"
fi

if grep -q "ORGANIZATION_NAME=" .env; then
    echo "   ✅ ORGANIZATION_NAME: $(grep ORGANIZATION_NAME= .env | cut -d'=' -f2)"
else
    echo "   ❌ ORGANIZATION_NAME not found in .env"
fi

echo ""
echo "3. Starting Docker container with updated environment..."
docker-compose -f docker-compose-customization.yaml up -d

echo ""
echo "4. Waiting for container to start..."
sleep 10

echo ""
echo "5. Verifying environment variables are loaded in container..."
docker exec open-webui-customization printenv | grep -E "(ORGANIZATION_NAME|OPENROUTER_EXTERNAL_USER|OPENROUTER_API_KEY)" || echo "   ⚠️  Environment variables not yet loaded, container may still be starting"

echo ""
echo "6. Container status:"
docker ps | grep open-webui-customization

echo ""
echo "✅ Environment fix completed!"
echo "💡 Now refresh your browser and check the Usage Settings tabs"
echo "🌐 Access at: http://localhost:3002"
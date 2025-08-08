#!/bin/bash

# Setup Token Groups for GPT-5 Models
# Replace YOUR_TOKEN_HERE with your actual auth token

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImY5YWJlOGJiLTcyMDItNGMxNi05YzFmLWZhYjc2MmY5YmZiZCJ9.PxZQd1muie8Bux08xcSk1plx0y3v1bp6FcqC-x6NXf8"

echo "🚀 Creating token groups for GPT-5 models..."

# Create gpt-5-models group (1M tokens)
echo "Creating gpt-5-models group (1M token limit)..."
curl -X POST "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "gpt-5-models",
       "models": ["gpt-5", "gpt-5-chat-latest"],
       "limit": 1000000
     }'

echo -e "\n"

# Create gpt-5-mini group (10M tokens)  
echo "Creating gpt-5-mini group (10M token limit)..."
curl -X POST "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "gpt-5-mini", 
       "models": ["gpt-5-mini"],
       "limit": 10000000
     }'

echo -e "\n"

# Verify groups were created
echo "Verifying created groups..."
curl "http://localhost:8081/api/usage/groups" \
     -H "Authorization: Bearer $TOKEN"

echo -e "\n✅ Token groups setup complete!"
echo "📊 gpt-5-models: 1,000,000 tokens (gpt-5, gpt-5-chat-latest)"
echo "📊 gpt-5-mini: 10,000,000 tokens (gpt-5-mini)"

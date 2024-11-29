#!/bin/bash

# Stop any running containers
docker compose -f docker-compose.prod.yaml down

# Copy environment file
cp .env.prod .env

# Start containers
docker compose -f docker-compose.prod.yaml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check service health
echo "Checking service health..."
curl -s http://localhost:8080/health || echo "Backend not responding"
curl -s http://localhost:80 || echo "Frontend not responding"
curl -s http://localhost:11435/api/health || echo "Ollama not responding"

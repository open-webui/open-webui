#!/bin/bash

# Stop any running containers
docker compose -f docker-compose.dev.yaml down

# Copy environment file
cp .env.dev .env

# Start containers
docker compose -f docker-compose.dev.yaml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check service health
echo "Checking service health..."
curl -s http://localhost:8080/health || echo "Backend not responding"
curl -s http://localhost:3000 || echo "Frontend not responding"
curl -s http://localhost:11434/api/health || echo "Ollama not responding"

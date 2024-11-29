#!/bin/bash

# Stop any running containers
docker compose -f docker-compose.test.yaml down

# Copy environment file
cp .env.test .env

# Start containers
docker compose -f docker-compose.test.yaml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check service health
echo "Checking service health..."
curl -s http://localhost:8080/health || echo "Backend not responding"
curl -s http://localhost:3002 || echo "Frontend not responding"
curl -s http://localhost:11436/api/health || echo "Ollama not responding"

# Run tests if all services are up
if curl -s http://localhost:8080/health > /dev/null; then
    echo "Running tests..."
    docker compose -f docker-compose.test.yaml run whatever-cypress
else
    echo "Services not healthy, skipping tests"
fi

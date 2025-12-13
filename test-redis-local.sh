#!/bin/bash

# Quick test script for Redis and RQ worker setup

set -e

echo "=========================================="
echo "Open WebUI - Redis & RQ Local Testing"
echo "=========================================="
echo ""

# Check if Redis is running locally
echo "Checking for local Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis is running locally"
        REDIS_HOST="host.docker.internal"
    else
        echo "⚠️  Redis CLI found but server not responding"
        REDIS_HOST="host.docker.internal"
    fi
else
    echo "⚠️  Redis CLI not found. Will use docker-compose Redis instead."
    REDIS_HOST="redis"
fi

# Detect M1 Mac
if [[ $(uname -m) == "arm64" ]] && [[ $(uname) == "Darwin" ]]; then
    echo "✅ Detected M1 Mac - will use native ARM64 build"
    COMPOSE_FILE="docker-compose.local.m1.yaml"
else
    COMPOSE_FILE="docker-compose.local.yaml"
fi

echo ""
echo "Choose an option:"
echo "1. Use Docker Compose (includes Redis container)"
echo "2. Use Docker Run with local Redis (brew install redis)"
echo "3. Use Docker Run without Redis (BackgroundTasks fallback)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Building image..."
        docker build -t test_a3 .
        echo ""
        echo "Starting with Docker Compose..."
        docker-compose -f $COMPOSE_FILE up
        ;;
    2)
        echo ""
        echo "Building image..."
        docker build -t test_a3 .
        echo ""
        echo "Starting container with local Redis..."
        echo "Make sure Redis is running: redis-server"
        docker run -it -p 8080:8080 \
            -e REDIS_URL=redis://host.docker.internal:6379/0 \
            -e ENABLE_JOB_QUEUE=True \
            test_a3
        ;;
    3)
        echo ""
        echo "Building image..."
        docker build -t test_a3 .
        echo ""
        echo "Starting container without Redis (using BackgroundTasks)..."
        docker run -it -p 8080:8080 \
            -e ENABLE_JOB_QUEUE=False \
            test_a3
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

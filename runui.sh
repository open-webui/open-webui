#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Set default port if not provided
PORT=${PORT:-3000}

# Install dependencies
npm ci

# Build the application
npm run build

# Start the application
npm start -- --port $PORT
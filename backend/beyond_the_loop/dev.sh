#!/bin/bash

# Set the Python path to include the backend directory
export PYTHONPATH="/Users/philszalay/Documents/code/beyond-the-loop/backend:$PYTHONPATH"

PORT="${PORT:-8080}"

# Start the LiteLLM container in the background
cd /Users/philszalay/Documents/code/beyond-the-loop && docker-compose -f docker-compose-local.yaml up -d litellm

# Start the uvicorn server
cd /Users/philszalay/Documents/code/beyond-the-loop/backend && uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload

#!/bin/bash

image_name="open-webui"
container_name="open-webui"
host_port=3000
container_port=8080

docker build -t "$image_name" .
docker stop "$container_name" &>/dev/null || true
docker rm "$container_name" &>/dev/null || true

docker run -d -p "$host_port":"$container_port" \
    -e USE_CUDA_DOCKER=false \
    -e OLLAMA_BASE_URL=https://example.com \
    -v "${image_name}:/app/backend/data" \
    --name "$container_name" \
    --restart always \
    "$image_name"

docker image prune -f

# docker run -d -p 3000:8080 -e 
#     USE_CUDA_DOCKER=false -e 
#     OLLAMA_BASE_URL=https://example.com 
    
#     -v open-webui:/app/backend/data --name open-webui 
#     --restart always ghcr.io/open-webui/open-webui:main --pull=always


# docker run -d -p "$host_port":"$container_port" \
#     -e USE_CUDA_DOCKER=false \
#     -e OLLAMA_BASE_URL=https://example.com \
#     # --add-host=host.docker.internal:host-gateway \
#     -v "${image_name}:/app/backend/data" \
#     --name "$container_name" \
#     --restart always ghcr.io/open-webui/open-webui:main \
#     "$image_name"
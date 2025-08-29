#!/bin/bash

source .config

echo "Building image $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION"

# This script builds the project using the specified build tool.
docker build -t $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION .  \
              --build-arg USE_SLIM=true \
              --build-arg USE_CUDA=false \
              --build-arg USE_OLLAMA=false \
              && \

docker push $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION
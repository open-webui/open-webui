#!/bin/bash

set -ex

IMAGE_NAME="openwebui-local"

docker build --platform linux/amd64 -t $IMAGE_NAME .
# Remove existing container and volume to ensure a clean deployment
# The || true handles cases where the container doesn't exist
docker stop $IMAGE_NAME || true
docker rm $IMAGE_NAME || true
docker volume rm $IMAGE_NAME || true

docker run \
  --platform linux/amd64 \
  --env-file .env.dyson \
  --net='host' \
  -v $IMAGE_NAME:/app/backend/data \
  -v ~/.config/gcloud:/root/.config/gcloud \
  --name $IMAGE_NAME $IMAGE_NAME:latest
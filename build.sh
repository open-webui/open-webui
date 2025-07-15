#!/bin/bash

IMAGE_NAME=cybertech/open-webui
IMAGE_VERSION=latest

read -p "Enter the registry url: " REGISTRY_URL

# This script builds the project using the specified build tool.
docker build -t $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION . 
docker push $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION
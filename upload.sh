#!/bin/bash

source .config

echo "Uploading image $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION"

# If the build is successful, push the image to the specified registry.
docker push $REGISTRY_URL/$IMAGE_NAME:$IMAGE_VERSION
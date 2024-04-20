#!/bin/bash

set -e

STATIC_DIR=$SNAP_DATA/static
mkdir -p $STATIC_DIR

DATA_DIR=$(snapctl get data-dir) \
STATIC_DIR=$STATIC_DIR \
FRONTEND_BUILD_DIR=$SNAP/build \
HOST=$(snapctl get host) \
PORT=$(snapctl get port) \
WEBUI_SECRET_KEY=$(snapctl get secret-key) \
OLLAMA_API_BASE_URL=$(snapctl get ollama-api-base-url) \
OPENAI_API_BASE_URL=$(snapctl get openai-api-base-url) \
OPENAI_API_KEY=$(snapctl get openai-api-key) \
ENABLE_SIGNUP=$(snapctl get enable-signup) \
    $SNAP/backend/start.sh $@

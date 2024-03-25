#!/bin/bash

set -e

DATA_DIR=$(snapctl get data-dir) \
PORT=$(snapctl get port) \
HOST=$(snapctl get host) \
WEBUI_SECRET_KEY=$(snapctl get secret-key) \
OLLAMA_API_BASE_URL=$(snapctl get ollama-api-base-url) \
OPENAI_API_BASE_URL=$(snapctl get openai-api-base-url) \
OPENAI_API_KEY=$(snapctl get openai-api-key) \
ENABLE_SIGNUP=$(snapctl get enable-signup) \
FRONTEND_BUILD_DIR=$SNAP/frontend \
$SNAP/backend/start.sh $@

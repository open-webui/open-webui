#!/usr/bin/env bash

docker run --gpus all --rm \
  -p 8000:8000 \
  -v /data/hf-cache:/root/.cache/huggingface \
  -e HUGGING_FACE_HUB_TOKEN=$HUGGING_FACE_HUB_TOKEN \
  vllm/vllm-openai:latest \
  --model $MODEL_ID \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len $MAX_MODEL_LEN
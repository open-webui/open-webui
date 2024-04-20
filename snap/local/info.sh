#!/bin/bash

HOST=$(snapctl get host)
PORT=$(snapctl get port)

SERVICE_INFO=$(snapctl services $SNAP_INSTANCE_NAME.listener)

STATUS=$(echo "$SERVICE_INFO" | awk '/open-webui.listener/{print $3}')

echo "$SNAP_INSTANCE_NAME.listener: $STATUS"

if [ "$STATUS" == "active" ]; then
  echo ''
  echo "To use $SNAP_INSTANCE_NAME, open the following URL in your browser: http://$HOST:$PORT"
else
  echo ''
  echo "If you expected the service to be up, check that the port $PORT is available, not bound by some other service."
fi

echo ''
echo 'For documentation, see https://docs.openwebui.com'
echo ''
echo "You can use a local AI model with $SNAP_INSTANCE_NAME with ollama (http://ollama.com)."
echo ' - You can install ollama with `sudo snap install ollama --channel=beta`'
echo ' - ollama is by default expected to be serving at 'http://localhost:11434/api'. To customize that, do `sudo snap set open-webui ollama-api-base-url=...`'
echo ' - for all available configuration parameters, see `sudo snap get open-webui`'
echo ''
echo "You can access any OpenAI compatible API endpoint with $SNAP_INSTANCE_NAME."
echo ' - To configure the OpenAI endpoint (by default expected to be "https://api.openai.com/v1"), do `sudo snap set open-webui openai-api-base-url=...`'
echo ' - To configure the OpenAI API key (by default an empty string), do `sudo snap set open-webui openai-api-key=...`'

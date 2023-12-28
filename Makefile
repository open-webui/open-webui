WEBUI_REPO ?= ghcr.io/meteron-ai/ollama-webui
TAG_NAME ?= latest

image-server:
	docker build --platform linux/amd64 -t ${WEBUI_REPO}:${TAG_NAME} -f Dockerfile --build-arg OLLAMA_API_BASE_URL=/ollama/api  .

image-push: image-server
	docker push ${WEBUI_REPO}:${TAG_NAME}
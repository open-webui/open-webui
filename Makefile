
ifneq ($(shell which docker-compose 2>/dev/null),)
    DOCKER_COMPOSE := docker-compose
else
    DOCKER_COMPOSE := docker compose
endif

image_name="open-webui-iara"
container_name:="open-webui-iara"
host_port:=3000
container_port:=8080

install:
	$(DOCKER_COMPOSE) up -d

remove:
	@chmod +x confirm_remove.sh
	@./confirm_remove.sh

start:
	$(DOCKER_COMPOSE) start
startAndBuild: 
	$(DOCKER_COMPOSE) up -d --build

stop:
	$(DOCKER_COMPOSE) stop

update:
	# Calls the LLM update script
	chmod +x update_ollama_models.sh
	@./update_ollama_models.sh
	@git pull
	$(DOCKER_COMPOSE) down
	# Make sure the ollama-webui container is stopped before rebuilding
	@docker stop open-webui || true
	$(DOCKER_COMPOSE) up --build -d
	$(DOCKER_COMPOSE) start

docker-build:
	@echo "--> Docker build"
	@docker build -t docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.5.16-2 .

create-buildx:
	@docker buildx create --use

buildx:
	@docker buildx build  --platform linux/arm64,linux/amd64 -t docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:weaviate.0.5.16 --push .

buildx-arm:
	@docker buildx build  --platform linux/arm64 -t docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.5.16 --push .

buildx-amd:
	@docker buildx build  --platform linux/amd64 -t docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.5.16 --push .

run:
	@docker run -p 3000:8080 --env WEB_CONCURRENCY=1 -add-host=host.docker.internal:host-gateway -v "/app/backend/data:/app/backend/data" --name docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.5.16 --restart always

run-litellm:
	@docker run -d -v $(pwd)/litellm_config.yaml:/app/config.yaml \ 
	-p 4000:4000 \
	ghcr.io/berriai/litellm:main-latest \
	--config /app/config.yaml --detailed_debug
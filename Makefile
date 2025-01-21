
ifneq ($(shell which docker-compose 2>/dev/null),)
    DOCKER_COMPOSE := docker-compose
else
    DOCKER_COMPOSE := docker compose
endif

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

build:
	@echo "--> Docker build"
	docker build -t docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.0.1 .

create-buildx:
	@docker buildx create --use

buildx:
	@docker buildx build  --platform linux/arm64,linux/amd64 -t docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.0.1 --push .

run:
	@docker run -d -p 80:80 --env WEB_CONCURRENCY=1 docker-unj-repo.softplan.com.br/unj/inovacao/openwebui-iara:0.0.1
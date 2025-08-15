
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

ecr-login:
	aws sso login --profile speDeveloper-654281453265
	aws --profile speDeveloper-654281453265 ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 654281453265.dkr.ecr.us-east-1.amazonaws.com

# aws configure
# aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 654281453265.dkr.ecr.us-east-1.amazonaws.com
# docker pull 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:0.0.1

build-cuda: # upgrade version number manually here
	docker build --platform=linux/amd64 --build-arg USE_CUDA=true -t openwebui-modified-cuda .
	docker rm -f openwebui-modified-cuda || true
	docker tag openwebui-modified-cuda 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:0.0.1
	docker push 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:0.0.1

build:
	docker build . -t openwebui-modified
	docker rm -f openwebui-modified || true
	docker tag openwebui-modified:latest 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:latest
	docker push 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:latest

run-prod:
	docker pull 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:0.0.1
	docker run -d -p 3002:8080 --gpus all --add-host=host.docker.internal:host-gateway -v openwebui-modified-cuda:/app/backend/data --name openwebui-modified-cuda --restart always 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:0.0.1

	docker run -d -p 8006:8080 --gpus all --add-host=host.docker.internal:host-gateway -v openwebui-modified-cuda-volume:/app/backend/data --name openwebui-modified-cuda-2 --restart always 654281453265.dkr.ecr.us-east-1.amazonaws.com/artificial-insanity:0.0.2

run:
	docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v openwebui-modified:/app/backend/data --name openwebui-modified --restart always openwebui-modified



install:
	@docker-compose up -d

remove:
	@docker-compose down -v

start:
	@docker-compose start

stop:
	@docker-compose stop

update:
	# Calls the LLM update script
	@./update_llm.sh
	@git pull
	@docker-compose down
	# Make sure the ollama-webui container is stopped before rebuilding
	@docker stop ollama-webui || true
	@docker-compose up --build -d
	@docker-compose start


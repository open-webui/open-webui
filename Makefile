install:
	@docker-compose up -d

remove:
	@chmod +x confirm_remove.sh
	@./confirm_remove.sh


start:
	@docker-compose start

stop:
	@docker-compose stop

update:
	# Calls the LLM update script
	chmod +x update_ollama_models.sh
	@./update_ollama_models.sh
	@git pull
	@docker-compose down
	# Make sure the ollama-webui container is stopped before rebuilding
	@docker stop open-webui || true
	@docker-compose up --build -d
	@docker-compose start


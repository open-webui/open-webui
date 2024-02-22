install:
	@docker-compose up -d

remove:
	@docker-compose down -v

start:
	@docker-compose start

stop:
	@docker-compose stop

update:
	# Appelle le script de mise à jour des LLM
	@./update_llm.sh
	@git pull
	@docker-compose down
	# Assure-toi que le conteneur ollama-webui est arrêté avant de reconstruire
	@docker stop ollama-webui || true
	@docker-compose up --build -d
	@docker-compose start


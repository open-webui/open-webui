@echo off

REM Stop any running containers
docker compose -f docker-compose.dev.yaml down

REM Copy environment file
copy .env.dev .env

REM Start containers
docker compose -f docker-compose.dev.yaml up -d

REM Wait for services to be ready
echo Waiting for services to start...
timeout /t 5 /nobreak

REM Check service health
echo Checking service health...
curl -s http://localhost:8080/health || echo Backend not responding
curl -s http://localhost:3000 || echo Frontend not responding
curl -s http://localhost:11434/api/health || echo Ollama not responding

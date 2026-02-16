if (!(Test-Path ".env")) { Write-Host "Missing .env. Copy .env.example -> .env and set ZAI_API_KEY"; exit 1 }
docker compose --env-file .env -f docker-compose.openwebui.yml up -d
Write-Host "Open WebUI: http://localhost:3000"

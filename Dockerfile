version: '3'

services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://192.168.189:11434
      - OPENAI_API_KEY=your_openai_api_key
      - ADMIN_EMAIL=admin@example.com
      - ADMIN_PASSWORD=admin_password
      - WEBUI_SECRET_KEY=your_secret_key
    volumes:
      -./data:/app/backend/data
    restart: always

  ollama:
    image: ollama/ollama
    command: serve --host 0.0.0.0 --port 11434
    ports:
      - "192.168.189:11434:11434"
    volumes:
      - ollama:/root/.ollama
    restart: always

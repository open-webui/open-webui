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
      - USE_CUDA=false
      - USE_OLLAMA=true
      - USE_CUDA_VER=cu121
      - USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
      - USE_RERANKING_MODEL=""
      - USE_TIKTOKEN_ENCODING_NAME="cl100k_base"
      - BUILD_HASH=dev-build
      - UID=0
      - GID=0
      - SCARF_NO_ANALYTICS=true
      - DO_NOT_TRACK=true
      - ANONYMIZED_TELEMETRY=false
      - WHISPER_MODEL="base"
      - WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"
      - RAG_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
      - RAG_RERANKING_MODEL=""
      - SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"
      - TIKTOKEN_ENCODING_NAME="cl100k_base"
      - TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken"
      - HF_HOME="/app/backend/data/cache/embedding/models"
    volumes:
      -./data:/app/backend/data
    restart: always

volumes:
  data:

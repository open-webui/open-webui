#!/bin/bash

# Script de inicio para desarrollo local completo
# Frontend: http://localhost:5173
# Backend: http://localhost:8080 (requiere Docker)

set -e

echo "=========================================="
echo "  Open WebUi - Desarrollo Local"
echo "=========================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para iniciar frontend
start_frontend() {
    echo -e "${GREEN}[1/2]${NC} Iniciando servidor de desarrollo Frontend..."
    npm run dev
}

# Función para iniciar backend con Docker
start_backend_docker() {
    echo -e "${GREEN}[2/2]${NC} Iniciando Backend con Docker..."
    docker run -d \
        --name open-webui-backend-dev \
        -p 8080:8080 \
        -v open-webui-data:/app/backend/data \
        --add-host=host.docker.internal:host-gateway \
        -e WEBUI_NAME="Open WebUi" \
        -e WEBUI_FAVICON_URL="https://webui.codingsoft.org/favicon.png" \
        -e WEBUI_ADMIN_EMAIL="team@codingsoft.org" \
        -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
        ghcr.io/codingsoft/open-webui:dev || \
    docker run -d \
        --name open-webui-backend-dev \
        -p 8080:8080 \
        -v open-webui-data:/app/backend/data \
        --add-host=host.docker.internal:host-gateway \
        -e WEBUI_NAME="Open WebUi" \
        -e WEBUI_FAVICON_URL="https://webui.codingsoft.org/favicon.png" \
        -e WEBUI_ADMIN_EMAIL="team@codingsoft.org" \
        -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
        ghcr.io/open-webui/open-webui:dev

    echo "Backend iniciado en http://localhost:8080"
}

# Función para detener backend
stop_backend() {
    echo -e "${YELLOW}[-]${NC} Deteniendo backend..."
    docker stop open-webui-backend-dev 2>/dev/null || true
    docker rm open-webui-backend-dev 2>/dev/null || true
}

# Menú de opciones
case "${1:-dev}" in
    dev)
        start_frontend
        ;;
    backend)
        start_backend_docker
        ;;
    stop)
        stop_backend
        ;;
    all)
        stop_backend
        start_backend_docker &
        start_frontend
        ;;
    *)
        echo "Uso: $0 {dev|backend|stop|all}"
        echo ""
        echo "  dev     - Iniciar solo frontend (recomendado para desarrollo)"
        echo "  backend - Iniciar backend con Docker"
        echo "  stop    - Detener backend"
        echo "  all     - Iniciar ambos (frontend + backend)"
        exit 1
        ;;
esac

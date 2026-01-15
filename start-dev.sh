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
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

CONTAINER_NAME="open-webui-backend-dev"
IMAGE_NAME="ghcr.io/codingsoft/open-webui:dev"
FALLBACK_IMAGE="ghcr.io/open-webui/open-webui:dev"

# Función para mostrar estado
status() {
    echo -e "${CYAN}[*]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verificar si Docker está corriendo
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker no está corriendo. Inicia Docker Desktop primero."
        exit 1
    fi
    success "Docker está corriendo"
}

# Verificar si el contenedor ya existe
container_exists() {
    docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"
}

# Verificar si el contenedor está corriendo
container_running() {
    docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"
}

# Función para iniciar backend con Docker
start_backend_docker() {
    status "Iniciando Backend con Docker..."

    check_docker

    if container_running; then
        warning "El backend ya está corriendo en http://localhost:8080"
        return 0
    fi

    # Detener contenedor anterior si existe
    if container_exists; then
        warning "Eliminando contenedor anterior..."
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi

    # Crear volumen si no existe
    if ! docker volume ls --format '{{.Name}}' | grep -q "^open-webui-data$"; then
        status "Creando volumen..."
        docker volume create open-webui-data >/dev/null 2>&1
    fi

    # Intentar con la imagen personalizada primero
    status "Intentando imagen personalizada: $IMAGE_NAME"
    if docker pull "$IMAGE_NAME" >/dev/null 2>&1; then
        IMAGE="$IMAGE_NAME"
    else
        warning "Imagen personalizada no encontrada, usando fallback..."
        if docker pull "$FALLBACK_IMAGE" >/dev/null 2>&1; then
            IMAGE="$FALLBACK_IMAGE"
        else
            error "No se pudo descargar ninguna imagen"
            error "Ejecuta 'docker build' primero o verifica tu conexión"
            exit 1
        fi
    fi

    status "Iniciando contenedor con imagen: $IMAGE"

    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 8080:8080 \
        -v open-webui-data:/app/backend/data \
        --add-host=host.docker.internal:host-gateway \
        -e WEBUI_NAME="Open WebUi" \
        -e WEBUI_FAVICON_URL="https://webui.codingsoft.org/favicon.png" \
        -e WEBUI_ADMIN_EMAIL="team@codingsoft.org" \
        -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
        -e WEBUI_AUTH="False" \
        --restart=no \
        "$IMAGE"

    # Esperar a que el contenedor esté listo
    status "Esperando a que el backend esté listo..."
    sleep 3

    if container_running; then
        success "Backend iniciado correctamente"
        echo ""
        echo "  URL: http://localhost:8080"
        echo "  API: http://localhost:8080/api"
        echo ""
        echo "  Logs: docker logs $CONTAINER_NAME"
        echo "  Stop: $0 stop"
    else
        error "El contenedor no pudo iniciar"
        docker logs "$CONTAINER_NAME" 2>&1 | tail -20
        exit 1
    fi
}

# Función para detener backend
stop_backend() {
    status "Deteniendo backend..."

    if container_running; then
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1
        success "Backend detenido"
    else
        warning "El backend no estaba corriendo"
    fi
}

# Función para mostrar estado del backend
status_backend() {
    if container_running; then
        echo -e "${GREEN}✓${NC} Backend corriendo en http://localhost:8080"
        docker ps --filter "name=$CONTAINER_NAME" --format "  {{.Names}}: {{.Status}}"
    else
        echo -e "${YELLOW}✗${NC} Backend detenido"
    fi
}

# Función para iniciar frontend
start_frontend() {
    status "Iniciando servidor de desarrollo Frontend..."
    echo ""
    npm run dev
}

# Mostrar ayuda
show_help() {
    echo "Uso: $0 {comando}"
    echo ""
    echo "Comandos:"
    echo "  dev      Iniciar solo frontend (recomendado para desarrollo UI)"
    echo "  backend  Iniciar backend con Docker"
    echo "  start    Iniciar ambos (frontend + backend)"
    echo "  stop     Detener backend"
    echo "  restart  Reiniciar backend"
    echo "  status   Mostrar estado del backend"
    echo "  logs     Mostrar logs del backend"
    echo "  help     Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 dev       # Solo frontend"
    echo "  $0 backend   # Solo backend"
    echo "  $0 start     # Ambos"
    echo "  $0 stop      # Detener backend"
}

# Mostrar logs
show_logs() {
    if container_running; then
        docker logs -f "$CONTAINER_NAME"
    else
        warning "El backend no está corriendo. Usa '$0 start' primero."
    fi
}

# Menú de opciones
case "${1:-help}" in
    dev)
        start_frontend
        ;;
    backend)
        start_backend_docker
        ;;
    start)
        stop_backend
        start_backend_docker &
        start_frontend
        ;;
    stop)
        stop_backend
        ;;
    restart)
        stop_backend
        start_backend_docker
        ;;
    status)
        status_backend
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Comando desconocido: $1"
        show_help
        exit 1
        ;;
esac

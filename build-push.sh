#!/bin/bash

# Script de build y deploy para GitHub Container Registry
# Ejecutar en VPS o servidor con recursos suficientes

set -e

echo "=========================================="
echo "  Open WebUi - Build & Deploy"
echo "=========================================="

# Configuración
IMAGE_NAME="ghcr.io/codingsoft/open-webui"
REGISTRY_USER="CodingSoft"

# Detectar si el primer argumento es un tag o un comando
_is_tag() {
    [[ "$1" == dev || "$1" == latest || "$1" =~ ^v[0-9]+\.[0-9]+ ]]
}

if [ -n "$1" ] && _is_tag "$1"; then
    TAG="$1"
    shift
else
    TAG="dev"
fi

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

success() { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Verificar GitHub Token
check_token() {
    if [ -z "$GITHUB_TOKEN" ]; then
        error "GITHUB_TOKEN no está configurado. Ejecuta:"
        echo '  export GITHUB_TOKEN="tu_token_aqui"'
        echo ""
        echo "Para crear un token:"
        echo "  1. Ve a https://github.com/settings/tokens"
        echo "  2. Genera nuevo token (classic)"
        echo "  3. Permisos: read:packages, write:packages, delete:packages"
        exit 1
    fi
    success "GITHUB_TOKEN configurado"
}

# Verificar espacio en disco
check_disk_space() {
    AVAILABLE=$(df -h . | tail -1 | awk '{print $4}' | sed 's/Gi//g')
    REQUIRED=10
    if ! [[ "$AVAILABLE" =~ ^[0-9]+$ ]]; then
        AVAILABLE=$(df -h . | tail -1 | awk '{print $4}' | sed 's/G//g')
    fi
    if [ "$AVAILABLE" -lt "$REQUIRED" ]; then
        error "Espacio insuficiente: ${AVAILABLE}GB disponibles (se requieren ${REQUIRED}GB)"
    fi
    success "Espacio disponible: ${AVAILABLE}GB"
}

# Verificar Docker
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker no está corriendo"
    fi
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker Buildx no está instalado"
    fi
    success "Docker disponible"
}

# Build de la imagen
build_image() {
    local no_cache="${1:-false}"
    warning "Iniciando build multi-platform..."
    echo "  Tag: ${IMAGE_NAME}:${TAG}"
    echo "  Platforms: linux/amd64, linux/arm64"
    echo "  Esto puede tomar varios minutos..."

    local build_args="BUILD_HASH=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"

    if [ "$no_cache" = "true" ]; then
        warning "Build sin caché"
    fi

    docker buildx build \
        --pull \
        $([ "$no_cache" = "true" ] && echo "--no-cache" || echo "") \
        --platform linux/amd64,linux/arm64 \
        --push \
        -t "${IMAGE_NAME}:${TAG}" \
        -t "${IMAGE_NAME}:latest" \
        --build-arg "$build_args" \
        .

    success "Build completado: ${IMAGE_NAME}:${TAG}"
}

# Login a GHCR (ya no necesario con buildx --push, pero kept para compatibilidad)
login_ghcr() {
    warning "Autenticando en GitHub Container Registry..."
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$REGISTRY_USER" --password-stdin
    success "Login exitoso"
}

# Limpiar imágenes antiguas
cleanup() {
    warning "Limpiando imágenes antiguas..."
    docker image prune -f
    success "Limpieza completada"
}

# Mostrar ayuda
show_help() {
    echo ""
    echo "Uso: $0 [tag] [--nocache]"
    echo ""
    echo "Tags disponibles:"
    echo "  dev     - Build de desarrollo"
    echo "  v0.7.2  - Build de versión específica"
    echo "  latest  - Build latest"
    echo ""
    echo "Opciones:"
    echo "  --nocache  - Build sin caché"
    echo ""
    echo "Ejemplos:"
    echo "  $0 dev              # Build dev con caché"
    echo "  $0 dev --nocache    # Build dev sin caché"
    echo "  $0 v0.7.2           # Build versión específica"
    echo ""
    echo "Variables requeridas:"
    echo "  GITHUB_TOKEN - Token de GitHub con permisos de packages"
}

# Menú
case "${1:-help}" in
    build)
        check_docker
        check_disk_space
        build_image
        ;;
    login)
        check_token
        login_ghcr
        ;;
    deploy)
        check_token
        check_docker
        check_disk_space
        login_ghcr
        build_image
        cleanup
        success "Deploy completado!"
        echo ""
        echo "Imagen disponible: ${IMAGE_NAME}:${TAG}"
        ;;
    --nocache)
        TAG="${2:-dev}"
        check_token
        check_docker
        check_disk_space
        login_ghcr
        build_image "true"
        cleanup
        success "Build sin caché completado!"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        check_token
        check_docker
        check_disk_space
        build_image
        cleanup
        success "Build y push completados!"
        ;;
esac

echo ""
echo "=========================================="

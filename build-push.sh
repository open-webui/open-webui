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
TAG="${1:-dev}"

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

# Verificar Docker
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker no está corriendo"
    fi
    success "Docker disponible"
}

# Build de la imagen
build_image() {
    warning "Iniciando build de imagen..."
    echo "  Tag: ${IMAGE_NAME}:${TAG}"
    echo "  Esto puede tomar varios minutos..."

    # Build con caché aumentado
    docker build \
        --pull \
        --no-cache \
        -t "${IMAGE_NAME}:${TAG}" \
        -t "${IMAGE_NAME}:latest" \
        .

    success "Build completado: ${IMAGE_NAME}:${TAG}"
}

# Login a GHCR
login_ghcr() {
    warning "Autenticando en GitHub Container Registry..."
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$REGISTRY_USER" --password-stdin
    success "Login exitoso"
}

# Push de la imagen
push_image() {
    warning "Subiendo imagen a GHCR..."

    docker tag "${IMAGE_NAME}:${TAG}" "${IMAGE_NAME}:${TAG}"
    docker push "${IMAGE_NAME}:${TAG}"

    docker tag "${IMAGE_NAME}:${TAG}" "${IMAGE_NAME}:latest"
    docker push "${IMAGE_NAME}:latest"

    success "Imagen subida: ${IMAGE_NAME}:${TAG}"
    success "Imagen latest: ${IMAGE_NAME}:latest"
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
    echo "Uso: $0 [tag]"
    echo ""
    echo "Tags disponibles:"
    echo "  dev     - Build de desarrollo"
    echo "  v0.7.2  - Build de versión específica"
    echo "  latest  - Build latest"
    echo ""
    echo "Ejemplos:"
    echo "  $0 dev       # Build dev"
    echo "  $0 v0.7.2    # Build versión específica"
    echo ""
    echo "Variables requeridas:"
    echo "  GITHUB_TOKEN - Token de GitHub con permisos de packages"
}

# Menú
case "${1:-help}" in
    build)
        check_docker
        build_image
        ;;
    login)
        check_token
        login_ghcr
        ;;
    push)
        check_token
        push_image
        ;;
    deploy)
        check_token
        check_docker
        build_image
        login_ghcr
        push_image
        cleanup
        success "Deploy completado!"
        echo ""
        echo "Imagen disponible: ${IMAGE_NAME}:${TAG}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        check_token
        check_docker
        build_image
        login_ghcr
        push_image
        cleanup
        success "Build y push completados!"
        ;;
esac

echo ""
echo "=========================================="

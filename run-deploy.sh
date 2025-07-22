#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# ================================
# Configuration and Environment Setup
# ================================

# Path to the environment file
ENV_FILE="env-deploy"

# Function: Load Environment Variables
load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        echo "Loading environment variables from $ENV_FILE..."
        # Export each line as an environment variable, handling spaces and special characters
        set -o allexport
        source "$ENV_FILE"
        set +o allexport
    else
        echo "Error: Environment file '$ENV_FILE' not found."
        exit 1
    fi
}

# Function: Validate Required Environment Variables
validate_env() {
    required_vars=("CACHE_DIR" "IMAGE_BASE_NAME" "VERSION" "CONTAINER_NAME" "HOST_PORT" "CONTAINER_PORT" "LOCAL_CACHE_DIR")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            echo "Error: $var is not set in $ENV_FILE."
            exit 1
        fi
    done
}

# ================================
# Variable Definitions
# ================================

define_variables() {
    # Docker image details
    IMAGE_TAG="${IMAGE_BASE_NAME}:${VERSION}"
    UPDATED_IMAGE_TAG="${IMAGE_BASE_NAME}:${VERSION}_with_cache"

    # Volume name derived from image base name (if using volumes)
    VOLUME_NAME="${IMAGE_BASE_NAME//\//__}"

    echo "Configuration:"
    echo "  Image Tag: $IMAGE_TAG"
    echo "  Updated Image Tag: $UPDATED_IMAGE_TAG"
    echo "  Container Name: $CONTAINER_NAME"
    echo "  Host Port: $HOST_PORT"
    echo "  Container Port: $CONTAINER_PORT"
    echo "  Local Cache Directory: $LOCAL_CACHE_DIR"
    echo "  Cache Directory Inside Container: $CACHE_DIR"
}

# ================================
# Docker Operations
# ================================

# Function: Build Docker Image and Embed Cache Files
build_image() {
    echo "Starting build process..."

    # Step 1: Build the base Docker image if it doesn't exist
    if ! docker image inspect "$IMAGE_TAG" > /dev/null 2>&1; then
        echo "Building Docker image '$IMAGE_TAG'..."
        docker build -t "$IMAGE_TAG" .
        echo "Docker image '$IMAGE_TAG' built successfully."
    else
        echo "Docker image '$IMAGE_TAG' already exists. Skipping build."
    fi

    # Step 2: Run a temporary container to copy cache files
    echo "Running temporary container to embed cache files..."
    docker run --name temp_container -d "$IMAGE_TAG" tail -f /dev/null

    # Step 3: Copy local cache files into the temporary container
    echo "Copying local cache files from '$LOCAL_CACHE_DIR' to '$CACHE_DIR' inside the container..."
    docker cp "$LOCAL_CACHE_DIR"/. temp_container:"$CACHE_DIR"/
    docker exec temp_container python -c "import nltk; nltk.download('punkt_tab')"

    # commit: Commit the container's state to a new image
    echo "Committing the container with cache files to a new image '$UPDATED_IMAGE_TAG'..."
    docker commit temp_container "$UPDATED_IMAGE_TAG"
    echo "New image '$UPDATED_IMAGE_TAG' created successfully."

    # final: Remove the temporary container
    echo "Removing temporary container 'temp_container'..."
    docker rm -f temp_container > /dev/null 2>&1
    echo "Temporary container removed."

    echo "Build process completed successfully."
}

# Function: Remove Existing Docker Container if It Exists
remove_container() {
    if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}$"; then
        echo "Removing existing Docker container '$CONTAINER_NAME'..."
        docker rm -f "$CONTAINER_NAME"
        echo "Docker container '$CONTAINER_NAME' removed."
    else
        echo "No existing Docker container named '$CONTAINER_NAME' found. Skipping removal."
    fi
}

# Function: Run Docker Container from Updated Image
run_container() {
    echo "Starting Docker container '$CONTAINER_NAME' from image '$UPDATED_IMAGE_TAG'..."

    docker run -d \
        -p "${HOST_PORT}:${CONTAINER_PORT}" \
        --add-host=host.docker.internal:host-gateway \
        -v "${CONTAINER_NAME}:${DATA_DIR}" \
        --name "$CONTAINER_NAME" \
        --restart always \
        --env-file "$ENV_FILE" \
        "$UPDATED_IMAGE_TAG" \
        bash start.sh

    echo "Docker container '$CONTAINER_NAME' started and running."
}

# ================================
# Usage Information
# ================================

show_help() {
    echo "Usage: $0 {build|push|deploy|run|help}"
    echo
    echo "Commands:"
    echo "  build    Build the Docker image and embed cache files."
    echo "  deploy   Perform both build and push operations."
    echo "  run      Remove existing container (if any) and run the container from the updated image."
    echo "  help     Display this help message."
    echo
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 push"
    echo "  $0 deploy"
    echo "  $0 run"
}

# ================================
# Main Execution Flow with Subcommands
# ================================

main() {
    # Ensure at least one argument is provided
    if [[ $# -lt 1 ]]; then
        show_help
        exit 1
    fi

    # Load and validate environment variables
    load_env
    validate_env
    define_variables

    # Handle subcommands
    case "$1" in
        build)
            build_image
            ;;
        deploy)
            build_image
            push_image
            ;;
        run)
            remove_container
            run_container
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Error: Unknown command '$1'"
            show_help
            exit 1
            ;;
    esac
}

# Invoke the main function with all script arguments
main "$@"

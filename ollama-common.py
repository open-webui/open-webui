# ollama-common.py

phrases = {
    "docker-compose.api.yaml": [
        'services:',
        'ollama:',
        '# Expose Ollama API outside the container stack',
        'ports:',
        '- ${OLLAMA_WEBAPI_PORT-11434}:11434'
    ],
    "docker-compose.yaml": [
        'ollama:',
        'volumes:',
        '- ollama:/root/.ollama',
        'container_name: ollama',
        'pull_policy: always',
        'tty: true',
        'restart: unless-stopped',
        'image: ollama/ollama:${OLLAMA_DOCKER_TAG-latest}',

        'args:',
        "OLLAMA_BASE_URL: '/ollama'",

        "depends_on:",
        "  - ollama",

        "environment:",
        "  - 'OLLAMA_BASE_URL=http://ollama:11434'",
        "  - 'WEBUI_SECRET_KEY='",

        "ollama: {}"
    ]
}

# 
# SKIP_OLLAMA_TESTS: 'true'
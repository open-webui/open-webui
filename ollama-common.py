# ollama-common.py

phrases = {
    "docker-compose.api.yaml": [
        'services:',
        'ollama:',
        '# Expose Ollama API outside the container stack',
        'ports:',
        '- ${OLLAMA_WEBAPI_PORT-11434}:11434'
    ]
}

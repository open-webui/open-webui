from fastapi import FastAPI

from open_webui.config import (
    AppConfig,
    WEBUI_NAME,
    ENABLE_OLLAMA_API,
    OLLAMA_BASE_URLS,
    OLLAMA_API_CONFIGS,
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URLS,
    OPENAI_API_KEYS,
    OPENAI_API_CONFIGS,
    ENABLE_DIRECT_CONNECTIONS,
    ENABLE_BASE_MODELS_CACHE,
    TOOL_SERVER_CONNECTIONS,
)
from open_webui.env import (
    REDIS_URL,
    REDIS_CLUSTER,
    REDIS_KEY_PREFIX,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_PORT,
    ENABLE_SCIM,
    SCIM_TOKEN,
)
from open_webui.utils.redis import get_sentinels_from_env


def initialize_app_state(app: FastAPI) -> None:
    """Initialize core shared app state used during bootstrap and runtime."""
    app.state.instance_id = None
    app.state.config = AppConfig(
        redis_url=REDIS_URL,
        redis_sentinels=get_sentinels_from_env(
            REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT
        ),
        redis_cluster=REDIS_CLUSTER,
        redis_key_prefix=REDIS_KEY_PREFIX,
    )
    app.state.redis = None

    app.state.WEBUI_NAME = WEBUI_NAME
    app.state.LICENSE_METADATA = None


def configure_provider_state(app: FastAPI) -> None:
    """Configure provider, tool-server and model bootstrap state."""
    app.state.config.ENABLE_OLLAMA_API = ENABLE_OLLAMA_API
    app.state.config.OLLAMA_BASE_URLS = OLLAMA_BASE_URLS
    app.state.config.OLLAMA_API_CONFIGS = OLLAMA_API_CONFIGS
    app.state.OLLAMA_MODELS = {}

    app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
    app.state.config.OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS
    app.state.config.OPENAI_API_KEYS = OPENAI_API_KEYS
    app.state.config.OPENAI_API_CONFIGS = OPENAI_API_CONFIGS
    app.state.OPENAI_MODELS = {}

    app.state.config.TOOL_SERVER_CONNECTIONS = TOOL_SERVER_CONNECTIONS
    app.state.TOOL_SERVERS = []

    app.state.config.ENABLE_DIRECT_CONNECTIONS = ENABLE_DIRECT_CONNECTIONS

    app.state.ENABLE_SCIM = ENABLE_SCIM
    app.state.SCIM_TOKEN = SCIM_TOKEN

    app.state.config.ENABLE_BASE_MODELS_CACHE = ENABLE_BASE_MODELS_CACHE
    app.state.BASE_MODELS = []

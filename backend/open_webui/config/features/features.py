import json
import os
from open_webui.config.core.base import PersistentConfig
from open_webui.env import log

####################################
# FEATURE TOGGLES
####################################

ENABLE_DIRECT_CONNECTIONS = PersistentConfig(
    "ENABLE_DIRECT_CONNECTIONS",
    "direct.enable",
    os.environ.get("ENABLE_DIRECT_CONNECTIONS", "False").lower() == "true",
)

ENABLE_BASE_MODELS_CACHE = PersistentConfig(
    "ENABLE_BASE_MODELS_CACHE",
    "models.base_models_cache",
    os.environ.get("ENABLE_BASE_MODELS_CACHE", "False").lower() == "true",
)

ENABLE_CHANNELS = PersistentConfig(
    "ENABLE_CHANNELS",
    "channels.enable",
    os.environ.get("ENABLE_CHANNELS", "False").lower() == "true",
)

ENABLE_NOTES = PersistentConfig(
    "ENABLE_NOTES",
    "notes.enable",
    os.environ.get("ENABLE_NOTES", "True").lower() == "true",
)

ENABLE_EVALUATION_ARENA_MODELS = PersistentConfig(
    "ENABLE_EVALUATION_ARENA_MODELS",
    "evaluation.arena.enable",
    os.environ.get("ENABLE_EVALUATION_ARENA_MODELS", "True").lower() == "true",
)

EVALUATION_ARENA_MODELS = PersistentConfig(
    "EVALUATION_ARENA_MODELS",
    "evaluation.arena.models",
    [],
)

DEFAULT_ARENA_MODEL = {
    "id": "arena-model",
    "name": "Arena Model",
    "meta": {
        "profile_image_url": "/favicon.png",
        "description": "Submit your questions to anonymous AI chatbots and vote on the best response.",
        "model_ids": None,
    },
}

####################################
# TOOL SERVERS
####################################

try:
    tool_server_connections = json.loads(
        os.environ.get("TOOL_SERVER_CONNECTIONS", "[]")
    )
except Exception as e:
    log.exception(f"Error loading TOOL_SERVER_CONNECTIONS: {e}")
    tool_server_connections = []

TOOL_SERVER_CONNECTIONS = PersistentConfig(
    "TOOL_SERVER_CONNECTIONS",
    "tool_server.connections",
    tool_server_connections,
)

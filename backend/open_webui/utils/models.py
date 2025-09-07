import time
import logging
import sys

from fastapi import Request

from open_webui.routers import openai, ollama
from open_webui.models.models import Models
from open_webui.utils.access_control import has_access
from open_webui.config import DEFAULT_ARENA_MODEL
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL
from open_webui.models.users import UserModel

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def get_all_base_models(request: Request):
    openai_models = []
    ollama_models = []

    if request.app.state.config.ENABLE_OPENAI_API:
        openai_models = await openai.get_all_models(request)
        openai_models = openai_models["data"]

    if request.app.state.config.ENABLE_OLLAMA_API:
        ollama_models = await ollama.get_all_models(request)
        ollama_models = [
            {
                "id": model["model"],
                "name": model["name"],
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama",
                "ollama": model,
                "tags": model.get("tags", []),
            }
            for model in ollama_models["models"]
        ]

    return openai_models + ollama_models


async def get_all_models(request):
    models = await get_all_base_models(request)

    # If there are no models, return an empty list
    if len(models) == 0:
        return []

    # Add arena models
    if request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS:
        if len(request.app.state.config.EVALUATION_ARENA_MODELS) > 0:
            arena_models = [
                {
                    "id": model["id"],
                    "name": model["name"],
                    "info": {
                        "meta": model["meta"],
                    },
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "arena",
                    "arena": True,
                }
                for model in request.app.state.config.EVALUATION_ARENA_MODELS
            ]
        else:
            # Add default arena model
            arena_models = [
                {
                    "id": DEFAULT_ARENA_MODEL["id"],
                    "name": DEFAULT_ARENA_MODEL["name"],
                    "info": {
                        "meta": DEFAULT_ARENA_MODEL["meta"],
                    },
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "arena",
                    "arena": True,
                }
            ]
        models = models + arena_models
    log.debug(f"get_all_models() returned {len(models)} models")

    request.app.state.MODELS = {model["id"]: model for model in models}
    return models

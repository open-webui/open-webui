import time
import logging
import asyncio
import sys

from aiocache import cached
from fastapi import Request

from open_webui.routers import openai, ollama
from open_webui.functions import get_function_models


from open_webui.models.functions import Functions
from open_webui.models.models import Models


from open_webui.utils.plugin import (
    load_function_module_by_id,
    get_function_module_from_cache,
)
from open_webui.utils.access_control import has_access


from open_webui.config import (
    DEFAULT_ARENA_MODEL,
)

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL
from open_webui.models.users import UserModel


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def fetch_ollama_models(request: Request, user: UserModel = None):
    raw_ollama_models = await ollama.get_all_models(request, user=user)
    return [
        {
            "id": model["model"],
            "name": model["name"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "ollama",
            "ollama": model,
            "connection_type": model.get("connection_type", "local"),
            "tags": model.get("tags", []),
        }
        for model in raw_ollama_models["models"]
    ]
    

async def fetch_openai_models(request: Request, user: UserModel = None):
    openai_response = await openai.get_all_models(request, user=user)
    return openai_response["data"]


async def get_all_base_models(request: Request, user: UserModel = None):
    openai_task = (
        fetch_openai_models(request, user)
        if request.app.state.config.ENABLE_OPENAI_API
        else asyncio.sleep(0, result=[])
    )
    ollama_task = (
        fetch_ollama_models(request, user)
        if request.app.state.config.ENABLE_OLLAMA_API
        else asyncio.sleep(0, result=[])
    )
    function_task = get_function_models(request)

    openai_models, ollama_models, function_models = await asyncio.gather(
        openai_task, ollama_task, function_task
    )

    return function_models + openai_models + ollama_models


async def get_all_models(request, user: UserModel = None):
    models = await get_all_base_models(request, user=user)

    if len(models) == 0:
        return []

    if request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS:
        arena_models = []
        if len(request.app.state.config.EVALUATION_ARENA_MODELS) > 0:
            arena_models = [
                {
                    "id": model["id"],
                    "name": model["name"],
                    "info": {"meta": model["meta"]},
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "arena",
                    "arena": True,
                }
                for model in request.app.state.config.EVALUATION_ARENA_MODELS
            ]
        else:
            arena_models = [
                {
                    "id": DEFAULT_ARENA_MODEL["id"],
                    "name": DEFAULT_ARENA_MODEL["name"],
                    "info": {"meta": DEFAULT_ARENA_MODEL["meta"]},
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "arena",
                    "arena": True,
                }
            ]
        models.extend(arena_models)

    global_action_ids = {function.id for function in Functions.get_global_action_functions()}
    enabled_action_ids = {function.id for function in Functions.get_functions_by_type("action", active_only=True)}
    global_filter_ids = {function.id for function in Functions.get_global_filter_functions()}
    enabled_filter_ids = {function.id for function in Functions.get_functions_by_type("filter", active_only=True)}

    custom_models = Models.get_all_models()
    active_custom_models = {model.id: model for model in custom_models if model.is_active}
    inactive_custom_models = {model.id: model for model in custom_models if not model.is_active}

    models_to_remove = []
    models_dict = {model["id"]: model for model in models}
    
    for model_id, model in models_dict.items():
        if model_id in inactive_custom_models and inactive_custom_models[model_id].base_model_id is None:
            models_to_remove.append(model)
        elif model_id in active_custom_models:
            custom_model = active_custom_models[model_id]
            if custom_model.base_model_id is None:
                model["name"] = custom_model.name
                model["info"] = custom_model.model_dump()
                
                action_ids = []
                filter_ids = []
                if "info" in model and "meta" in model["info"]:
                    action_ids.extend(model["info"]["meta"].get("actionIds", []))
                    filter_ids.extend(model["info"]["meta"].get("filterIds", []))
                
                model["action_ids"] = action_ids
                model["filter_ids"] = filter_ids

    for model in models_to_remove:
        models.remove(model)

    for custom_model in active_custom_models.values():
        if custom_model.base_model_id is not None and custom_model.id not in models_dict:
            owned_by = "openai"
            pipe = None
            
            for model in models:
                if (custom_model.base_model_id == model["id"] or 
                    custom_model.base_model_id == model["id"].split(":")[0]):
                    owned_by = model.get("owned_by", "unknown owner")
                    if "pipe" in model:
                        pipe = model["pipe"]
                    break

            action_ids = []
            filter_ids = []
            if custom_model.meta:
                meta = custom_model.meta.model_dump()
                action_ids.extend(meta.get("actionIds", []))
                filter_ids.extend(meta.get("filterIds", []))

            new_model = {
                "id": custom_model.id,
                "name": custom_model.name,
                "object": "model",
                "created": custom_model.created_at,
                "owned_by": owned_by,
                "info": custom_model.model_dump(),
                "preset": True,
                "action_ids": action_ids,
                "filter_ids": filter_ids,
            }
            if pipe is not None:
                new_model["pipe"] = pipe
            
            models.append(new_model)

    all_action_ids = set()
    all_filter_ids = set()
    
    for model in models:
        model_action_ids = set(model.get("action_ids", []))
        model_filter_ids = set(model.get("filter_ids", []))
        
        model_action_ids.update(global_action_ids)
        model_filter_ids.update(global_filter_ids)
        
        model_action_ids.intersection_update(enabled_action_ids)
        model_filter_ids.intersection_update(enabled_filter_ids)
        
        model["final_action_ids"] = model_action_ids
        model["final_filter_ids"] = model_filter_ids
        
        all_action_ids.update(model_action_ids)
        all_filter_ids.update(model_filter_ids)

    action_functions_map = {}
    filter_functions_map = {}
    
    if all_action_ids:
        action_functions = Functions.get_functions_by_ids(list(all_action_ids))
        action_functions_map = {func.id: func for func in action_functions if func is not None}
    
    if all_filter_ids:
        filter_functions = Functions.get_functions_by_ids(list(all_filter_ids))
        filter_functions_map = {func.id: func for func in filter_functions if func is not None}

    function_modules_cache = {}
    all_function_ids = all_action_ids.union(all_filter_ids)
    
    for function_id in all_function_ids:
        try:
            function_module, _, _ = get_function_module_from_cache(request, function_id)
            function_modules_cache[function_id] = function_module
        except Exception as e:
            log.warning(f"Failed to load function module {function_id}: {e}")
            continue

    def get_action_items_from_module(function, module):
        if hasattr(module, "actions"):
            return [
                {
                    "id": f"{function.id}.{action['id']}",
                    "name": action.get("name", f"{function.name} ({action['id']})"),
                    "description": function.meta.description,
                    "icon": action.get(
                        "icon_url",
                        function.meta.manifest.get("icon_url", None)
                        or getattr(module, "icon_url", None)
                        or getattr(module, "icon", None),
                    ),
                }
                for action in module.actions
            ]
        else:
            return [
                {
                    "id": function.id,
                    "name": function.name,
                    "description": function.meta.description,
                    "icon": function.meta.manifest.get("icon_url", None)
                    or getattr(module, "icon_url", None)
                    or getattr(module, "icon", None),
                }
            ]

    def get_filter_items_from_module(function, module):
        return [
            {
                "id": function.id,
                "name": function.name,
                "description": function.meta.description,
                "icon": function.meta.manifest.get("icon_url", None)
                or getattr(module, "icon_url", None)
                or getattr(module, "icon", None),
            }
        ]

    for model in models:
        final_action_ids = model.pop("final_action_ids", set())
        final_filter_ids = model.pop("final_filter_ids", set())
        model.pop("action_ids", None)
        model.pop("filter_ids", None)

        model["actions"] = []
        for action_id in final_action_ids:
            if action_id in action_functions_map and action_id in function_modules_cache:
                action_function = action_functions_map[action_id]
                function_module = function_modules_cache[action_id]
                model["actions"].extend(
                    get_action_items_from_module(action_function, function_module)
                )

        model["filters"] = []
        for filter_id in final_filter_ids:
            if filter_id in filter_functions_map and filter_id in function_modules_cache:
                filter_function = filter_functions_map[filter_id]
                function_module = function_modules_cache[filter_id]
                
                if getattr(function_module, "toggle", None):
                    model["filters"].extend(
                        get_filter_items_from_module(filter_function, function_module)
                    )

    log.debug(f"get_all_models() returned {len(models)} models")

    request.app.state.MODELS = {model["id"]: model for model in models}
    return models



def check_model_access(user, model):
    if model.get("arena"):
        if not has_access(
            user.id,
            type="read",
            access_control=model.get("info", {})
            .get("meta", {})
            .get("access_control", {}),
        ):
            raise Exception("Model not found")
    else:
        model_info = Models.get_model_by_id(model.get("id"))
        if not model_info:
            raise Exception("Model not found")
        elif not (
            user.id == model_info.user_id
            or has_access(
                user.id, type="read", access_control=model_info.access_control
            )
        ):
            raise Exception("Model not found")

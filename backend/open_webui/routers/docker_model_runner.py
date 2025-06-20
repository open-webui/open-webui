import logging
import time
from typing import Optional, Union

import aiohttp
from aiocache import cached
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from starlette.background import BackgroundTask

from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    BYPASS_MODEL_ACCESS_CONTROL,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    SRC_LOG_LEVELS
)
from open_webui.models.users import UserModel
from open_webui.models.models import Models
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DMR"])

router = APIRouter()

# DMR-specific constants
DMR_ENGINE_SUFFIX = "/engines/llama.cpp/v1"

##########################################
#
# Utility functions
#
##########################################

async def send_get_request(url, user: UserModel = None):
    """Send a GET request to DMR backend with proper error handling"""
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url,
                headers={
                    "Content-Type": "application/json",
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS and user
                        else {}
                    ),
                },
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        log.error(f"DMR connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    """Clean up aiohttp resources"""
    if response:
        response.close()
    if session:
        await session.close()


async def send_post_request(
    url: str,
    payload: Union[str, bytes, dict],
    stream: bool = False,
    content_type: Optional[str] = None,
    user: UserModel = None,
):
    """Send POST request to DMR backend with proper error handling"""
    r = None
    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.post(
            url,
            data=payload if isinstance(payload, (str, bytes)) else aiohttp.JsonPayload(payload),
            headers={
                "Content-Type": content_type or "application/json",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user
                    else {}
                ),
            },
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        r.raise_for_status()

        if stream:
            response_headers = dict(r.headers)
            if content_type:
                response_headers["Content-Type"] = content_type

            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=response_headers,
                background=BackgroundTask(cleanup_response, response=r, session=session),
            )
        else:
            res = await r.json()
            await cleanup_response(r, session)
            return res

    except Exception as e:
        detail = None
        if r is not None:
            try:
                res = await r.json()
                if "error" in res:
                    detail = f"DMR: {res.get('error', 'Unknown error')}"
            except Exception:
                detail = f"DMR: {e}"

        await cleanup_response(r, session)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "Open WebUI: DMR Connection Error",
        )


def get_dmr_base_url(request: Request):
    """Get DMR base URL with engine suffix"""
    base_url = request.app.state.config.DMR_BASE_URL
    if not base_url:
        raise HTTPException(status_code=500, detail="DMR base URL not configured")
    
    # Always append the engine prefix for OpenAI-compatible endpoints
    if not base_url.rstrip("/").endswith(DMR_ENGINE_SUFFIX):
        base_url = base_url.rstrip("/") + DMR_ENGINE_SUFFIX
    return base_url


@cached(ttl=1)
async def get_all_models(request: Request, user: UserModel = None):
    """
    Fetch all models from the DMR backend in OpenAI-compatible format for internal use.
    Returns: dict with 'data' key (list of models)
    """
    log.info("get_all_models() - DMR")
    
    if not request.app.state.config.ENABLE_DMR_API:
        return {"data": []}
    
    try:
        url = get_dmr_base_url(request)
        
        response = await send_get_request(f"{url}/models", user=user)
        if response is None:
            return {"data": []}
        
        # Ensure response is in correct format
        if isinstance(response, dict) and "data" in response:
            # Transform models to include Open WebUI required fields
            models = []
            for m in response["data"]:
                # Ensure each model has a 'name' field for frontend compatibility
                if "name" not in m:
                    m["name"] = m["id"]
                
                # Add Open WebUI specific fields
                model = {
                    "id": m["id"],
                    "name": m["name"],
                    "object": m.get("object", "model"),
                    "created": m.get("created", int(time.time())),
                    "owned_by": "docker",
                    "dmr": m,  # Store original DMR model data
                    "connection_type": "local",
                    "tags": [],
                }
                models.append(model)
            
            return {"data": models}
        elif isinstance(response, list):
            # Convert list to OpenAI format with Open WebUI fields
            models = []
            for m in response:
                if isinstance(m, str):
                    model = {
                        "id": m,
                        "name": m,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "docker",
                        "dmr": {"id": m, "name": m},
                        "connection_type": "local",
                        "tags": [],
                    }
                elif isinstance(m, dict):
                    model_id = m.get("id") or m.get("name") or str(m)
                    model = {
                        "id": model_id,
                        "name": m.get("name", model_id),
                        "object": m.get("object", "model"),
                        "created": m.get("created", int(time.time())),
                        "owned_by": "docker",
                        "dmr": m,
                        "connection_type": "local",
                        "tags": [],
                    }
                models.append(model)
            return {"data": models}
        else:
            # Fallback: wrap in data with Open WebUI fields
            if response:
                model = {
                    "id": str(response),
                    "name": str(response),
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "docker",
                    "dmr": response,
                    "connection_type": "local",
                    "tags": [],
                }
                return {"data": [model]}
            return {"data": []}
    except Exception as e:
        log.exception(f"DMR get_all_models failed: {e}")
        return {"data": []}


async def get_filtered_models(models, user):
    """Filter models based on user access control"""
    if BYPASS_MODEL_ACCESS_CONTROL:
        return models.get("data", [])
    
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
        else:
            # If no model info found and user is admin, include it
            if user.role == "admin":
                filtered_models.append(model)
    return filtered_models


##########################################
#
# Configuration endpoints
#
##########################################

@router.head("/")
@router.get("/")
async def get_status():
    return {"status": True}


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    """Get DMR configuration"""
    return {
        "ENABLE_DMR_API": request.app.state.config.ENABLE_DMR_API,
        "DMR_BASE_URL": request.app.state.config.DMR_BASE_URL,
        "DMR_API_CONFIGS": request.app.state.config.DMR_API_CONFIGS,
    }


class DMRConfigForm(BaseModel):
    ENABLE_DMR_API: Optional[bool] = None
    DMR_BASE_URL: str
    DMR_API_CONFIGS: dict = {}


@router.post("/config/update")
async def update_config(request: Request, form_data: DMRConfigForm, user=Depends(get_admin_user)):
    """Update DMR configuration"""
    request.app.state.config.ENABLE_DMR_API = form_data.ENABLE_DMR_API
    request.app.state.config.DMR_BASE_URL = form_data.DMR_BASE_URL
    request.app.state.config.DMR_API_CONFIGS = form_data.DMR_API_CONFIGS

    return {
        "ENABLE_DMR_API": request.app.state.config.ENABLE_DMR_API,
        "DMR_BASE_URL": request.app.state.config.DMR_BASE_URL,
        "DMR_API_CONFIGS": request.app.state.config.DMR_API_CONFIGS,
    }


class ConnectionVerificationForm(BaseModel):
    url: str


@router.post("/verify")
async def verify_connection(form_data: ConnectionVerificationForm, user=Depends(get_admin_user)):
    """Verify connection to DMR backend"""
    url = form_data.url
    
    # Append engine suffix if not present
    if not url.rstrip("/").endswith(DMR_ENGINE_SUFFIX):
        url = url.rstrip("/") + DMR_ENGINE_SUFFIX
    
    try:
        response = await send_get_request(f"{url}/models", user=user)
        if response is not None:
            return {"status": "success", "message": "Connection verified"}
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to DMR backend")
    except Exception as e:
        log.exception(f"DMR connection verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Connection verification failed: {e}")


##########################################
#
# Model endpoints
#
##########################################

@router.get("/api/tags")
async def get_dmr_tags(request: Request, user=Depends(get_verified_user)):
    """Get available models from DMR backend (Ollama-compatible format)"""
    models = await get_all_models(request, user=user)
    
    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        filtered_models = await get_filtered_models(models, user)
        models = {"data": filtered_models}
    
    # Convert to Ollama-compatible format
    ollama_models = []
    for model in models.get("data", []):
        ollama_model = {
            "model": model["id"],
            "name": model["name"],
            "size": model.get("size", 0),
            "digest": model.get("digest", ""),
            "details": model.get("details", {}),
            "expires_at": model.get("expires_at"),
            "size_vram": model.get("size_vram", 0),
        }
        ollama_models.append(ollama_model)
    
    return {"models": ollama_models}


@router.get("/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    """Get available models from DMR backend (OpenAI-compatible format)"""
    models = await get_all_models(request, user=user)
    
    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        filtered_models = await get_filtered_models(models, user)
        return {"data": filtered_models}
    
    return models


class ModelNameForm(BaseModel):
    name: str


@router.post("/api/show")
async def show_model_info(
    request: Request, form_data: ModelNameForm, user=Depends(get_verified_user)
):
    """Show model information (Ollama-compatible)"""
    models = await get_all_models(request, user=user)
    
    # Find the model
    model_found = None
    for model in models.get("data", []):
        if model["id"] == form_data.name or model["name"] == form_data.name:
            model_found = model
            break
    
    if not model_found:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
        )
    
    # Return model info in Ollama format
    return {
        "model": model_found["id"],
        "details": model_found.get("dmr", {}),
        "modelfile": "",  # DMR doesn't provide modelfile
        "parameters": "",  # DMR doesn't provide parameters
        "template": "",   # DMR doesn't provide template
    }


##########################################
#
# Generation endpoints
#
##########################################

class GenerateChatCompletionForm(BaseModel):
    model: str
    messages: list[dict]
    stream: Optional[bool] = False
    model_config = ConfigDict(extra="allow")


@router.post("/api/chat")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    """Generate chat completions using DMR backend (Ollama-compatible)"""
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    metadata = form_data.pop("metadata", None)
    
    try:
        completion_form = GenerateChatCompletionForm(**form_data)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=400, detail=str(e))
    
    payload = {**completion_form.model_dump(exclude_none=True)}
    if "metadata" in payload:
        del payload["metadata"]

    model_id = payload["model"]
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop("system", None)
            payload = apply_model_params_to_body_openai(params, payload)
            payload = apply_model_system_prompt_to_body(system, payload, metadata, user)

        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    url = get_dmr_base_url(request)
    
    log.debug(f"DMR chat completion: model = {payload.get('model', 'NO_MODEL')}")
    
    return await send_post_request(
        f"{url}/chat/completions",
        payload,
        stream=payload.get("stream", False),
        content_type="application/x-ndjson" if payload.get("stream") else None,
        user=user,
    )


class GenerateCompletionForm(BaseModel):
    model: str
    prompt: str
    stream: Optional[bool] = False
    model_config = ConfigDict(extra="allow")


@router.post("/api/generate")
async def generate_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """Generate completions using DMR backend (Ollama-compatible)"""
    try:
        completion_form = GenerateCompletionForm(**form_data)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=400, detail=str(e))
    
    payload = {**completion_form.model_dump(exclude_none=True)}
    
    model_id = payload["model"]
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            payload = apply_model_params_to_body_openai(params, payload)

        # Check if user has access to the model
        if user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    else:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    url = get_dmr_base_url(request)
    
    return await send_post_request(
        f"{url}/completions",
        payload,
        stream=payload.get("stream", False),
        user=user,
    )


class GenerateEmbeddingsForm(BaseModel):
    model: str
    input: Union[str, list[str]]
    model_config = ConfigDict(extra="allow")


@router.post("/api/embeddings")
async def embeddings(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate embeddings using DMR backend (Ollama-compatible)"""
    try:
        embedding_form = GenerateEmbeddingsForm(**form_data)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=400, detail=str(e))
    
    payload = {**embedding_form.model_dump(exclude_none=True)}
    
    model_id = payload["model"]
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        # Check if user has access to the model
        if user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    else:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    url = get_dmr_base_url(request)
    
    return await send_post_request(f"{url}/embeddings", payload, stream=False, user=user)


##########################################
#
# OpenAI-compatible endpoints
#
##########################################

@router.get("/v1/models")
async def get_openai_models(request: Request, user=Depends(get_verified_user)):
    """Get available models from DMR backend (OpenAI-compatible)"""
    models = await get_all_models(request, user=user)
    
    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        filtered_models = await get_filtered_models(models, user)
        models = {"data": filtered_models}
    
    # Convert to OpenAI format
    openai_models = []
    for model in models.get("data", []):
        openai_model = {
            "id": model["id"],
            "object": "model",
            "created": model.get("created", int(time.time())),
            "owned_by": "docker",
        }
        openai_models.append(openai_model)
    
    return {
        "object": "list",
        "data": openai_models,
    }


@router.post("/v1/chat/completions")
async def generate_openai_chat_completion(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate chat completions using DMR backend (OpenAI-compatible)"""
    metadata = form_data.pop("metadata", None)
    
    payload = {**form_data}
    if "metadata" in payload:
        del payload["metadata"]

    model_id = payload["model"]
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop("system", None)
            payload = apply_model_params_to_body_openai(params, payload)
            payload = apply_model_system_prompt_to_body(system, payload, metadata, user)

        # Check if user has access to the model
        if user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    else:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    url = get_dmr_base_url(request)
    
    return await send_post_request(
        f"{url}/chat/completions",
        payload,
        stream=payload.get("stream", False),
        user=user,
    )


@router.post("/v1/completions")
async def generate_openai_completion(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate completions using DMR backend (OpenAI-compatible)"""
    payload = {**form_data}
    
    model_id = payload["model"]
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            payload = apply_model_params_to_body_openai(params, payload)

        # Check if user has access to the model
        if user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    else:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    url = get_dmr_base_url(request)
    
    return await send_post_request(
        f"{url}/completions",
        payload,
        stream=payload.get("stream", False),
        user=user,
    )


@router.post("/v1/embeddings")
async def generate_openai_embeddings(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate embeddings using DMR backend (OpenAI-compatible)"""
    payload = {**form_data}
    
    model_id = payload["model"]
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        # Check if user has access to the model
        if user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    else:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    url = get_dmr_base_url(request)
    
    return await send_post_request(f"{url}/embeddings", payload, stream=False, user=user)

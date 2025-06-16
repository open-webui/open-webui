import logging
import aiohttp
from typing import Union
from urllib.parse import urlparse
import time

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from open_webui.models.users import UserModel
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL, 
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    SRC_LOG_LEVELS
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("DMR", logging.INFO))

router = APIRouter()

# DMR-specific constants
DMR_ENGINE_SUFFIX = "/engines/llama.cpp/v1"

##########################################
#
# Utility functions
#
##########################################

async def send_get_request(url, user: UserModel = None):
    """Send GET request to DMR backend with proper error handling"""
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
        )
        r.raise_for_status()

        if stream:
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
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
        raise HTTPException(status_code=500, detail="No DMR base URL configured")
    
    # Always append the engine prefix for OpenAI-compatible endpoints
    if not base_url.rstrip("/").endswith(DMR_ENGINE_SUFFIX):
        base_url = base_url.rstrip("/") + DMR_ENGINE_SUFFIX
    return base_url


##########################################
#
# API routes
#
##########################################

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


@router.get("/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    """Get available models from DMR backend"""
    url = get_dmr_base_url(request)
    
    response = await send_get_request(f"{url}/models", user=user)
    if response is None:
        raise HTTPException(status_code=500, detail="Failed to fetch models from DMR backend")
    return response


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    """Generate chat completions using DMR backend"""
    url = get_dmr_base_url(request)
    
    log.debug(f"DMR chat_completions: model = {form_data.get('model', 'NO_MODEL')}")
    
    # Resolve model ID if needed
    if "model" in form_data:
        models = await get_all_models(request, user=user)
        for m in models.get("data", []):
            if m.get("id") == form_data["model"] or m.get("name") == form_data["model"]:
                form_data["model"] = m["id"]
                break
    
    return await send_post_request(
        f"{url}/chat/completions", 
        form_data, 
        stream=form_data.get("stream", False), 
        user=user
    )


@router.post("/completions")
async def generate_completion(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user),
):
    """Generate completions using DMR backend"""
    url = get_dmr_base_url(request)
    
    # Resolve model ID if needed
    if "model" in form_data:
        models = await get_all_models(request, user=user)
        for m in models.get("data", []):
            if m.get("id") == form_data["model"] or m.get("name") == form_data["model"]:
                form_data["model"] = m["id"]
                break
    
    return await send_post_request(
        f"{url}/completions", 
        form_data, 
        stream=form_data.get("stream", False), 
        user=user
    )


@router.post("/embeddings")
async def embeddings(request: Request, form_data: dict, user=Depends(get_verified_user)):
    """Generate embeddings using DMR backend"""
    url = get_dmr_base_url(request)
    
    return await send_post_request(f"{url}/embeddings", form_data, stream=False, user=user)


# OpenAI-compatible endpoints
@router.get("/v1/models")
async def get_openai_models(request: Request, user=Depends(get_verified_user)):
    """Get available models from DMR backend (OpenAI-compatible)"""
    return await get_models(request, user)


@router.post("/v1/chat/completions")
async def generate_openai_chat_completion(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate chat completions using DMR backend (OpenAI-compatible)"""
    return await generate_chat_completion(request, form_data, user)


@router.post("/v1/completions")
async def generate_openai_completion(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate completions using DMR backend (OpenAI-compatible)"""
    return await generate_completion(request, form_data, user)


@router.post("/v1/embeddings")
async def generate_openai_embeddings(
    request: Request, 
    form_data: dict, 
    user=Depends(get_verified_user)
):
    """Generate embeddings using DMR backend (OpenAI-compatible)"""
    return await embeddings(request, form_data, user)


# Internal utility for Open WebUI model aggregation
async def get_all_models(request: Request, user: UserModel = None):
    """
    Fetch all models from the DMR backend in OpenAI-compatible format for internal use.
    Returns: dict with 'data' key (list of models)
    """
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

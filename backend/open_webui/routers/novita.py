import asyncio
import hashlib
import json
import logging
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from aiocache import cached

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

from pydantic import BaseModel

from open_webui.models.models import Models
from open_webui.env import (
    MODELS_CACHE_TTL,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
    stream_chunks_handler,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)

router = APIRouter()

"""
Novita AI Provider Router

Novita AI provides an OpenAI-compatible API at https://api.novita.ai/openai
This router handles Novita-specific configuration and API calls.
"""

# Default Novita models (from CLAUDE.md)
DEFAULT_NOVITA_MODELS = [
    {
        "id": "moonshotai/kimi-k2.5",
        "name": "Kimi K2.5 (Default)",
        "owned_by": "novita",
        "context_length": 262144,
        "max_output": 262144,
    },
    {
        "id": "zai-org/glm-5",
        "name": "GLM 5",
        "owned_by": "novita",
        "context_length": 202800,
        "max_output": 131072,
    },
    {
        "id": "minimax/minimax-m2.5",
        "name": "MiniMax M2.5",
        "owned_by": "novita",
        "context_length": 204800,
        "max_output": 131100,
    },
    {
        "id": "qwen/qwen3-embedding-0.6b",
        "name": "Qwen3 Embedding 0.6B",
        "owned_by": "novita",
        "type": "embedding",
    },
]


async def send_get_request(url, key=None, user: UserModel = None):
    """Send a GET request to the Novita API."""
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                **({"Authorization": f"Bearer {key}"} if key else {}),
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            async with session.get(
                url,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        log.error(f"Novita connection error: {e}")
        return None


async def get_novita_models(url, key, user: UserModel = None):
    """Fetch models from Novita API endpoint."""
    try:
        response = await send_get_request(f"{url}/models", key, user=user)
        if response and "data" in response:
            return response
        elif response and isinstance(response, list):
            return {"data": response}
        else:
            # Return default models if API call fails
            return {"data": DEFAULT_NOVITA_MODELS}
    except Exception as e:
        log.warning(f"Failed to fetch Novita models, using defaults: {e}")
        return {"data": DEFAULT_NOVITA_MODELS}


async def get_headers_and_cookies(
    request: Request,
    url,
    key=None,
    config=None,
    metadata: Optional[dict] = None,
    user: UserModel = None,
):
    """Build headers for Novita API requests."""
    headers = {
        "Content-Type": "application/json",
    }

    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)

    if key:
        headers["Authorization"] = f"Bearer {key}"

    if config and config.get("headers"):
        headers = {**headers, **config.get("headers")}

    return headers, {}


##########################################
# Configuration Endpoints
##########################################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_NOVITA_API": request.app.state.config.ENABLE_NOVITA_API,
        "NOVITA_API_BASE_URLS": request.app.state.config.NOVITA_API_BASE_URLS,
        "NOVITA_API_KEYS": request.app.state.config.NOVITA_API_KEYS,
        "NOVITA_API_CONFIGS": request.app.state.config.NOVITA_API_CONFIGS,
    }


class NovitaConfigForm(BaseModel):
    ENABLE_NOVITA_API: Optional[bool] = None
    NOVITA_API_BASE_URLS: list[str]
    NOVITA_API_KEYS: list[str]
    NOVITA_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: NovitaConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_NOVITA_API = form_data.ENABLE_NOVITA_API
    request.app.state.config.NOVITA_API_BASE_URLS = form_data.NOVITA_API_BASE_URLS
    request.app.state.config.NOVITA_API_KEYS = form_data.NOVITA_API_KEYS

    # Ensure keys length matches URLs length
    if len(request.app.state.config.NOVITA_API_KEYS) != len(
        request.app.state.config.NOVITA_API_BASE_URLS
    ):
        if len(request.app.state.config.NOVITA_API_KEYS) > len(
            request.app.state.config.NOVITA_API_BASE_URLS
        ):
            request.app.state.config.NOVITA_API_KEYS = (
                request.app.state.config.NOVITA_API_KEYS[
                    : len(request.app.state.config.NOVITA_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.NOVITA_API_KEYS += [""] * (
                len(request.app.state.config.NOVITA_API_BASE_URLS)
                - len(request.app.state.config.NOVITA_API_KEYS)
            )

    request.app.state.config.NOVITA_API_CONFIGS = form_data.NOVITA_API_CONFIGS

    # Remove configs for URLs that no longer exist
    keys = list(map(str, range(len(request.app.state.config.NOVITA_API_BASE_URLS))))
    request.app.state.config.NOVITA_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.NOVITA_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_NOVITA_API": request.app.state.config.ENABLE_NOVITA_API,
        "NOVITA_API_BASE_URLS": request.app.state.config.NOVITA_API_BASE_URLS,
        "NOVITA_API_KEYS": request.app.state.config.NOVITA_API_KEYS,
        "NOVITA_API_CONFIGS": request.app.state.config.NOVITA_API_CONFIGS,
    }


##########################################
# Models Endpoints
##########################################


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    """Get model responses from all configured Novita endpoints."""
    if not request.app.state.config.ENABLE_NOVITA_API:
        return []

    api_base_urls = request.app.state.config.NOVITA_API_BASE_URLS
    api_keys = list(request.app.state.config.NOVITA_API_KEYS)
    api_configs = request.app.state.config.NOVITA_API_CONFIGS

    num_urls = len(api_base_urls)
    num_keys = len(api_keys)

    if num_keys != num_urls:
        if num_keys > num_urls:
            api_keys = api_keys[:num_urls]
        else:
            api_keys += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(api_base_urls):
        if str(idx) not in api_configs:
            request_tasks.append(get_novita_models(url, api_keys[idx], user=user))
        else:
            api_config = api_configs.get(str(idx), {})
            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        get_novita_models(url, api_keys[idx], user=user)
                    )
                else:
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "novita",
                                "novita": {"id": model_id},
                                "urlIdx": idx,
                            }
                            for model_id in model_ids
                        ],
                    }
                    request_tasks.append(
                        asyncio.ensure_future(asyncio.sleep(0, model_list))
                    )
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)
    return responses


@cached(
    ttl=MODELS_CACHE_TTL,
    key=lambda _, user: f"novita_all_models_{user.id}" if user else "novita_all_models",
)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    """Get all available Novita models."""
    log.info("get_novita_all_models()")

    if not request.app.state.config.ENABLE_NOVITA_API:
        return {"data": []}

    api_base_urls = request.app.state.config.NOVITA_API_BASE_URLS
    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def get_merged_models(model_lists):
        models = {}
        for idx, model_list in enumerate(model_lists):
            if model_list is not None and "error" not in model_list:
                for model in model_list:
                    model_id = model.get("id") or model.get("name")
                    if model_id and model_id not in models:
                        models[model_id] = {
                            **model,
                            "name": model.get("name", model_id),
                            "owned_by": model.get("owned_by", "novita"),
                            "novita": model,
                            "connection_type": "external",
                            "urlIdx": idx,
                        }
        return models

    models = get_merged_models(map(extract_data, responses))
    request.app.state.NOVITA_MODELS = models
    return {"data": list(models.values())}


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    if not request.app.state.config.ENABLE_NOVITA_API:
        raise HTTPException(status_code=503, detail="Novita API is disabled")

    models = {"data": []}

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.NOVITA_API_BASE_URLS[url_idx]
        key = request.app.state.config.NOVITA_API_KEYS[url_idx]

        r = None
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                models = await get_novita_models(url, key, user=user)
            except Exception as e:
                log.exception(f"Error fetching Novita models: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error fetching Novita models: {str(e)}",
                )

    return models


##########################################
# Connection Verification
##########################################


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str
    config: Optional[dict] = None


@router.post("/verify")
async def verify_connection(
    request: Request,
    form_data: ConnectionVerificationForm,
    user=Depends(get_admin_user),
):
    """Verify Novita API connection."""
    url = form_data.url
    key = form_data.key

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            headers = {"Authorization": f"Bearer {key}"}
            async with session.get(
                f"{url}/models",
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                try:
                    response_data = await r.json()
                except Exception:
                    response_data = await r.text()

                if r.status != 200:
                    if isinstance(response_data, (dict, list)):
                        return JSONResponse(status_code=r.status, content=response_data)
                    else:
                        return JSONResponse(
                            status_code=r.status,
                            content={"error": response_data},
                        )

                return response_data

        except aiohttp.ClientError as e:
            log.exception(f"Novita connection error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )


##########################################
# Chat Completions
##########################################


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
    bypass_system_prompt: bool = False,
):
    """Generate chat completion using Novita API."""
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0
    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop("system", None)
            payload = apply_model_params_to_body_openai(params, payload)
            if not bypass_system_prompt:
                payload = apply_system_prompt_to_body(system, payload, metadata, user)

        # Check user access
        if not bypass_filter and user.role == "user":
            if user.id != model_info.user_id:
                raise HTTPException(status_code=403, detail="Model not found")

    # Get model from app state
    models = request.app.state.NOVITA_MODELS
    if not models or model_id not in models:
        await get_all_models(request, user=user)
        models = request.app.state.NOVITA_MODELS

    model = models.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get API config
    api_config = request.app.state.config.NOVITA_API_CONFIGS.get(str(idx), {})

    # Handle prefix_id
    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    url = request.app.state.config.NOVITA_API_BASE_URLS[idx]
    key = request.app.state.config.NOVITA_API_KEYS[idx]

    # Handle logit_bias
    if "logit_bias" in payload and payload["logit_bias"]:
        logit_bias = convert_logit_bias_input_to_json(payload["logit_bias"])
        if logit_bias:
            payload["logit_bias"] = json.loads(logit_bias)

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, metadata, user=user
    )

    payload = json.dumps(payload)

    r = None
    session = None
    streaming = False

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=None)
        )

        async with session.post(
            f"{url}/chat/completions",
            data=payload,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            if r.status != 200:
                raise Exception(f"HTTP {r.status}")

            content_type = r.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                streaming = True

                async def stream_generator():
                    try:
                        async for chunk in r.content.iter_any():
                            yield chunk
                    finally:
                        if session and not session.closed:
                            await session.close()

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                )
            else:
                try:
                    response_data = await r.json()
                    return response_data
                except Exception:
                    response_data = await r.text()
                    return JSONResponse(content={"error": response_data})

    except Exception as e:
        log.exception(f"Novita chat completion error: {e}")
        if session and not session.closed:
            await session.close()
        raise HTTPException(status_code=500, detail=str(e))

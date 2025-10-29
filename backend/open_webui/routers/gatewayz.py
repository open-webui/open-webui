import asyncio
import hashlib
import json
import logging
from typing import Optional

import aiohttp
from aiocache import cached
import requests
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from open_webui.models.models import Models
from open_webui.config import CACHE_DIR
from open_webui.env import (
    MODELS_CACHE_TTL,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.misc import convert_logit_bias_input_to_json

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("GATEWAYZ", "INFO"))


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url, key=None, user: UserModel = None):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url,
                headers={
                    **({"Authorization": f"Bearer {key}"} if key else {}),
                    **(
                        {
                            "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
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
        log.error(f"Connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


async def get_headers_and_cookies(
    request: Request,
    url,
    key=None,
    config=None,
    metadata: Optional[dict] = None,
    user: UserModel = None,
):
    cookies = {}
    headers = {
        "Content-Type": "application/json",
        **(
            {
                "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                "X-OpenWebUI-User-Id": user.id,
                "X-OpenWebUI-User-Email": user.email,
                "X-OpenWebUI-User-Role": user.role,
                **(
                    {"X-OpenWebUI-Chat-Id": metadata.get("chat_id")}
                    if metadata and metadata.get("chat_id")
                    else {}
                ),
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS
            else {}
        ),
    }

    token = None
    auth_type = config.get("auth_type") if config else None

    if auth_type == "bearer" or auth_type is None:
        # Default to bearer if not specified
        token = f"{key}"
    elif auth_type == "none":
        token = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if config and config.get("headers") and isinstance(config.get("headers"), dict):
        headers = {**headers, **config.get("headers")}

    return headers, cookies


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_GATEWAYZ_API": request.app.state.config.ENABLE_GATEWAYZ_API,
        "GATEWAYZ_API_BASE_URLS": request.app.state.config.GATEWAYZ_API_BASE_URLS,
        "GATEWAYZ_API_KEYS": request.app.state.config.GATEWAYZ_API_KEYS,
        "GATEWAYZ_API_CONFIGS": request.app.state.config.GATEWAYZ_API_CONFIGS,
    }


class GatewayzConfigForm(BaseModel):
    ENABLE_GATEWAYZ_API: Optional[bool] = None
    GATEWAYZ_API_BASE_URLS: list[str]
    GATEWAYZ_API_KEYS: list[str]
    GATEWAYZ_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: GatewayzConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_GATEWAYZ_API = form_data.ENABLE_GATEWAYZ_API
    request.app.state.config.GATEWAYZ_API_BASE_URLS = form_data.GATEWAYZ_API_BASE_URLS
    request.app.state.config.GATEWAYZ_API_KEYS = form_data.GATEWAYZ_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.GATEWAYZ_API_KEYS) != len(
        request.app.state.config.GATEWAYZ_API_BASE_URLS
    ):
        if len(request.app.state.config.GATEWAYZ_API_KEYS) > len(
            request.app.state.config.GATEWAYZ_API_BASE_URLS
        ):
            request.app.state.config.GATEWAYZ_API_KEYS = (
                request.app.state.config.GATEWAYZ_API_KEYS[
                    : len(request.app.state.config.GATEWAYZ_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.GATEWAYZ_API_KEYS += [""] * (
                len(request.app.state.config.GATEWAYZ_API_BASE_URLS)
                - len(request.app.state.config.GATEWAYZ_API_KEYS)
            )

    request.app.state.config.GATEWAYZ_API_CONFIGS = form_data.GATEWAYZ_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.GATEWAYZ_API_BASE_URLS))))
    request.app.state.config.GATEWAYZ_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.GATEWAYZ_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_GATEWAYZ_API": request.app.state.config.ENABLE_GATEWAYZ_API,
        "GATEWAYZ_API_BASE_URLS": request.app.state.config.GATEWAYZ_API_BASE_URLS,
        "GATEWAYZ_API_KEYS": request.app.state.config.GATEWAYZ_API_KEYS,
        "GATEWAYZ_API_CONFIGS": request.app.state.config.GATEWAYZ_API_CONFIGS,
    }


class VerifyConnectionForm(BaseModel):
    url: str
    key: str


@router.post("/verify")
async def verify_connection(
    request: Request, form_data: VerifyConnectionForm, user=Depends(get_admin_user)
):
    """Verify connection to Gatewayz.ai API"""
    try:
        response = await send_get_request(
            f"{form_data.url}/models", form_data.key, user=user
        )
        if response:
            return {"status": "success", "data": response}
        else:
            raise HTTPException(
                status_code=500, detail="Failed to connect to Gatewayz.ai API"
            )
    except Exception as e:
        log.error(f"Error verifying connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_GATEWAYZ_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.GATEWAYZ_API_BASE_URLS)
    num_keys = len(request.app.state.config.GATEWAYZ_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.GATEWAYZ_API_KEYS[:num_urls]
            request.app.state.config.GATEWAYZ_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.GATEWAYZ_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.GATEWAYZ_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.GATEWAYZ_API_CONFIGS) and (
            url not in request.app.state.config.GATEWAYZ_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.GATEWAYZ_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.GATEWAYZ_API_CONFIGS.get(
                str(idx),
                request.app.state.config.GATEWAYZ_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.GATEWAYZ_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "gatewayz",
                                "gatewayz": {"id": model_id},
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

    for idx, response in enumerate(responses):
        if response:
            url = request.app.state.config.GATEWAYZ_API_BASE_URLS[idx]
            api_config = request.app.state.config.GATEWAYZ_API_CONFIGS.get(
                str(idx),
                request.app.state.config.GATEWAYZ_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            connection_type = api_config.get("connection_type", "external")
            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            model_list = (
                response if isinstance(response, list) else response.get("data", [])
            )
            if not isinstance(model_list, list):
                # Catch non-list responses
                model_list = []

            for model in model_list:
                # Remove name key if its value is None
                if "name" in model and model["name"] is None:
                    del model["name"]

                if prefix_id:
                    model["id"] = (
                        f"{prefix_id}.{model.get('id', model.get('name', ''))}"
                    )

                if tags:
                    model["tags"] = tags

                if connection_type:
                    model["connection_type"] = connection_type

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user):
    # Filter models based on user access control
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


@cached(
    ttl=MODELS_CACHE_TTL,
    key=lambda _, user: f"gatewayz_all_models_{user.id}" if user else "gatewayz_all_models",
)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_GATEWAYZ_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        elif response and isinstance(response, list):
            return response
        return None

    models = {
        "data": [
            model
            for response in responses
            if response
            for model in (extract_data(response) or [])
        ]
    }

    if BYPASS_MODEL_ACCESS_CONTROL:
        return models
    else:
        filtered_models = await get_filtered_models(models, user)
        return {"data": filtered_models}


@router.get("/models")
@router.get("/v1/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    return await get_all_models(request, user)


@router.api_route("/{path:path}", methods=["POST"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Proxy all other requests to Gatewayz.ai API
    """
    body = await request.body()

    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError:
        payload = {}

    model_id = payload.get("model")
    if not model_id:
        raise HTTPException(status_code=400, detail="Model ID is required")

    # Get the model info to find the correct URL
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        # Apply model-specific parameters
        payload = apply_model_params_to_body_openai(
            payload, model_info.params if model_info else {}
        )
        payload = apply_system_prompt_to_body(payload, model_info)

    # Find the URL index for this model
    idx = 0
    for i, url in enumerate(request.app.state.config.GATEWAYZ_API_BASE_URLS):
        api_config = request.app.state.config.GATEWAYZ_API_CONFIGS.get(
            str(i),
            request.app.state.config.GATEWAYZ_API_CONFIGS.get(url, {}),
        )
        prefix_id = api_config.get("prefix_id", None)
        if prefix_id and model_id.startswith(f"{prefix_id}."):
            idx = i
            break

    url = request.app.state.config.GATEWAYZ_API_BASE_URLS[idx]
    key = request.app.state.config.GATEWAYZ_API_KEYS[idx]
    api_config = request.app.state.config.GATEWAYZ_API_CONFIGS.get(
        str(idx),
        request.app.state.config.GATEWAYZ_API_CONFIGS.get(url, {}),
    )

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, payload.get("metadata", {}), user=user
    )

    # Forward the request
    target_url = f"{url}/{path}"

    try:
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(
                target_url,
                headers=headers,
                cookies=cookies,
                json=payload,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Gatewayz.ai API error: {error_text}",
                    )

                # Check if streaming response
                if payload.get("stream", False):

                    async def stream_generator():
                        async for chunk in response.content.iter_any():
                            yield chunk

                    return StreamingResponse(
                        stream_generator(),
                        media_type="text/event-stream",
                        headers=dict(response.headers),
                    )
                else:
                    result = await response.json()
                    return JSONResponse(content=result)

    except aiohttp.ClientError as e:
        log.error(f"Error proxying request to Gatewayz.ai: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error connecting to Gatewayz.ai: {str(e)}"
        )
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

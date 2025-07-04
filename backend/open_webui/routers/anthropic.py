import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, Optional, overload

import aiohttp
from aiocache import cached
import requests


from fastapi import Depends, FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
)
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENV, SRC_LOG_LEVELS


from open_webui.utils.payload import (
    apply_model_params_to_body_openai,  # TODO: Create apply_model_params_to_body_anthropic
    apply_model_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["ANTHROPIC"])


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
                    "X-API-Key": f"{key}", # Anthropic uses X-API-Key
                    "anthropic-version": "2023-06-01", # Required Anthropic version
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
        # Handle connection error here
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


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
        "ANTHROPIC_API_BASE_URLS": request.app.state.config.ANTHROPIC_API_BASE_URLS,
        "ANTHROPIC_API_KEYS": request.app.state.config.ANTHROPIC_API_KEYS,
        "ANTHROPIC_API_CONFIGS": request.app.state.config.ANTHROPIC_API_CONFIGS,
    }


class AnthropicConfigForm(BaseModel):
    ENABLE_ANTHROPIC_API: Optional[bool] = None
    ANTHROPIC_API_BASE_URLS: list[str]
    ANTHROPIC_API_KEYS: list[str]
    ANTHROPIC_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: AnthropicConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_ANTHROPIC_API = form_data.ENABLE_ANTHROPIC_API
    request.app.state.config.ANTHROPIC_API_BASE_URLS = form_data.ANTHROPIC_API_BASE_URLS
    request.app.state.config.ANTHROPIC_API_KEYS = form_data.ANTHROPIC_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.ANTHROPIC_API_KEYS) != len(
        request.app.state.config.ANTHROPIC_API_BASE_URLS
    ):
        if len(request.app.state.config.ANTHROPIC_API_KEYS) > len(
            request.app.state.config.ANTHROPIC_API_BASE_URLS
        ):
            request.app.state.config.ANTHROPIC_API_KEYS = (
                request.app.state.config.ANTHROPIC_API_KEYS[
                    : len(request.app.state.config.ANTHROPIC_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.ANTHROPIC_API_KEYS += [""] * (
                len(request.app.state.config.ANTHROPIC_API_BASE_URLS)
                - len(request.app.state.config.ANTHROPIC_API_KEYS)
            )

    request.app.state.config.ANTHROPIC_API_CONFIGS = form_data.ANTHROPIC_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.ANTHROPIC_API_BASE_URLS))))
    request.app.state.config.ANTHROPIC_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.ANTHROPIC_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
        "ANTHROPIC_API_BASE_URLS": request.app.state.config.ANTHROPIC_API_BASE_URLS,
        "ANTHROPIC_API_KEYS": request.app.state.config.ANTHROPIC_API_KEYS,
        "ANTHROPIC_API_CONFIGS": request.app.state.config.ANTHROPIC_API_CONFIGS,
    }


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.ANTHROPIC_API_BASE_URLS)
    num_keys = len(request.app.state.config.ANTHROPIC_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.ANTHROPIC_API_KEYS[:num_urls]
            request.app.state.config.ANTHROPIC_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.ANTHROPIC_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.ANTHROPIC_API_BASE_URLS):
        # Anthropic doesn't have a dedicated /models endpoint.
        # We will assume some common models or allow users to specify them in ANTHROPIC_API_CONFIGS
        api_config = request.app.state.config.ANTHROPIC_API_CONFIGS.get(
            str(idx),
            request.app.state.config.ANTHROPIC_API_CONFIGS.get(
                url, {}
            ),  # Legacy support
        )

        enable = api_config.get("enable", True)
        model_ids = api_config.get("model_ids", ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-2.1", "claude-2.0", "claude-instant-1.2"]) # Default common Anthropic models

        if enable:
            model_list = {
                "object": "list",
                "data": [
                    {
                        "id": model_id,
                        "name": model_id,
                        "owned_by": "anthropic", # Or appropriate owner
                        "anthropic": {"id": model_id},
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
            url = request.app.state.config.ANTHROPIC_API_BASE_URLS[idx]
            api_config = request.app.state.config.ANTHROPIC_API_CONFIGS.get(
                str(idx),
                request.app.state.config.ANTHROPIC_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            connection_type = api_config.get("connection_type", "external")
            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            for model in (
                response if isinstance(response, list) else response.get("data", [])
            ):
                if prefix_id:
                    model["id"] = f"{prefix_id}.{model['id']}"

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


@cached(ttl=1)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def merge_models_lists(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        merged_list = []

        for idx, models in enumerate(model_lists):
            if models is not None and "error" not in models:

                merged_list.extend(
                    [
                        {
                            **model,
                            "name": model.get("name", model["id"]),
                            "owned_by": "anthropic",
                            "anthropic": model, # Store original model info if needed
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }
                        for model in models
                        if (model.get("id") or model.get("name"))
                    ]
                )
        return merged_list

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    request.app.state.ANTHROPIC_MODELS = {model["id"]: model for model in models["data"]}
    return models


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        # For a specific URL index, return the configured models for that index
        url = request.app.state.config.ANTHROPIC_API_BASE_URLS[url_idx]
        api_config = request.app.state.config.ANTHROPIC_API_CONFIGS.get(
            str(url_idx),
            request.app.state.config.ANTHROPIC_API_CONFIGS.get(url, {}),  # Legacy support
        )
        model_ids = api_config.get("model_ids", ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-2.1", "claude-2.0", "claude-instant-1.2"])
        models_data = [
            {
                "id": model_id,
                "name": model_id,
                "owned_by": "anthropic",
                "anthropic": {"id": model_id},
                "urlIdx": url_idx,
            }
            for model_id in model_ids
        ]
        models = {"data": models_data, "object": "list"}


    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str
    config: Optional[dict] = None


@router.post("/verify")
async def verify_connection(
    form_data: ConnectionVerificationForm, user=Depends(get_admin_user)
):
    url = form_data.url
    key = form_data.key
    # api_config = form_data.config or {} # Not directly used for Anthropic verification like Azure

    # Anthropic verification can be done by trying to list models (which we simulate)
    # or making a simple request like a small completion.
    # For now, we'll assume if the config is set, it's verified,
    # as there isn't a standard "list models" or "version" endpoint for all Anthropic providers.
    # A more robust verification would involve making a test API call.
    # This is a placeholder, actual verification might need a test call to /v1/messages with a dummy prompt.
    log.info(f"Verifying Anthropic connection to {url}")
    # Simulate a successful response if URL and key are present
    if url and key:
        # In a real scenario, you might try a lightweight API call here
        # For now, let's assume it's okay if the details are provided.
        # This is a simplified verification.
        # A true verification would be to send a test message.
        # e.g. try to send a message to "claude-instant-1.2"
        try:
            async with aiohttp.ClientSession(
                trust_env=True,
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
            ) as session:
                async with session.post(
                    f"{url}/v1/messages", # Common Anthropic endpoint
                    headers={
                        "X-API-Key": f"{key}",
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-instant-1.2", # A common, smaller model for testing
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hello"}],
                    },
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status != 200:
                        error_detail = f"HTTP Error: {r.status}"
                        try:
                            res_text = await r.text()
                            res = json.loads(res_text)
                            if "error" in res:
                                error_detail = f"External Error: {res['error'].get('message', res['error'].get('type', 'Unknown error'))}"
                        except Exception as parse_exc:
                            log.error(f"Failed to parse error response: {parse_exc}, original text: {res_text}")
                            error_detail = f"HTTP Error: {r.status} - Could not parse error response."
                        raise Exception(error_detail)
                    # If the call is successful, return a success-like message or model list
                    return {"status": "success", "message": "Connection to Anthropic API verified."}
        except aiohttp.ClientError as e:
            log.exception(f"Client error during Anthropic verification: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error (Anthropic)"
            )
        except Exception as e:
            log.exception(f"Unexpected error during Anthropic verification: {e}")
            error_detail = f"Unexpected error: {str(e)}"
            raise HTTPException(status_code=500, detail=error_detail)
    else:
        raise HTTPException(status_code=400, detail="URL and API Key are required for Anthropic.")


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0
    payload = {**form_data}
    metadata = payload.pop("metadata", None)
    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id
        params = model_info.params.model_dump()
        if params:
            system = params.pop("system", None)
            # TODO: Create apply_model_params_to_body_anthropic
            # payload = apply_model_params_to_body_anthropic(params, payload)
            payload = apply_model_params_to_body_openai(params, payload) # Placeholder
            payload = apply_model_system_prompt_to_body(system, payload, metadata, user)

        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(status_code=403,detail="Model not found",)
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(status_code=403,detail="Model not found",)

    await get_all_models(request, user=user) # Ensure ANTHROPIC_MODELS is populated
    model_details = request.app.state.ANTHROPIC_MODELS.get(model_id)

    if model_details:
        idx = model_details["urlIdx"]
    else:
        raise HTTPException(status_code=404,detail="Model not found in ANTHROPIC_MODELS",)

    api_config = request.app.state.config.ANTHROPIC_API_CONFIGS.get(
        str(idx),
        request.app.state.config.ANTHROPIC_API_CONFIGS.get(
            request.app.state.config.ANTHROPIC_API_BASE_URLS[idx], {}
        ),
    )

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")


    # Anthropic-specific payload adjustments
    # Standard Anthropic messages endpoint uses "model", "messages", "max_tokens"
    # System prompt is passed as a top-level "system" parameter
    anthropic_payload = {
        "model": payload.get("model"),
        "messages": payload.get("messages"),
        "max_tokens": payload.get("max_tokens", 1024), # Default max_tokens for Anthropic
    }
    if "temperature" in payload:
        anthropic_payload["temperature"] = payload["temperature"]
    if "top_p" in payload:
        anthropic_payload["top_p"] = payload["top_p"]
    if "top_k" in payload:
        anthropic_payload["top_k"] = payload["top_k"]
    if "stream" in payload:
        anthropic_payload["stream"] = payload["stream"]

    # Handle system message
    if payload.get("messages") and payload["messages"][0]["role"] == "system":
        system_message = payload["messages"].pop(0)
        anthropic_payload["system"] = system_message["content"]
    elif "system" in payload: # If system prompt was already extracted by apply_model_system_prompt_to_body
        anthropic_payload["system"] = payload["system"]


    url = request.app.state.config.ANTHROPIC_API_BASE_URLS[idx]
    key = request.app.state.config.ANTHROPIC_API_KEYS[idx]

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": f"{key}",
        "anthropic-version": "2023-06-01", # Or a newer version if appropriate
         **(
            {
                "X-OpenWebUI-User-Name": user.name,
                "X-OpenWebUI-User-Id": user.id,
                "X-OpenWebUI-User-Email": user.email,
                "X-OpenWebUI-User-Role": user.role,
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS
            else {}
        ),
    }

    request_url = f"{url}/v1/messages" # Standard Anthropic messages endpoint

    # Remove None values from anthropic_payload before sending
    anthropic_payload_cleaned = {k: v for k, v in anthropic_payload.items() if v is not None}
    payload_json = json.dumps(anthropic_payload_cleaned)


    r = None
    session = None
    streaming = anthropic_payload_cleaned.get("stream", False)
    response_content = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )
        r = await session.request(
            method="POST",
            url=request_url,
            data=payload_json,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        if streaming:
            return StreamingResponse(
                r.content, # Stream content directly
                status_code=r.status,
                headers=dict(r.headers), # Pass through relevant headers
                media_type="text/event-stream" if streaming else "application/json",
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            response_content = await r.json()
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response_content

    except Exception as e:
        log.exception(e)
        detail = None
        if response_content and isinstance(response_content, dict) and "error" in response_content:
            err_obj = response_content['error']
            detail = f"Anthropic Error: {err_obj.get('type', '')} - {err_obj.get('message', str(e))}"
        elif r is not None:
             detail = f"Anthropic API request failed with status {r.status}: {await r.text()}"
        else:
            detail = f"Open WebUI: Server Connection Error to Anthropic: {e}"

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail,
        )
    finally:
        if not streaming and session: # If not streaming, session is closed here
            if r:
                r.close()
            await session.close()

# Placeholder for other endpoints like /embeddings if Anthropic offers them in a compatible way.
# For now, focusing on /chat/completions (i.e., /v1/messages)

# Remove or adapt generic proxy if not applicable to Anthropic's typical API structure
# Anthropic usually has specific endpoints like /v1/messages rather than a generic pass-through.
# If a generic proxy is needed for some custom Anthropic-compatible server, it can be adapted.
# For now, it's commented out as it's less likely to be used in the same way as with OpenAI.
"""
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    # This would need significant adaptation for Anthropic
    pass
"""

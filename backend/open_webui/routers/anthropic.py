"""
Anthropic native provider router.

Provides:
- Admin config endpoints (GET/POST /anthropic/config)
- Model discovery (GET /anthropic/models)
- Chat completion (POST /anthropic/chat/completions)

Uses the Anthropic Python SDK for direct API communication,
converting all responses to OpenAI-compatible format for the frontend.
"""

import asyncio
import json
import logging
from typing import Optional

import anthropic
from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from open_webui.models.models import Models
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.anthropic_payload import (
    convert_payload_openai_to_anthropic,
    apply_model_params_to_body_anthropic,
)
from open_webui.utils.anthropic_response import (
    convert_streaming_response_anthropic_to_openai,
    convert_response_anthropic_to_openai,
)
from open_webui.utils.payload import apply_system_prompt_to_body
from open_webui.utils.auth import get_admin_user, get_verified_user

from open_webui.env import (
    BYPASS_MODEL_ACCESS_CONTROL,
)

log = logging.getLogger(__name__)


router = APIRouter()


# Known Anthropic models — used as fallback when the API models endpoint
# is unavailable or the SDK version doesn't support client.models.list()
ANTHROPIC_KNOWN_MODELS = [
    {
        "id": "claude-opus-4-20250514",
        "name": "Claude Opus 4",
        "context_window": 200000,
        "max_output": 32000,
    },
    {
        "id": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "context_window": 200000,
        "max_output": 64000,
    },
    {
        "id": "claude-sonnet-4-5-20250514",
        "name": "Claude Sonnet 4.5",
        "context_window": 200000,
        "max_output": 64000,
    },
    {
        "id": "claude-haiku-3-5-20241022",
        "name": "Claude 3.5 Haiku",
        "context_window": 200000,
        "max_output": 8192,
    },
]


##########################################
#
# Config endpoints
#
##########################################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
        "ANTHROPIC_API_KEYS": request.app.state.config.ANTHROPIC_API_KEYS,
        "ANTHROPIC_API_BASE_URLS": request.app.state.config.ANTHROPIC_API_BASE_URLS,
        "ANTHROPIC_API_CONFIGS": request.app.state.config.ANTHROPIC_API_CONFIGS,
    }


class AnthropicConfigForm(BaseModel):
    ENABLE_ANTHROPIC_API: Optional[bool] = None
    ANTHROPIC_API_KEYS: list[str]
    ANTHROPIC_API_BASE_URLS: list[str]
    ANTHROPIC_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: AnthropicConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_ANTHROPIC_API = form_data.ENABLE_ANTHROPIC_API
    request.app.state.config.ANTHROPIC_API_KEYS = form_data.ANTHROPIC_API_KEYS
    request.app.state.config.ANTHROPIC_API_BASE_URLS = form_data.ANTHROPIC_API_BASE_URLS

    # Ensure keys and URLs lists are the same length
    num_urls = len(request.app.state.config.ANTHROPIC_API_BASE_URLS)
    num_keys = len(request.app.state.config.ANTHROPIC_API_KEYS)

    if num_keys != num_urls:
        if num_keys > num_urls:
            request.app.state.config.ANTHROPIC_API_KEYS = (
                request.app.state.config.ANTHROPIC_API_KEYS[:num_urls]
            )
        else:
            request.app.state.config.ANTHROPIC_API_KEYS += [""] * (
                num_urls - num_keys
            )

    request.app.state.config.ANTHROPIC_API_CONFIGS = form_data.ANTHROPIC_API_CONFIGS

    # Remove configs not matching a valid URL index
    keys = list(map(str, range(num_urls)))
    request.app.state.config.ANTHROPIC_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.ANTHROPIC_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
        "ANTHROPIC_API_KEYS": request.app.state.config.ANTHROPIC_API_KEYS,
        "ANTHROPIC_API_BASE_URLS": request.app.state.config.ANTHROPIC_API_BASE_URLS,
        "ANTHROPIC_API_CONFIGS": request.app.state.config.ANTHROPIC_API_CONFIGS,
    }


##########################################
#
# Model discovery
#
##########################################


def _build_client(api_key: str, base_url: str) -> anthropic.AsyncAnthropic:
    """Create an Anthropic async client for the given credentials."""
    kwargs = {"api_key": api_key}
    if base_url and base_url != "https://api.anthropic.com":
        kwargs["base_url"] = base_url
    return anthropic.AsyncAnthropic(**kwargs)


async def _fetch_models_for_key(api_key: str, base_url: str, idx: int) -> list[dict]:
    """
    Attempt to list models from the Anthropic API for a single key/URL pair.
    Falls back to the hardcoded known models list on failure.
    """
    if not api_key:
        return []

    try:
        client = _build_client(api_key, base_url)
        # The Anthropic SDK models.list() is available in recent versions
        response = await client.models.list(limit=100)
        models = []
        for model_data in response.data:
            model_id = model_data.id
            model_name = getattr(model_data, "display_name", model_id)
            models.append(
                {
                    "id": model_id,
                    "name": model_name,
                    "object": "model",
                    "owned_by": "anthropic",
                    "anthropic": {"id": model_id},
                    "urlIdx": idx,
                }
            )
        return models
    except Exception as e:
        log.warning(
            f"Could not list Anthropic models for key index {idx} "
            f"(falling back to known models): {e}"
        )
        # Return the known models list as fallback
        return [
            {
                "id": m["id"],
                "name": m["name"],
                "object": "model",
                "owned_by": "anthropic",
                "anthropic": {
                    "id": m["id"],
                    "context_window": m.get("context_window"),
                    "max_output": m.get("max_output"),
                },
                "urlIdx": idx,
            }
            for m in ANTHROPIC_KNOWN_MODELS
        ]


async def get_all_models(request: Request, user: UserModel = None) -> dict:
    """
    Fetch all available Anthropic models across all configured API keys/URLs.
    Returns in the standard {"data": [...]} format.
    """
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        return {"data": []}

    api_keys = list(request.app.state.config.ANTHROPIC_API_KEYS)
    api_base_urls = list(request.app.state.config.ANTHROPIC_API_BASE_URLS)
    api_configs = request.app.state.config.ANTHROPIC_API_CONFIGS

    # Ensure lists are the same length
    num_urls = len(api_base_urls)
    if len(api_keys) < num_urls:
        api_keys += [""] * (num_urls - len(api_keys))

    # Fetch models from each configured endpoint in parallel
    tasks = []
    for idx in range(num_urls):
        config = api_configs.get(str(idx), {})
        if not config.get("enable", True):
            tasks.append(asyncio.ensure_future(asyncio.sleep(0, result=[])))
            continue

        model_ids = config.get("model_ids", [])
        if model_ids:
            # Use explicitly configured model IDs instead of fetching
            prefix_id = config.get("prefix_id", None)
            models = []
            for mid in model_ids:
                display_id = f"{prefix_id}.{mid}" if prefix_id else mid
                models.append(
                    {
                        "id": display_id,
                        "name": display_id,
                        "object": "model",
                        "owned_by": "anthropic",
                        "anthropic": {"id": mid},
                        "urlIdx": idx,
                    }
                )
            tasks.append(asyncio.ensure_future(asyncio.sleep(0, result=models)))
        else:
            tasks.append(_fetch_models_for_key(api_keys[idx], api_base_urls[idx], idx))

    results = await asyncio.gather(*tasks)

    # Apply config-level prefix_id, tags, and connection_type to each model
    # BEFORE dedup so that prefixed IDs don't collide with un-prefixed ones.
    for idx, model_list in enumerate(results):
        if not model_list:
            continue
        config = api_configs.get(str(idx), {})
        prefix_id = config.get("prefix_id", None)
        config_tags = config.get("tags", [])
        connection_type = config.get("connection_type", "external")

        for model in model_list:
            model_id = model.get("id", "")
            if prefix_id and model_id and not model_id.startswith(f"{prefix_id}."):
                model["id"] = f"{prefix_id}.{model_id}"
                model["name"] = model["id"]

            # Use prefix_id as the tag (matching OpenAI behavior), plus any config tags
            model_tags = []
            if prefix_id:
                model_tags.append({"name": prefix_id})
            if config_tags:
                existing_names = {t["name"].lower() for t in model_tags}
                for t in config_tags:
                    if t.get("name", "").lower() not in existing_names:
                        model_tags.append(t)
            if model_tags:
                model["tags"] = model_tags
            model["connection_type"] = connection_type

    # Merge models, deduplicating by final ID (first occurrence wins)
    seen = {}
    for model_list in results:
        if model_list:
            for model in model_list:
                final_id = model.get("id", "")
                if final_id and final_id not in seen:
                    seen[final_id] = model

    request.app.state.ANTHROPIC_MODELS = seen
    return {"data": list(seen.values())}


@router.get("/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        raise HTTPException(status_code=503, detail="Anthropic API is disabled")
    return await get_all_models(request, user=user)


##########################################
#
# Chat completion
#
##########################################


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
    bypass_system_prompt: bool = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Check model info and apply overrides
    if model_info:
        if model_info.base_model_id:
            base_model_id = model_info.base_model_id
            payload["model"] = base_model_id
            model_id = base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop("system", None)
            payload = apply_model_params_to_body_anthropic(params, payload)
            if not bypass_system_prompt:
                payload = apply_system_prompt_to_body(system, payload, metadata, user)

        # Access control
        if not bypass_filter and user.role == "user":
            user_group_ids = {
                group.id for group in Groups.get_groups_by_member_id(user.id)
            }
            if not (
                user.id == model_info.user_id
                or AccessGrants.has_access(
                    user_id=user.id,
                    resource_type="model",
                    resource_id=model_info.id,
                    permission="read",
                    user_group_ids=user_group_ids,
                )
            ):
                raise HTTPException(status_code=403, detail="Model not found")
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    # Resolve model to find the correct API key index
    models = request.app.state.ANTHROPIC_MODELS
    if not models or model_id not in models:
        await get_all_models(request, user=user)
        models = request.app.state.ANTHROPIC_MODELS
    model = models.get(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    idx = model.get("urlIdx", 0)

    # Get credentials
    api_keys = list(request.app.state.config.ANTHROPIC_API_KEYS)
    api_base_urls = list(request.app.state.config.ANTHROPIC_API_BASE_URLS)
    api_configs = request.app.state.config.ANTHROPIC_API_CONFIGS

    if idx >= len(api_keys) or idx >= len(api_base_urls):
        raise HTTPException(status_code=500, detail="Invalid API configuration index")

    api_key = api_keys[idx]
    base_url = api_base_urls[idx]
    config = api_configs.get(str(idx), {})

    if not api_key:
        raise HTTPException(status_code=401, detail="Anthropic API key not configured")

    # Strip prefix_id from model name if present
    prefix_id = config.get("prefix_id", None)
    actual_model_id = payload.get("model", model_id)
    if prefix_id and actual_model_id.startswith(f"{prefix_id}."):
        actual_model_id = actual_model_id[len(f"{prefix_id}."):]
    payload["model"] = actual_model_id

    # Convert payload from OpenAI format to Anthropic format
    is_stream = payload.get("stream", False)
    anthropic_payload = convert_payload_openai_to_anthropic(payload)

    # Remove internal metadata before sending to Anthropic
    anthropic_payload.pop("metadata", None)

    # Create SDK client
    client = _build_client(api_key, base_url)

    try:
        if is_stream:
            # Streaming — use raw SSE events
            stream = await client.messages.create(**anthropic_payload)

            return StreamingResponse(
                convert_streaming_response_anthropic_to_openai(stream),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming
            anthropic_payload.pop("stream", None)
            response = await client.messages.create(**anthropic_payload)
            return convert_response_anthropic_to_openai(response)

    except anthropic.AuthenticationError as e:
        log.error(f"Anthropic authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Anthropic API authentication failed: {e.message}",
        )
    except anthropic.PermissionDeniedError as e:
        log.error(f"Anthropic permission denied: {e}")
        raise HTTPException(
            status_code=403,
            detail=f"Anthropic API permission denied: {e.message}",
        )
    except anthropic.NotFoundError as e:
        log.error(f"Anthropic not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Anthropic API resource not found: {e.message}",
        )
    except anthropic.RateLimitError as e:
        log.error(f"Anthropic rate limit: {e}")
        raise HTTPException(
            status_code=429,
            detail=f"Anthropic API rate limit exceeded: {e.message}",
        )
    except anthropic.APIStatusError as e:
        log.error(f"Anthropic API error (status {e.status_code}): {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Anthropic API error: {e.message}",
        )
    except anthropic.APIConnectionError as e:
        log.error(f"Anthropic connection error: {e}")
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Anthropic API",
        )
    except anthropic.APITimeoutError as e:
        log.error(f"Anthropic timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Anthropic API request timed out",
        )
    except Exception as e:
        log.exception(f"Unexpected error calling Anthropic API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Open WebUI: Anthropic provider error: {str(e)}",
        )

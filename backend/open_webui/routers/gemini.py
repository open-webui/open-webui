"""
Gemini API Router

This module provides native Google Gemini API integration for Open WebUI.
It uses the google-genai SDK for direct API access, supporting multimodal features.
"""

import asyncio
import json
import logging
from typing import Optional

import aiohttp
from aiocache import cached

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from open_webui.models.models import Models
from open_webui.models.users import UserModel

from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    BYPASS_MODEL_ACCESS_CONTROL,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url: str, key: str = None, config: dict = None) -> dict:
    """Send a GET request to the Gemini API.
    
    Supports both Bearer token authentication (via Authorization header)
    and API key authentication (via query parameter).
    """
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {"Content-Type": "application/json"}
            
            # Determine authentication method based on config
            auth_type = (config or {}).get("auth_type", "bearer")
            
            if auth_type == "bearer" and key:
                # Use Authorization header for Bearer auth (proxy compatible)
                headers["Authorization"] = f"Bearer {key}"
                full_url = url
            elif auth_type == "none":
                # No authentication
                full_url = url
            else:
                # Default: Gemini uses API key as query parameter
                full_url = f"{url}?key={key}" if key else url
            
            async with session.get(full_url, headers=headers) as response:
                return await response.json()
    except Exception as e:
        log.error(f"Connection error: {e}")
        return None


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    """Get Gemini API configuration."""
    return {
        "ENABLE_GEMINI_API": request.app.state.config.ENABLE_GEMINI_API,
        "GEMINI_API_BASE_URLS": request.app.state.config.GEMINI_API_BASE_URLS,
        "GEMINI_API_KEYS": request.app.state.config.GEMINI_API_KEYS,
        "GEMINI_API_CONFIGS": request.app.state.config.GEMINI_API_CONFIGS,
    }


class GeminiConfigForm(BaseModel):
    ENABLE_GEMINI_API: Optional[bool] = None
    GEMINI_API_BASE_URLS: list[str]
    GEMINI_API_KEYS: list[str]
    GEMINI_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: GeminiConfigForm, user=Depends(get_admin_user)
):
    """Update Gemini API configuration."""
    request.app.state.config.ENABLE_GEMINI_API = form_data.ENABLE_GEMINI_API
    request.app.state.config.GEMINI_API_BASE_URLS = form_data.GEMINI_API_BASE_URLS
    request.app.state.config.GEMINI_API_KEYS = form_data.GEMINI_API_KEYS

    # Check if API KEYS length is same as API URLS length
    if len(request.app.state.config.GEMINI_API_KEYS) != len(
        request.app.state.config.GEMINI_API_BASE_URLS
    ):
        if len(request.app.state.config.GEMINI_API_KEYS) > len(
            request.app.state.config.GEMINI_API_BASE_URLS
        ):
            request.app.state.config.GEMINI_API_KEYS = (
                request.app.state.config.GEMINI_API_KEYS[
                    : len(request.app.state.config.GEMINI_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.GEMINI_API_KEYS += [""] * (
                len(request.app.state.config.GEMINI_API_BASE_URLS)
                - len(request.app.state.config.GEMINI_API_KEYS)
            )

    request.app.state.config.GEMINI_API_CONFIGS = form_data.GEMINI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.GEMINI_API_BASE_URLS))))
    request.app.state.config.GEMINI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.GEMINI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_GEMINI_API": request.app.state.config.ENABLE_GEMINI_API,
        "GEMINI_API_BASE_URLS": request.app.state.config.GEMINI_API_BASE_URLS,
        "GEMINI_API_KEYS": request.app.state.config.GEMINI_API_KEYS,
        "GEMINI_API_CONFIGS": request.app.state.config.GEMINI_API_CONFIGS,
    }


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    """Get all Gemini models from configured endpoints."""
    if not request.app.state.config.ENABLE_GEMINI_API:
        return []

    # Check if API KEYS length is same as API URLS length
    num_urls = len(request.app.state.config.GEMINI_API_BASE_URLS)
    num_keys = len(request.app.state.config.GEMINI_API_KEYS)

    if num_keys != num_urls:
        if num_keys > num_urls:
            request.app.state.config.GEMINI_API_KEYS = (
                request.app.state.config.GEMINI_API_KEYS[:num_urls]
            )
        else:
            request.app.state.config.GEMINI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.GEMINI_API_BASE_URLS):
        api_config = request.app.state.config.GEMINI_API_CONFIGS.get(str(idx), {})
        enable = api_config.get("enable", True)
        model_ids = api_config.get("model_ids", [])

        if enable:
            if len(model_ids) == 0:
                # Fetch models from Gemini API
                request_tasks.append(
                    send_get_request(
                        f"{url}/models",
                        request.app.state.config.GEMINI_API_KEYS[idx],
                        api_config,  # Pass config for auth_type handling
                    )
                )
            else:
                # Use predefined model IDs
                model_list = {
                    "models": [
                        {
                            "name": f"models/{model_id}",
                            "displayName": model_id,
                            "supportedGenerationMethods": ["generateContent"],
                        }
                        for model_id in model_ids
                    ]
                }
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, model_list)))
        else:
            request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            api_config = request.app.state.config.GEMINI_API_CONFIGS.get(str(idx), {})
            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            model_list = response.get("models", [])
            for model in model_list:
                # Add metadata
                model["urlIdx"] = idx
                if prefix_id:
                    model_name = model.get("name", "").replace("models/", "")
                    model["id"] = f"{prefix_id}.{model_name}"
                else:
                    model["id"] = model.get("name", "").replace("models/", "")
                if tags:
                    model["tags"] = tags

    return responses


async def get_filtered_models(models, user):
    """Filter models based on user access control."""
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


async def get_all_models(request: Request, user: UserModel) -> dict:
    """Get all available Gemini models."""
    log.info("get_all_models() - Gemini")

    if not request.app.state.config.ENABLE_GEMINI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    models = {}
    for idx, response in enumerate(responses):
        if response and "models" in response:
            for model in response["models"]:
                model_id = model.get("id", model.get("name", "").replace("models/", ""))
                
                # Only include models that support generateContent
                supported_methods = model.get("supportedGenerationMethods", [])
                if "generateContent" not in supported_methods:
                    continue

                if model_id and model_id not in models:
                    models[model_id] = {
                        "id": model_id,
                        "name": model.get("displayName", model_id),
                        "owned_by": "google",
                        "gemini": model,
                        "urlIdx": idx,
                    }

    request.app.state.GEMINI_MODELS = models
    return {"data": list(models.values())}


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    """Get Gemini models."""
    models = {"data": []}

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.GEMINI_API_BASE_URLS[url_idx]
        key = request.app.state.config.GEMINI_API_KEYS[url_idx]

        response = await send_get_request(f"{url}/models", key)
        if response and "models" in response:
            models = {
                "data": [
                    {
                        "id": m.get("name", "").replace("models/", ""),
                        "name": m.get("displayName", ""),
                        "owned_by": "google",
                    }
                    for m in response["models"]
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
            }

    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


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
    """Verify Gemini API connection."""
    url = form_data.url
    key = form_data.key
    config = form_data.config or {}

    try:
        response = await send_get_request(f"{url}/models", key, config)
        if response is None:
            raise HTTPException(
                status_code=500, detail="Failed to connect to Gemini API"
            )
        if "error" in response:
            raise HTTPException(
                status_code=response.get("error", {}).get("code", 500),
                detail=response.get("error", {}).get("message", "Unknown error"),
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500, detail="Open WebUI: Server Connection Error"
        )


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    """
    Generate chat completion using Gemini API.
    
    This endpoint accepts OpenAI-compatible format and converts it to Gemini format.
    """
    model_id = form_data.get("model", "")
    stream = form_data.get("stream", False)
    
    # Find the model's URL index
    idx = None
    model_info = request.app.state.GEMINI_MODELS.get(model_id)
    if model_info:
        idx = model_info.get("urlIdx", 0)
    else:
        # Try to find by prefix
        for key, info in request.app.state.GEMINI_MODELS.items():
            if model_id.endswith(key) or key.endswith(model_id):
                idx = info.get("urlIdx", 0)
                break
    
    if idx is None:
        idx = 0
    
    url = request.app.state.config.GEMINI_API_BASE_URLS[idx]
    key = request.app.state.config.GEMINI_API_KEYS[idx]
    api_config = request.app.state.config.GEMINI_API_CONFIGS.get(str(idx), {})
    
    # Convert OpenAI format to Gemini format
    messages = form_data.get("messages", [])
    
    # Build Gemini contents
    contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            system_instruction = content
            continue
        
        gemini_role = "user" if role == "user" else "model"
        
        # Handle multimodal content
        if isinstance(content, list):
            parts = []
            for item in content:
                if item.get("type") == "text":
                    parts.append({"text": item.get("text", "")})
                elif item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:"):
                        # Base64 image
                        import base64
                        header, data = image_url.split(",", 1)
                        mime_type = header.split(":")[1].split(";")[0]
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": data
                            }
                        })
                    else:
                        # URL image (Gemini doesn't support URL directly, would need to download)
                        parts.append({"text": f"[Image: {image_url}]"})
            contents.append({"role": gemini_role, "parts": parts})
        else:
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    
    # Clean model ID for Gemini API
    gemini_model = model_id
    for prefix_check in request.app.state.config.GEMINI_API_CONFIGS.values():
        prefix = prefix_check.get("prefix_id", "")
        if prefix and model_id.startswith(f"{prefix}."):
            gemini_model = model_id[len(prefix) + 1:]
            break
    
    # Build Gemini request
    gemini_payload = {
        "contents": contents,
        "generationConfig": {}
    }
    
    if system_instruction:
        gemini_payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    
    # Map OpenAI parameters to Gemini
    if "temperature" in form_data:
        gemini_payload["generationConfig"]["temperature"] = form_data["temperature"]
    if "max_tokens" in form_data:
        gemini_payload["generationConfig"]["maxOutputTokens"] = form_data["max_tokens"]
    if "top_p" in form_data:
        gemini_payload["generationConfig"]["topP"] = form_data["top_p"]
    if "stop" in form_data:
        gemini_payload["generationConfig"]["stopSequences"] = form_data["stop"] if isinstance(form_data["stop"], list) else [form_data["stop"]]
    
    # Make request to Gemini API
    endpoint = "streamGenerateContent" if stream else "generateContent"
    
    # Determine authentication method based on config
    auth_type = api_config.get("auth_type", "bearer")
    headers = {"Content-Type": "application/json"}
    
    if auth_type == "bearer" and key:
        # Use Authorization header for Bearer auth (proxy compatible)
        headers["Authorization"] = f"Bearer {key}"
        gemini_url = f"{url}/models/{gemini_model}:{endpoint}"
    elif auth_type == "none":
        # No authentication
        gemini_url = f"{url}/models/{gemini_model}:{endpoint}"
    else:
        # Default: Gemini uses API key as query parameter
        gemini_url = f"{url}/models/{gemini_model}:{endpoint}?key={key}"
    
    if stream:
        gemini_url += ("&" if "?" in gemini_url else "?") + "alt=sse"
    
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(
                gemini_url,
                json=gemini_payload,
                headers=headers,
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    raise HTTPException(
                        status_code=response.status,
                        detail=error_data.get("error", {}).get("message", "Gemini API Error")
                    )
                
                if stream:
                    async def stream_generator():
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                try:
                                    gemini_response = json.loads(data)
                                    # Convert Gemini response to OpenAI format
                                    openai_chunk = convert_gemini_to_openai_stream(gemini_response, model_id)
                                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                                except json.JSONDecodeError:
                                    continue
                    
                    return StreamingResponse(
                        stream_generator(),
                        media_type="text/event-stream"
                    )
                else:
                    gemini_response = await response.json()
                    openai_response = convert_gemini_to_openai(gemini_response, model_id)
                    return JSONResponse(content=openai_response)
                    
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error calling Gemini API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def convert_gemini_to_openai(gemini_response: dict, model_id: str) -> dict:
    """Convert Gemini response to OpenAI format."""
    candidates = gemini_response.get("candidates", [])
    
    choices = []
    for i, candidate in enumerate(candidates):
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        
        choices.append({
            "index": i,
            "message": {
                "role": "assistant",
                "content": text
            },
            "finish_reason": candidate.get("finishReason", "stop").lower()
        })
    
    usage = gemini_response.get("usageMetadata", {})
    
    return {
        "id": f"chatcmpl-gemini-{model_id}",
        "object": "chat.completion",
        "model": model_id,
        "choices": choices,
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0)
        }
    }


def convert_gemini_to_openai_stream(gemini_chunk: dict, model_id: str) -> dict:
    """Convert Gemini streaming chunk to OpenAI format."""
    candidates = gemini_chunk.get("candidates", [])
    
    choices = []
    for i, candidate in enumerate(candidates):
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        
        delta = {"content": text} if text else {}
        if candidate.get("finishReason"):
            delta = {}
        
        choices.append({
            "index": i,
            "delta": delta,
            "finish_reason": candidate.get("finishReason", None)
        })
    
    return {
        "id": f"chatcmpl-gemini-{model_id}",
        "object": "chat.completion.chunk",
        "model": model_id,
        "choices": choices
    }

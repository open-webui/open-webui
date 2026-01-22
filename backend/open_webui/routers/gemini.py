"""
Gemini API Router

This module provides native Google Gemini API integration for Open WebUI.
It uses the REST v1beta endpoints (generateContent / streamGenerateContent with alt=sse)
and converts responses into OpenAI-compatible format for the Open WebUI frontend.
"""

import asyncio
import copy
import codecs
import json
import logging
import time
import uuid
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
                # Gemini standard expects ?key=
                full_url = f"{url}?key={key}"
            elif auth_type == "none":
                full_url = url
            else:
                full_url = f"{url}?key={key}" if key else url

            log.info(f"send_get_request full_url: {full_url}")
            async with session.get(full_url, headers=headers) as response:
                try:
                    return await response.json(content_type=None)
                except Exception:
                    text_content = await response.text()
                    log.error(
                        f"Failed to parse JSON response (status {response.status}): {text_content[:500]}"
                    )
                    return {
                        "error": {
                            "message": f"Invalid response from Gemini API: {text_content[:200]}"
                        }
                    }
    except Exception as e:
        log.error(f"Connection error: {e}")
        return None


def _map_finish_reason(fr: Optional[str]) -> Optional[str]:
    """Map Gemini finishReason to OpenAI finish_reason."""
    if not fr:
        return None
    fr_u = str(fr).upper()
    if fr_u == "STOP":
        return "stop"
    if fr_u == "MAX_TOKENS":
        return "length"
    if fr_u in ("SAFETY", "RECITATION"):
        return "content_filter"
    # Fallback: treat as stop
    return "stop"


def _parse_gemini_error_message(error_text: str) -> str:
    if not error_text:
        return "Gemini API Error"
    try:
        err_json = json.loads(error_text)
    except Exception:
        return error_text[:500]
    if isinstance(err_json, dict):
        err = err_json.get("error")
        if isinstance(err, dict):
            message = err.get("message")
            if message:
                return message
    return error_text[:500]


def _build_compat_payload(
    gemini_payload: dict,
    *,
    drop_tools: bool = False,
    drop_thinking: bool = False,
    drop_response_modalities: bool = False,
) -> dict:
    compat_payload = copy.deepcopy(gemini_payload)
    if drop_tools:
        compat_payload.pop("tools", None)
    generation_config = compat_payload.get("generationConfig")
    if isinstance(generation_config, dict):
        if drop_thinking:
            generation_config.pop("thinkingConfig", None)
        if drop_response_modalities:
            generation_config.pop("responseModalities", None)
        if not generation_config:
            compat_payload.pop("generationConfig", None)
    return compat_payload


def _openai_chunk(
    stream_id: str,
    model_id: str,
    delta: dict,
    finish_reason: Optional[str] = None,
    index: int = 0,
    usage: Optional[dict] = None,
) -> dict:
    chunk = {
        "id": stream_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": index,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    if usage:
        chunk["usage"] = usage
    return chunk


# Maximum chunk size for streaming content (32KB to be safe with various proxies/browsers)
MAX_STREAM_CHUNK_SIZE = 32 * 1024


def _yield_content_chunks(content: str, stream_id: str, model_id: str):
    """
    Generator that yields content in chunks to avoid "Chunk too big" errors.
    Large content (especially base64 images) is split into smaller SSE events.
    """
    if len(content) <= MAX_STREAM_CHUNK_SIZE:
        # Small content, yield as single chunk
        chunk = _openai_chunk(stream_id, model_id, {"content": content}, None, 0)
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    else:
        # Large content, split into multiple chunks
        log.info(f"[GEMINI STREAM] Splitting large content ({len(content)} bytes) into chunks")
        offset = 0
        while offset < len(content):
            chunk_content = content[offset:offset + MAX_STREAM_CHUNK_SIZE]
            chunk = _openai_chunk(stream_id, model_id, {"content": chunk_content}, None, 0)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            offset += MAX_STREAM_CHUNK_SIZE


def _wants_web_search(fd: dict) -> bool:
    if fd.get("web_search") is True:
        return True
    if fd.get("native_web_search") is True:
        return True
    tools = fd.get("tools") or []
    for t in tools:
        if isinstance(t, dict) and t.get("type") in ("web_search", "web_search_preview", "browser_search"):
            return True
    return False


def _clean_schema_for_gemini(schema: dict) -> dict:
    """
    Clean OpenAPI schema to remove fields not supported by Gemini API.
    Gemini only supports a subset of OpenAPI schema fields.
    Every property MUST have a type field.
    """
    if not isinstance(schema, dict):
        return schema

    # Fields supported by Gemini API
    supported_fields = {"type", "description", "properties", "required", "items", "enum", "format", "nullable"}

    cleaned = {}
    for key, value in schema.items():
        if key not in supported_fields:
            continue

        if key == "properties" and isinstance(value, dict):
            # Recursively clean nested properties
            # Filter out properties that don't have a valid type after cleaning
            cleaned_props = {}
            for prop_name, prop_schema in value.items():
                cleaned_prop = _clean_schema_for_gemini(prop_schema)
                # Only include property if it has a type (Gemini requires type for all properties)
                if cleaned_prop.get("type"):
                    cleaned_props[prop_name] = cleaned_prop
            if cleaned_props:
                cleaned[key] = cleaned_props
        elif key == "items" and isinstance(value, dict):
            # Recursively clean array items schema
            cleaned[key] = _clean_schema_for_gemini(value)
        elif key == "required" and isinstance(value, list):
            # Only include required if non-empty
            if value:
                cleaned[key] = value
        else:
            cleaned[key] = value

    # If type is object but no properties, remove type to avoid Gemini error
    if cleaned.get("type") == "object" and "properties" not in cleaned:
        cleaned.pop("type", None)

    # Filter required list to only include properties that exist after cleaning
    if "required" in cleaned and "properties" in cleaned:
        cleaned["required"] = [r for r in cleaned["required"] if r in cleaned["properties"]]
        if not cleaned["required"]:
            del cleaned["required"]

    return cleaned


def _convert_openai_tools_to_gemini(openai_tools: list) -> list:
    """
    Convert OpenAI format tools to Gemini functionDeclarations format.

    OpenAI format:
    [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }
    ]

    Gemini format:
    [
        {
            "functionDeclarations": [
                {
                    "name": "search_web",
                    "description": "Search the web",
                    "parameters": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            ]
        }
    ]
    """
    if not openai_tools or not isinstance(openai_tools, list):
        return []

    function_declarations = []

    for tool in openai_tools:
        if not isinstance(tool, dict):
            continue

        tool_type = tool.get("type", "function")
        if tool_type != "function":
            continue

        function_spec = tool.get("function", {})
        if not isinstance(function_spec, dict):
            continue

        # Extract function details
        name = function_spec.get("name")
        description = function_spec.get("description", "")
        parameters = function_spec.get("parameters", {})

        if not name:
            continue

        # Clean parameters schema to remove unsupported fields
        cleaned_parameters = _clean_schema_for_gemini(parameters)

        # Build Gemini function declaration
        gemini_function = {
            "name": name,
            "description": description,
        }
        # Only add parameters if non-empty (Gemini rejects empty parameters object)
        if cleaned_parameters:
            gemini_function["parameters"] = cleaned_parameters

        function_declarations.append(gemini_function)

    if not function_declarations:
        return []

    return [{"functionDeclarations": function_declarations}]


def _extract_content(candidate: dict, starting_tool_index: int = 0) -> tuple[str, str, str, str, list, int]:
    """
    Extract text + inline image markdown + grounding metadata + thinking content + tool calls from a Gemini candidate.
    Returns: (text, image_markdown, grounding_markdown, thinking_content, tool_calls, next_tool_index)

    Args:
        candidate: Gemini API response candidate
        starting_tool_index: The starting index for tool calls (for parallel tool call scenarios)

    Returns:
        Tuple of (text, image_markdown, grounding_markdown, thinking_content, tool_calls, next_tool_index)
        next_tool_index is the index to use for the next tool call
    """
    # SAFEGUARD: Handle None or invalid candidate
    if candidate is None or not isinstance(candidate, dict):
        return "", "", "", "", [], starting_tool_index

    content = candidate.get("content", {}) or {}
    parts = content.get("parts", []) or []

    text_parts = []
    thinking_parts = []
    image_md_parts = []
    tool_calls = []
    tool_call_index = starting_tool_index  # CRITICAL: Use starting index for parallel tool calls

    for part in parts:
        # DEBUG: Log each part to see what Gemini returns
        if part.get("thought") is True or "thought" in part:
            log.info(f"[GEMINI THINKING DEBUG] Found thought part: thought={part.get('thought')}, keys={list(part.keys())}")

        if "text" in part and part["text"]:
            # Check if this is a thinking part (Gemini 3 thinking mode)
            if part.get("thought") is True:
                thinking_parts.append(part["text"])
                log.info(f"[GEMINI THINKING] Extracted thinking content: {part['text'][:200]}...")
            else:
                text_parts.append(part["text"])
        elif "inlineData" in part:
            inline_data = part.get("inlineData", {}) or {}
            mime_type = inline_data.get("mimeType", "image/png")
            data = inline_data.get("data", "")
            if data:
                image_md_parts.append(f"\n![Generated Image](data:{mime_type};base64,{data})\n")
        elif "functionCall" in part:
            # Extract Gemini function call and convert to OpenAI format
            function_call = part.get("functionCall", {})
            # DEBUG: Log the raw functionCall to see if thought_signature is present
            log.info(f"[GEMINI DEBUG] Raw functionCall from Gemini: {json.dumps(function_call, ensure_ascii=False, default=str)[:500]}")
            if isinstance(function_call, dict):
                function_name = function_call.get("name", "")
                function_args = function_call.get("args", {})
                # Gemini 3 introduces thought_signature for security
                thought_signature = function_call.get("thought_signature", "")

                if function_name:
                    # Convert args dict to JSON string for OpenAI format
                    try:
                        args_json = json.dumps(function_args, ensure_ascii=False)
                    except Exception:
                        args_json = "{}"

                    tool_call_data = {
                        "index": tool_call_index,  # CRITICAL FIX: Add index field for middleware
                        "id": f"call_{uuid.uuid4().hex}",
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": args_json
                        }
                    }
                    # Store thought_signature in a custom field for Gemini 3 compatibility
                    if thought_signature:
                        tool_call_data["thought_signature"] = thought_signature
                        log.info(f"[GEMINI 3] Captured thought_signature for function {function_name}")

                    tool_calls.append(tool_call_data)
                    tool_call_index += 1  # Increment for next tool call

    # Extract Grounding Metadata (Search Sources)
    grounding_md = ""
    grounding_metadata = candidate.get("groundingMetadata", {})
    if grounding_metadata:
        chunks = grounding_metadata.get("groundingChunks", [])
        supports = grounding_metadata.get("groundingSupports", [])

        # Only process if we have web chunks
        web_sources = []
        for chunk in chunks:
            web = chunk.get("web", {})
            if web:
                title = web.get("title", "Source")
                uri = web.get("uri", "")
                if uri:
                    web_sources.append(f"[{title}]({uri})")

        if web_sources:
            grounding_md = "\n\n**Sources:**\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(web_sources)]) + "\n"

    thinking_content = "".join(thinking_parts)
    return "".join(text_parts), "".join(image_md_parts), grounding_md, thinking_content, tool_calls, tool_call_index


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

    # Clear model cache when config changes
    request.app.state.BASE_MODELS = None

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
            request.app.state.config.GEMINI_API_KEYS = request.app.state.config.GEMINI_API_KEYS[:num_urls]
        else:
            request.app.state.config.GEMINI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.GEMINI_API_BASE_URLS):
        api_config = request.app.state.config.GEMINI_API_CONFIGS.get(str(idx), {})
        enable = api_config.get("enable", True)
        model_ids = api_config.get("model_ids", [])

        if enable:
            if len(model_ids) == 0:
                # No models specified, skip fetching (user should add models manually)
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))
            else:
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
                        **({"tags": model["tags"]} if "tags" in model else {}),
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
        api_config = request.app.state.config.GEMINI_API_CONFIGS.get(str(url_idx), {})

        response = await send_get_request(f"{url}/models", key, api_config)
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
            raise HTTPException(status_code=500, detail="Failed to connect to Gemini API")
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
        raise HTTPException(status_code=500, detail="Open WebUI: Server Connection Error")


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

    # Detect if this is an image editing model
    image_edit_keywords = ["image-preview", "image-edit", "imagen"]
    is_image_edit_model = any(keyword in model_id.lower() for keyword in image_edit_keywords)
    
    # For image editing models, only use the last user message to save tokens
    # Image editing is a single-shot operation that doesn't need conversation history
    if is_image_edit_model:
        original_count = len(messages)
        
        # Extract system message if present
        system_msg = None
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg
                break
        
        # Helper function to check if a message contains an image
        # Supports both OpenAI format {"type": "image_url"} and Markdown format ![...](data:image/...)
        import re
        markdown_image_pattern = re.compile(r'!\[.*?\]\((data:image/[^;]+;base64,[A-Za-z0-9+/=]+)\)')
        
        def has_image(msg):
            content = msg.get("content", "")
            # Ensure content is string, not bytes
            if isinstance(content, bytes):
                try:
                    content = content.decode("utf-8")
                except Exception:
                    content = ""
            # Check OpenAI multimodal format
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") in ["image_url", "image"]:
                            return True
            # Check for Markdown embedded base64 image in string content
            if isinstance(content, str):
                if markdown_image_pattern.search(content):
                    return True
            return False
            
        # Helper function to extract images from a message
        # Converts Markdown images to OpenAI format for consistency
        def extract_images(msg):
            images = []
            content = msg.get("content", "")
            # Ensure content is string, not bytes
            if isinstance(content, bytes):
                try:
                    content = content.decode("utf-8")
                except Exception:
                    content = ""
            # Extract from OpenAI multimodal format
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") in ["image_url", "image"]:
                        images.append(item)
            # Extract from Markdown format and convert to OpenAI format
            if isinstance(content, str):
                matches = markdown_image_pattern.findall(content)
                for data_url in matches:
                    images.append({
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    })
            return images
        
        # Helper function to extract text from a message
        def extract_text(msg):
            content = msg.get("content", "")
            # Ensure content is string, not bytes
            if isinstance(content, bytes):
                try:
                    content = content.decode("utf-8")
                except Exception:
                    content = ""
            if isinstance(content, str):
                # Remove Markdown image syntax from text
                text = markdown_image_pattern.sub('', content).strip()
                return text if text else content
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        texts.append(item)
                return " ".join(texts)
            return ""

        # DEBUG LOGGING: Print structure of last few messages to understand why image is not found
        log.info(f"DEBUG: Scanning {len(messages)} messages for images. Dumping structure:")
        for i, msg in enumerate(reversed(messages)):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            content_type = type(content).__name__
            content_preview = "..."
            if isinstance(content, list):
                content_preview = str([
                    {k: v for k, v in item.items() if k != 'image_url'} 
                    if isinstance(item, dict) else str(item)[:50] 
                    for item in content
                ])
            elif isinstance(content, str):
                content_preview = content[:100]
            
            log.info(f"DEBUG Msg {len(messages)-1-i} [{role}]: type={content_type}, content={content_preview}")
            if i >= 4: # Only check last 5 messages to avoid log spam
                break

        # Find the last message with an image (from ANY role: user or assistant)
        last_image_msg = None
        last_image_index = -1
        for i, msg in enumerate(reversed(messages)):
            if has_image(msg):
                last_image_msg = msg
                last_image_index = len(messages) - 1 - i
                log.info(f"Found image in message {last_image_index} (Role: {msg.get('role')})")
                break
        
        # Find the last user message (the edit instruction)
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg
                break
        
        # CRITICAL FIX: Only modify messages if we actually found what we need
        if last_image_msg and last_user_msg:
            # Build the combined message
            if last_image_msg != last_user_msg:
                # Image and instruction are in different messages - merge them
                images = extract_images(last_image_msg)
                instruction_text = extract_text(last_user_msg)
                
                # Create combined content: images + instruction text
                combined_content = images + [{"type": "text", "text": instruction_text}]
                combined_msg = {"role": "user", "content": combined_content}
                
                messages = [combined_msg]
                log.info(f"Image edit mode: Merged image from msg {last_image_index} with instruction from last user msg")
            else:
                # Last message already contains the image, use it directly
                messages = [last_user_msg]
                log.info("Image edit mode: Last user message already contains the image")
            
            if system_msg:
                messages.insert(0, system_msg)
            log.info(f"Image edit mode: Trimmed messages from {original_count} to {len(messages)} to save tokens")
        else:
            log.warning(f"Image edit mode: Aborted optimization. Found Image: {bool(last_image_msg)}, Found User Msg: {bool(last_user_msg)}. Sending original messages.")

    # Build Gemini contents
    contents = []
    system_instruction = None

    # DEBUG: Log the raw messages before conversion
    log.info(f"[GEMINI MESSAGES DEBUG] Received {len(messages)} messages from middleware")
    for i, msg in enumerate(messages):
        msg_role = msg.get("role", "unknown")
        msg_content_preview = str(msg.get("content", ""))[:100]
        has_tool_calls = bool(msg.get("tool_calls"))
        tool_call_id = msg.get("tool_call_id", "")
        log.info(f"[GEMINI MESSAGES DEBUG] Message {i}: role={msg_role}, has_tool_calls={has_tool_calls}, tool_call_id={tool_call_id}, content_preview={msg_content_preview}")

        # DEBUG: Log full structure of assistant and tool messages
        if msg_role in ("assistant", "tool", "function"):
            log.info(f"[GEMINI MESSAGES DEBUG] Message {i} FULL: {json.dumps(msg, ensure_ascii=False, default=str)[:1000]}")

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            system_instruction = content
            continue

        # Handle tool/function response messages
        if role in ("tool", "function"):
            # Convert OpenAI tool response to Gemini functionResponse format
            tool_call_id = msg.get("tool_call_id") or msg.get("id")
            tool_name = msg.get("name", "")

            # CRITICAL FIX: If tool_name is missing from the message (middleware doesn't include it),
            # we need to find it by matching tool_call_id with previous assistant message's tool_calls
            if not tool_name and tool_call_id:
                # Search backwards through messages to find the assistant message with matching tool_call_id
                for prev_msg in reversed(messages[:messages.index(msg)]):
                    if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                        for tool_call in prev_msg.get("tool_calls", []):
                            if tool_call.get("id") == tool_call_id:
                                tool_name = tool_call.get("function", {}).get("name", "")
                                log.info(f"[TOOL RESPONSE DEBUG] Found tool_name={tool_name} by matching tool_call_id={tool_call_id}")
                                break
                    if tool_name:
                        break

            # Parse the response content
            try:
                if isinstance(content, str):
                    response_data = json.loads(content) if content else {}
                else:
                    response_data = content
            except json.JSONDecodeError:
                response_data = {"result": content}

            # DEBUG: Log the response data structure
            log.info(f"[TOOL RESPONSE DEBUG] tool_call_id={tool_call_id}, tool_name={tool_name}, response_data type={type(response_data).__name__}, value={json.dumps(response_data, ensure_ascii=False, default=str)[:500]}")

            # Gemini API expects functionResponse with 'response' field containing a dict
            # CRITICAL FIX: If response_data is a list (e.g., search results), wrap it in a dict with 'results' key
            # Do NOT convert to string! Keep the original structure.
            if isinstance(response_data, list):
                response_data = {"results": response_data}
            elif not isinstance(response_data, dict):
                response_data = {"result": str(response_data)}

            # Gemini API要求functionResponse使用role="user"而不是"function"
            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": tool_name,
                        "response": response_data
                    }
                }]
            })
            log.info(f"[TOOL RESPONSE DEBUG] Added functionResponse to contents: {json.dumps(contents[-1], ensure_ascii=False, default=str)[:500]}")
            continue

        gemini_role = "user" if role == "user" else "model"

        # Handle assistant messages with tool_calls
        if role == "assistant" and msg.get("tool_calls"):
            parts = []

            # Add text content if present
            if content:
                parts.append({"text": content})

            # Add function calls
            for tool_call in msg.get("tool_calls", []):
                if not isinstance(tool_call, dict):
                    continue

                function_spec = tool_call.get("function", {})
                function_name = function_spec.get("name", "")
                function_args_str = function_spec.get("arguments", "{}")

                # Parse arguments from JSON string to dict
                try:
                    function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
                except json.JSONDecodeError:
                    function_args = {}

                if function_name:
                    function_call_part = {
                        "functionCall": {
                            "name": function_name,
                            "args": function_args
                        }
                    }
                    # Restore thought_signature for Gemini 3 compatibility
                    thought_signature = tool_call.get("thought_signature", "")
                    if thought_signature:
                        function_call_part["functionCall"]["thought_signature"] = thought_signature
                        log.info(f"[GEMINI 3] Restored thought_signature for function {function_name}")

                    parts.append(function_call_part)

            if parts:
                contents.append({"role": gemini_role, "parts": parts})
            continue

        # Handle multimodal content
        if isinstance(content, list):
            parts = []
            for item in content:
                if item.get("type") == "text":
                    parts.append({"text": item.get("text", "")})
                elif item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:"):
                        header, data = image_url.split(",", 1)
                        mime_type = header.split(":")[1].split(";")[0]
                        parts.append(
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": data,
                                }
                            }
                        )
                    else:
                        parts.append({"text": f"[Image: {image_url}]"})
            contents.append({"role": gemini_role, "parts": parts})
        else:
            contents.append({"role": gemini_role, "parts": [{"text": content}]})

    # Clean model ID for Gemini API
    gemini_model = model_id
    for prefix_check in request.app.state.config.GEMINI_API_CONFIGS.values():
        prefix = prefix_check.get("prefix_id", "")
        if prefix and model_id.startswith(f"{prefix}."):
            gemini_model = model_id[len(prefix) + 1 :]
            break

    # Build Gemini request
    gemini_payload = {"contents": contents, "generationConfig": {}}

    # Enable image output for image-capable models
    image_keywords = ["image", "draw", "paint", "picture", "art", "create-preview"]
    is_image_model = any(keyword in gemini_model.lower() for keyword in image_keywords)
    if is_image_model:
        log.info(f"Detected image generation model: {gemini_model}")
        gemini_payload["generationConfig"]["responseModalities"] = ["TEXT", "IMAGE"]
        if stream:
            log.info(f"Forcing stream=False for image model {gemini_model}")
            stream = False

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
        gemini_payload["generationConfig"]["stopSequences"] = (
            form_data["stop"] if isinstance(form_data["stop"], list) else [form_data["stop"]]
        )

    # Handle reasoning_effort -> thinkingConfig
    reasoning_effort = form_data.get("reasoning_effort")
    if reasoning_effort is not None:
        # Map reasoning_effort to thinkingBudget
        # Gemini supports thinkingBudget: 0 (off), or 1-24576
        effort_to_budget = {
            "none": 0,
            "minimal": 1024,
            "low": 2048,
            "medium": 8192,
            "high": 16384,
            "xhigh": 20480,
            "max": 24576,
        }
        if reasoning_effort in effort_to_budget:
            budget = effort_to_budget[reasoning_effort]
        else:
            # Try to parse as integer for custom values
            try:
                budget = int(reasoning_effort)
            except (ValueError, TypeError):
                budget = 8192  # Default to medium

        if budget > 0:
            gemini_payload["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": budget,
                "includeThoughts": True  # Required to get thinking content in response
            }
            log.info(f"[GEMINI] Enabled thinkingConfig with budget {budget} for model {gemini_model}")

    # Handle tools: Convert OpenAI format to Gemini format
    # Priority: Google Search > Native Tools
    if _wants_web_search(form_data):
        # Enable Google Search (Grounding)
        log.info(f"Enabling Google Search (Grounding) for model: {gemini_model}")
        gemini_payload["tools"] = [{"googleSearch": {}}]
    elif "tools" in form_data and form_data["tools"]:
        # Convert OpenAI format tools to Gemini functionDeclarations
        gemini_tools = _convert_openai_tools_to_gemini(form_data["tools"])
        if gemini_tools:
            gemini_payload["tools"] = gemini_tools
            log.info(f"Converted {len(form_data['tools'])} OpenAI tools to Gemini format for model: {gemini_model}")
            # Log first tool for debugging schema cleaning
            if gemini_tools and gemini_tools[0].get("functionDeclarations"):
                first_func = gemini_tools[0]["functionDeclarations"][0]
                log.info(f"[GEMINI TOOLS DEBUG] First function after cleaning: {json.dumps(first_func, ensure_ascii=False, default=str)[:500]}")

    # CRITICAL FIX: Gemini tool calling的消息序列规则
    # 当最后一条消息包含functionResponse时,说明我们在tool calling的第二轮
    # 此时应该只保留与当前tool call相关的user-model-functionResponse三元组,移除之前的对话历史
    contents = gemini_payload.get("contents", [])

    # 检查最后一条消息是否包含functionResponse (而不是检查role,因为role现在是"user")
    last_has_function_response = False
    if contents:
        last_parts = contents[-1].get("parts", [])
        last_has_function_response = any("functionResponse" in part for part in last_parts)

    if last_has_function_response:
        log.info("[GEMINI TOOL FIX] Detected tool calling scenario (last message contains functionResponse)")

        # 从后往前找到包含tool call的model消息
        tool_call_index = -1
        for i in range(len(contents) - 2, -1, -1):  # 倒数第二条开始往前找
            if contents[i].get("role") == "model":
                parts = contents[i].get("parts", [])
                if any("functionCall" in part for part in parts):
                    tool_call_index = i
                    log.info(f"[GEMINI TOOL FIX] Found tool call at index {i}")
                    break

        # 检查functionCall是否有thought_signature (Gemini 3需要)
        has_thought_signature = False
        if tool_call_index >= 0:
            model_parts = contents[tool_call_index].get("parts", [])
            for part in model_parts:
                if "functionCall" in part:
                    fc = part.get("functionCall", {})
                    if fc.get("thought_signature"):
                        has_thought_signature = True
                        break

        # 对于Gemini 3: 如果functionCall缺少thought_signature，使用替代方案
        is_gemini_3 = "gemini-3" in gemini_model.lower()
        if is_gemini_3 and not has_thought_signature and tool_call_index >= 0:
            log.info("[GEMINI 3 WORKAROUND] functionCall missing thought_signature, converting to text format")

            # 找到user消息
            user_msg_index = -1
            for i in range(tool_call_index - 1, -1, -1):
                if contents[i].get("role") == "user":
                    parts = contents[i].get("parts", [])
                    has_text = any("text" in part for part in parts)
                    has_func_response = any("functionResponse" in part for part in parts)
                    if has_text and not has_func_response:
                        user_msg_index = i
                        break

            if user_msg_index >= 0:
                # 提取原始user问题
                user_text = ""
                for part in contents[user_msg_index].get("parts", []):
                    if "text" in part:
                        user_text = part.get("text", "")
                        break

                # 提取functionResponse结果
                func_response_text = ""
                last_msg_parts = contents[-1].get("parts", [])
                for part in last_msg_parts:
                    if "functionResponse" in part:
                        fr = part.get("functionResponse", {})
                        func_name = fr.get("name", "tool")
                        func_result = fr.get("response", {})
                        func_response_text = f"\n\n[Tool Result from {func_name}]:\n{json.dumps(func_result, ensure_ascii=False, indent=2)}"
                        break

                # 创建新的contents: 只有user消息，包含原始问题+工具结果
                combined_text = user_text + func_response_text + "\n\nPlease answer based on the tool results above."
                new_contents = [
                    {"role": "user", "parts": [{"text": combined_text}]}
                ]
                gemini_payload["contents"] = new_contents
                log.info(f"[GEMINI 3 WORKAROUND] Converted to single user message with tool results embedded")

        else:
            # 正常的tool calling流程 (非Gemini 3，或有thought_signature)
            # 再往前找到对应的user消息 (必须是包含text的,不是包含functionResponse的)
            if tool_call_index > 0:
                user_msg_index = -1
                for i in range(tool_call_index - 1, -1, -1):
                    if contents[i].get("role") == "user":
                        # 确保这是包含text的user消息,不是functionResponse
                        parts = contents[i].get("parts", [])
                        has_text = any("text" in part for part in parts)
                        has_func_response = any("functionResponse" in part for part in parts)
                        if has_text and not has_func_response:
                            user_msg_index = i
                            log.info(f"[GEMINI TOOL FIX] Found corresponding user message at index {i}")
                            break

                # 只保留user->model(tool_call)->functionResponse这三条消息
                if user_msg_index >= 0:
                    original_count = len(contents)
                    trimmed_contents = contents[user_msg_index:]
                    gemini_payload["contents"] = trimmed_contents
                    log.info(f"[GEMINI TOOL FIX] Trimmed contents from {original_count} to {len(trimmed_contents)} messages")
                    log.info(f"[GEMINI TOOL FIX] Kept messages from index {user_msg_index} to end")

    # DEBUG: Log the complete contents array before making the request
    log.info(f"[GEMINI PAYLOAD DEBUG] Complete contents count: {len(gemini_payload.get('contents', []))}")
    for i, item in enumerate(gemini_payload.get("contents", [])):
        log.info(f"[GEMINI PAYLOAD DEBUG] Content {i}: role={item.get('role')}, parts_count={len(item.get('parts', []))}, parts_types={[list(p.keys()) for p in item.get('parts', [])]}")
    log.info(f"[GEMINI PAYLOAD DEBUG] Complete contents array: {json.dumps(gemini_payload.get('contents', []), ensure_ascii=False, default=str)[:2000]}")

    # Remove empty generationConfig to avoid potential issues
    if "generationConfig" in gemini_payload and not gemini_payload["generationConfig"]:
        del gemini_payload["generationConfig"]

    # Log full payload for debugging 400 errors
    log.info(f"[GEMINI PAYLOAD DEBUG] Full payload: {json.dumps(gemini_payload, ensure_ascii=False, default=str)[:5000]}")

    # Make request to Gemini API
    endpoint = "streamGenerateContent" if stream else "generateContent"

    # Determine authentication method based on config
    auth_type = api_config.get("auth_type", "bearer")
    headers = {"Content-Type": "application/json"}

    if auth_type == "bearer" and key:
        gemini_url = f"{url}/models/{gemini_model}:{endpoint}?key={key}"
    elif auth_type == "none":
        gemini_url = f"{url}/models/{gemini_model}:{endpoint}"
    else:
        gemini_url = f"{url}/models/{gemini_model}:{endpoint}?key={key}"

    if stream:
        gemini_url += ("&" if "?" in gemini_url else "?") + "alt=sse"

    log.info(f"Gemini Chat Request: URL={gemini_url}, AuthType={auth_type}, Stream={stream}")

    if stream:

        async def stream_generator():
            timeout = aiohttp.ClientTimeout(total=300)
            decoder = codecs.getincrementaldecoder("utf-8")()
            buf = ""
            stream_id = f"chatcmpl-gemini-{uuid.uuid4().hex}"
            global_tool_call_index = 0  # CRITICAL: Track tool call index across stream chunks for parallel tool calls

            try:
                async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                    async with session.post(gemini_url, json=gemini_payload, headers=headers) as response:
                        log.info(f"Gemini Stream Response Status: {response.status}")
                        log.info(f"Gemini Stream Response Headers: {response.headers}")

                        if response.status != 200:
                            try:
                                err_text = await response.text()
                            except Exception as e:
                                err_text = f"Failed to read error body: {e}"

                            # Log full error for debugging
                            log.error(f"[GEMINI API ERROR] Status: {response.status}, Full response: {err_text[:2000]}")

                            # Format understandable error message
                            msg = f"[Gemini API Error {response.status}] {err_text[:500]}"
                            try:
                                err_json = json.loads(err_text)
                                if "error" in err_json:
                                    msg = f"[Gemini API Error {response.status}] {err_json['error'].get('message', err_text[:200])}"
                            except:
                                pass

                            # Stream error object that frontend can detect for red styling
                            error_chunk = {
                                "error": {
                                    "message": msg,
                                    "type": "api_error",
                                    "code": f"http_{response.status}"
                                }
                            }
                            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            try:
                                await response.release()
                            except:
                                pass
                            return

                        # Optional: send role first (OpenAI-style)
                        yield f"data: {json.dumps(_openai_chunk(stream_id, model_id, {'role': 'assistant'}), ensure_ascii=False)}\n\n"

                        async for raw in response.content.iter_any():
                            if not raw:
                                continue

                            # Decode bytes to string, handling incomplete UTF-8 sequences
                            chunk_str = decoder.decode(raw, False)
                            if not chunk_str:
                                continue
                            buf += chunk_str

                            # SSE events are separated by blank line
                            while "\n\n" in buf:
                                event, buf = buf.split("\n\n", 1)
                                if not event.strip():
                                    continue

                                # collect all data lines
                                data_lines = []
                                for line in event.splitlines():
                                    line = line.rstrip("\r")
                                    if line.startswith("data:"):
                                        data_lines.append(line[5:].lstrip())
                                if not data_lines:
                                    continue

                                data_str = "\n".join(data_lines).strip()
                                if not data_str:
                                    continue

                                if data_str == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    return

                                # Handle potentially stacked JSONs (e.g. if \n\n was missed or data lines merged)
                                json_decoder = json.JSONDecoder()
                                pos = 0
                                while pos < len(data_str):
                                    search_str = data_str[pos:].lstrip()
                                    if not search_str:
                                        break
                                    try:
                                        gemini_obj, idx = json_decoder.raw_decode(search_str)
                                        # raw_decode returns index relative to search_str
                                        pos += len(data_str[pos:]) - len(search_str) + idx
                                        
                                        candidates = gemini_obj.get("candidates") or []
                                        if not candidates:
                                            continue

                                        c0 = candidates[0]
                                        # SAFEGUARD: Skip if candidate is None
                                        if c0 is None:
                                            continue
                                        text, image_md, grounding_md, thinking_content, tool_calls, global_tool_call_index = _extract_content(c0, global_tool_call_index)
                                        out_text = (text or "") + (image_md or "") + (grounding_md or "")

                                        # 1) yield thinking content first if present (reasoning_content for frontend)
                                        if thinking_content:
                                            thinking_chunk = _openai_chunk(stream_id, model_id, {"reasoning_content": thinking_content}, None, 0)
                                            yield f"data: {json.dumps(thinking_chunk, ensure_ascii=False)}\n\n"

                                        # 2) yield tool calls if present
                                        if tool_calls:
                                            for tool_call in tool_calls:
                                                tool_chunk = _openai_chunk(stream_id, model_id, {"tool_calls": [tool_call]}, None, 0)
                                                yield f"data: {json.dumps(tool_chunk, ensure_ascii=False)}\n\n"

                                        # 3) yield content if present (with chunking for large content like images)
                                        if out_text:
                                            for content_chunk in _yield_content_chunks(out_text, stream_id, model_id):
                                                yield content_chunk

                                        # 4) then yield finish with usage
                                        finish = _map_finish_reason(c0.get("finishReason") if isinstance(c0, dict) else None)
                                        if finish:
                                            # If there are tool calls, override finish_reason to "tool_calls"
                                            if tool_calls:
                                                finish = "tool_calls"
                                            # Extract usage from gemini response
                                            usage_meta = gemini_obj.get("usageMetadata", {}) or {}
                                            usage = None
                                            if usage_meta:
                                                usage = {
                                                    "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                                                    "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                                                    "total_tokens": usage_meta.get("totalTokenCount", 0),
                                                }
                                                # Add thinking tokens if available
                                                if usage_meta.get("thoughtsTokenCount"):
                                                    usage["reasoning_tokens"] = usage_meta.get("thoughtsTokenCount", 0)
                                            fin_chunk = _openai_chunk(stream_id, model_id, {}, finish, 0, usage)
                                            yield f"data: {json.dumps(fin_chunk, ensure_ascii=False)}\n\n"
                                            yield "data: [DONE]\n\n"
                                            return
                                            
                                    except json.JSONDecodeError as e:
                                        # If we can't decode the *first* object, it might be a partial frame (in main loop)
                                        # If we are in flush, it's just broken data.
                                        if pos == 0:
                                            # Put back and wait for more bytes (rare but safe)
                                            log.warning(f"JSON decode error (event): {e}, head={data_str[:120]}")
                                            buf = event + "\n\n" + buf
                                        else:
                                            log.warning(f"JSON decode error (stacked): {e} at pos {pos}")
                                        break

                        # flush remaining
                        tail = buf.strip()
                        if tail:
                            # try treat as one SSE event too
                            data_lines = []
                            for line in tail.splitlines():
                                line = line.rstrip("\r")
                                if line.startswith("data:"):
                                    data_lines.append(line[5:].lstrip())
                            if data_lines:
                                data_str = "\n".join(data_lines).strip()
                            else:
                                data_str = tail

                            if data_str and data_str != "[DONE]":
                                json_decoder_flush = json.JSONDecoder()
                                pos = 0
                                while pos < len(data_str):
                                    search_str = data_str[pos:].lstrip()
                                    if not search_str:
                                        break
                                    try:
                                        gemini_obj, idx = json_decoder_flush.raw_decode(search_str)
                                        pos += len(data_str[pos:]) - len(search_str) + idx

                                        candidates = gemini_obj.get("candidates") or []
                                        if candidates:
                                            c0 = candidates[0]
                                            # SAFEGUARD: Skip if candidate is None
                                            if c0 is None or not isinstance(c0, dict):
                                                continue
                                            text, image_md, grounding_md, thinking_content, tool_calls, global_tool_call_index = _extract_content(c0, global_tool_call_index)
                                            out_text = (text or "") + (image_md or "") + (grounding_md or "")

                                            # Yield thinking content first if present
                                            if thinking_content:
                                                thinking_chunk = _openai_chunk(stream_id, model_id, {"reasoning_content": thinking_content}, None, 0)
                                                yield f"data: {json.dumps(thinking_chunk, ensure_ascii=False)}\n\n"

                                            # Yield tool calls if present
                                            if tool_calls:
                                                for tool_call in tool_calls:
                                                    tool_chunk = _openai_chunk(stream_id, model_id, {"tool_calls": [tool_call]}, None, 0)
                                                    yield f"data: {json.dumps(tool_chunk, ensure_ascii=False)}\n\n"

                                            # Then yield content if present (with chunking for large content)
                                            if out_text:
                                                for content_chunk in _yield_content_chunks(out_text, stream_id, model_id):
                                                    yield content_chunk

                                            finish = _map_finish_reason(c0.get("finishReason") if isinstance(c0, dict) else None)
                                            if finish:
                                                # If there are tool calls, override finish_reason to "tool_calls"
                                                if tool_calls:
                                                    finish = "tool_calls"
                                                # Extract usage from gemini response
                                                usage_meta = gemini_obj.get("usageMetadata", {}) or {}
                                                usage = None
                                                if usage_meta:
                                                    usage = {
                                                        "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                                                        "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                                                        "total_tokens": usage_meta.get("totalTokenCount", 0),
                                                    }
                                                    if usage_meta.get("thoughtsTokenCount"):
                                                        usage["reasoning_tokens"] = usage_meta.get("thoughtsTokenCount", 0)
                                                fin_chunk = _openai_chunk(stream_id, model_id, {}, finish, 0, usage)
                                                yield f"data: {json.dumps(fin_chunk, ensure_ascii=False)}\n\n"
                                    except json.JSONDecodeError as e:
                                        log.warning(f"JSON decode error (flush): {e}, head={data_str[:120]}")
                                        break

                        yield "data: [DONE]\n\n"

            except Exception as e:
                log.exception(f"Error in stream generator: {e}")
                error_chunk = {
                    "error": {
                        "message": str(e),
                        "type": "stream_error",
                        "code": "internal_error"
                    }
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming response
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(gemini_url, json=gemini_payload, headers=headers) as response:
                log.info(f"Gemini Chat Response Status: {response.status}")
                if response.status != 200:
                    error_text = await response.text()
                    error_message = _parse_gemini_error_message(error_text)
                    if response.status == 400:
                        compat_payload = _build_compat_payload(
                            gemini_payload,
                            drop_tools=True,
                        )
                        if compat_payload != gemini_payload:
                            log.info("[GEMINI COMPAT] Retrying with tools/web_search stripped")
                            async with session.post(
                                gemini_url, json=compat_payload, headers=headers
                            ) as retry_response:
                                log.info(f"Gemini Chat Retry Response Status: {retry_response.status}")
                                if retry_response.status == 200:
                                    gemini_response = await retry_response.json(content_type=None)
                                    openai_response = convert_gemini_to_openai(gemini_response, model_id)
                                    return JSONResponse(content=openai_response)
                                retry_text = await retry_response.text()
                                error_message = _parse_gemini_error_message(retry_text)

                        compat_payload = _build_compat_payload(
                            gemini_payload,
                            drop_tools=True,
                            drop_thinking=True,
                        )
                        if compat_payload != gemini_payload:
                            log.info("[GEMINI COMPAT] Retrying with tools/web_search + thinkingConfig stripped")
                            async with session.post(
                                gemini_url, json=compat_payload, headers=headers
                            ) as retry_response:
                                log.info(f"Gemini Chat Retry Response Status: {retry_response.status}")
                                if retry_response.status == 200:
                                    gemini_response = await retry_response.json(content_type=None)
                                    openai_response = convert_gemini_to_openai(gemini_response, model_id)
                                    return JSONResponse(content=openai_response)
                                retry_text = await retry_response.text()
                                error_message = _parse_gemini_error_message(retry_text)

                        compat_payload = _build_compat_payload(
                            gemini_payload,
                            drop_tools=True,
                            drop_thinking=True,
                            drop_response_modalities=True,
                        )
                        if compat_payload != gemini_payload:
                            log.info("[GEMINI COMPAT] Retrying with tools/web_search + thinkingConfig + responseModalities stripped")
                            async with session.post(
                                gemini_url, json=compat_payload, headers=headers
                            ) as retry_response:
                                log.info(f"Gemini Chat Retry Response Status: {retry_response.status}")
                                if retry_response.status == 200:
                                    gemini_response = await retry_response.json(content_type=None)
                                    openai_response = convert_gemini_to_openai(gemini_response, model_id)
                                    return JSONResponse(content=openai_response)
                                retry_text = await retry_response.text()
                                error_message = _parse_gemini_error_message(retry_text)
                    raise HTTPException(
                        status_code=response.status,
                        detail=error_message or "Gemini API Error",
                    )

                gemini_response = await response.json(content_type=None)
                openai_response = convert_gemini_to_openai(gemini_response, model_id)
                return JSONResponse(content=openai_response)

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error calling Gemini API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def convert_gemini_to_openai(gemini_response: dict, model_id: str) -> dict:
    """Convert Gemini response to OpenAI non-streaming format."""
    candidates = gemini_response.get("candidates", []) or []

    choices = []
    tool_call_index = 0  # Track tool call index across candidates
    for i, candidate in enumerate(candidates):
        # SAFEGUARD: Skip if candidate is None
        if candidate is None or not isinstance(candidate, dict):
            continue
        text, image_md, grounding_md, thinking_content, tool_calls, tool_call_index = _extract_content(candidate, tool_call_index)
        combined = (text or "") + (image_md or "") + (grounding_md or "")

        message = {"role": "assistant", "content": combined}

        # Add reasoning_content if present (thinking mode)
        if thinking_content:
            message["reasoning_content"] = thinking_content

        # Add tool_calls to message if present
        if tool_calls:
            message["tool_calls"] = tool_calls

        # Determine finish_reason based on whether there are tool calls
        finish_reason = _map_finish_reason(candidate.get("finishReason") if isinstance(candidate, dict) else None) or "stop"
        if tool_calls and finish_reason == "stop":
            finish_reason = "tool_calls"

        choices.append(
            {
                "index": i,
                "message": message,
                "finish_reason": finish_reason,
            }
        )

    usage_meta = gemini_response.get("usageMetadata", {}) or {}
    usage_dict = {
        "prompt_tokens": usage_meta.get("promptTokenCount", 0),
        "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
        "total_tokens": usage_meta.get("totalTokenCount", 0),
    }
    # Add thinking tokens if available
    if usage_meta.get("thoughtsTokenCount"):
        usage_dict["reasoning_tokens"] = usage_meta.get("thoughtsTokenCount", 0)

    return {
        "id": f"chatcmpl-gemini-{model_id}",
        "object": "chat.completion",
        "model": model_id,
        "choices": choices,
        "usage": usage_dict,
    }


# 保留（可不用），以免你其他地方引用；流式现在由 stream_generator 直接拆分输出更稳
def convert_gemini_to_openai_stream(gemini_chunk: dict, model_id: str) -> dict:
    """Convert Gemini streaming chunk to OpenAI format (single-chunk)."""
    candidates = gemini_chunk.get("candidates", []) or []
    choices = []
    tool_call_index = 0  # Track tool call index

    for i, candidate in enumerate(candidates):
        text, image_md, grounding_md, thinking_content, tool_calls, tool_call_index = _extract_content(candidate, tool_call_index)
        combined = (text or "") + (image_md or "") + (grounding_md or "")
        delta = {"content": combined} if combined else {}

        # Add reasoning_content to delta if present
        if thinking_content:
            delta["reasoning_content"] = thinking_content

        # Add tool_calls to delta if present
        if tool_calls:
            delta["tool_calls"] = tool_calls

        choices.append(
            {
                "index": i,
                "delta": delta,
                "finish_reason": _map_finish_reason(candidate.get("finishReason")),
            }
        )

    return {
        "id": f"chatcmpl-gemini-{model_id}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": choices,
    }

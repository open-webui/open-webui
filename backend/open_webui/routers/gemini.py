"""
Gemini API Router

This module provides native Google Gemini API integration for Open WebUI.
It uses the REST v1beta endpoints (generateContent / streamGenerateContent with alt=sse)
and converts responses into OpenAI-compatible format for the Open WebUI frontend.
"""

import asyncio
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


def _openai_chunk(
    stream_id: str,
    model_id: str,
    delta: dict,
    finish_reason: Optional[str] = None,
    index: int = 0,
) -> dict:
    return {
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


def _extract_text_and_images(candidate: dict) -> tuple[str, str]:
    """
    Extract text + inline image markdown from a Gemini candidate.
    Returns: (text, image_markdown)
    """
    content = candidate.get("content", {}) or {}
    parts = content.get("parts", []) or []

    text_parts = []
    image_md_parts = []

    for part in parts:
        if "text" in part and part["text"]:
            text_parts.append(part["text"])
        elif "inlineData" in part:
            inline_data = part.get("inlineData", {}) or {}
            mime_type = inline_data.get("mimeType", "image/png")
            data = inline_data.get("data", "")
            if data:
                image_md_parts.append(f"\n![Generated Image](data:{mime_type};base64,{data})\n")

    return "".join(text_parts), "".join(image_md_parts)


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
                request_tasks.append(
                    send_get_request(
                        f"{url}/models",
                        request.app.state.config.GEMINI_API_KEYS[idx],
                        api_config,
                    )
                )
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
    if any(keyword in gemini_model.lower() for keyword in image_keywords):
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

    # Enable Google Search (Grounding)
    web_search_enabled = form_data.get("web_search", False)
    if web_search_enabled:
        log.info(f"Enabling Google Search (Grounding) for model: {gemini_model}")
        gemini_payload["tools"] = [{"googleSearch": {}}]

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

            try:
                async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                    async with session.post(gemini_url, json=gemini_payload, headers=headers) as response:
                        log.info(f"Gemini Stream Response Status: {response.status}")
                        log.info(f"Gemini Stream Response Headers: {response.headers}")

                        if response.status != 200:
                            try:
                                error_data = await response.json(content_type=None)
                            except Exception:
                                error_text = await response.text()
                                error_data = {"error": {"message": f"Gemini API Error: {error_text}"}}
                            error_msg = error_data.get("error", {}).get("message", "Gemini API Error")
                            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            return

                        # Optional: send role first (OpenAI-style)
                        yield f"data: {json.dumps(_openai_chunk(stream_id, model_id, {'role': 'assistant'}), ensure_ascii=False)}\n\n"

                        async for raw in response.content.iter_any():
                            if not raw:
                                continue
                            buf += decoder.decode(raw)

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
                                decoder = json.JSONDecoder()
                                pos = 0
                                while pos < len(data_str):
                                    search_str = data_str[pos:].lstrip()
                                    if not search_str:
                                        break
                                    try:
                                        gemini_obj, idx = decoder.raw_decode(search_str)
                                        # raw_decode returns index relative to search_str
                                        pos += len(data_str[pos:]) - len(search_str) + idx
                                        
                                        candidates = gemini_obj.get("candidates") or []
                                        if not candidates:
                                            continue

                                        c0 = candidates[0]
                                        text, image_md = _extract_text_and_images(c0)
                                        out_text = (text or "") + (image_md or "")

                                        # 1) yield content first
                                        if out_text:
                                            chunk = _openai_chunk(stream_id, model_id, {"content": out_text}, None, 0)
                                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                                        # 2) then yield finish
                                        finish = _map_finish_reason(c0.get("finishReason"))
                                        if finish:
                                            fin_chunk = _openai_chunk(stream_id, model_id, {}, finish, 0)
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
                                decoder = json.JSONDecoder()
                                pos = 0
                                while pos < len(data_str):
                                    search_str = data_str[pos:].lstrip()
                                    if not search_str:
                                        break
                                    try:
                                        gemini_obj, idx = decoder.raw_decode(search_str)
                                        pos += len(data_str[pos:]) - len(search_str) + idx

                                        candidates = gemini_obj.get("candidates") or []
                                        if candidates:
                                            c0 = candidates[0]
                                            text, image_md = _extract_text_and_images(c0)
                                            out_text = (text or "") + (image_md or "")
                                            if out_text:
                                                chunk = _openai_chunk(stream_id, model_id, {"content": out_text}, None, 0)
                                                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                                            finish = _map_finish_reason(c0.get("finishReason"))
                                            if finish:
                                                fin_chunk = _openai_chunk(stream_id, model_id, {}, finish, 0)
                                                yield f"data: {json.dumps(fin_chunk, ensure_ascii=False)}\n\n"
                                    except json.JSONDecodeError as e:
                                        log.warning(f"JSON decode error (flush): {e}, head={data_str[:120]}")
                                        break

                        yield "data: [DONE]\n\n"

            except Exception as e:
                log.exception(f"Error in stream generator: {e}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming response
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(gemini_url, json=gemini_payload, headers=headers) as response:
                log.info(f"Gemini Chat Response Status: {response.status}")
                if response.status != 200:
                    try:
                        error_data = await response.json(content_type=None)
                    except Exception:
                        error_text = await response.text()
                        error_data = {"error": {"message": f"Gemini API Error: {error_text}"}}
                    raise HTTPException(
                        status_code=response.status,
                        detail=error_data.get("error", {}).get("message", "Gemini API Error"),
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
    for i, candidate in enumerate(candidates):
        text, image_md = _extract_text_and_images(candidate)
        combined = (text or "") + (image_md or "")

        choices.append(
            {
                "index": i,
                "message": {"role": "assistant", "content": combined},
                "finish_reason": _map_finish_reason(candidate.get("finishReason")) or "stop",
            }
        )

    usage = gemini_response.get("usageMetadata", {}) or {}

    return {
        "id": f"chatcmpl-gemini-{model_id}",
        "object": "chat.completion",
        "model": model_id,
        "choices": choices,
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        },
    }


# 保留（可不用），以免你其他地方引用；流式现在由 stream_generator 直接拆分输出更稳
def convert_gemini_to_openai_stream(gemini_chunk: dict, model_id: str) -> dict:
    """Convert Gemini streaming chunk to OpenAI format (single-chunk)."""
    candidates = gemini_chunk.get("candidates", []) or []
    choices = []

    for i, candidate in enumerate(candidates):
        text, image_md = _extract_text_and_images(candidate)
        combined = (text or "") + (image_md or "")
        delta = {"content": combined} if combined else {}
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

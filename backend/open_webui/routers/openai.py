import asyncio
import copy
import hashlib
import json
import logging
import time
from typing import Optional

import aiohttp
from aiocache import cached
import requests

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    JSONResponse,
    PlainTextResponse,
)
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
)
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
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
    stream_chunks_handler,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.rate_limiter import limiter, get_role_based_limit, get_write_operation_limit
from open_webui.utils.access_control import has_access
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.prompt_composer import compose_with_fallback
from open_webui.utils.tool_gating import (
    build_tool_catalog,
    build_tool_selection_system_prompt,
    parse_tool_selection_response,
    get_tool_prompts_by_commands,
    compose_stage2_system_prompt,
)
from open_webui.utils.tool_inline_executor import build_tool_hints
from open_webui.utils.gemini_cache_manager import GeminiCacheManager


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url, key=None, user: UserModel = None):
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


def openai_reasoning_model_handler(payload):
    """
    Handle reasoning model specific parameters
    """
    if "max_tokens" in payload:
        # Convert "max_tokens" to "max_completion_tokens" for all reasoning models
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    # Handle system role conversion based on model type
    if payload["messages"][0]["role"] == "system":
        model_lower = payload["model"].lower()
        # Legacy models use "user" role instead of "system"
        if model_lower.startswith("o1-mini") or model_lower.startswith("o1-preview"):
            payload["messages"][0]["role"] = "user"
        else:
            payload["messages"][0]["role"] = "developer"

    return payload


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
                "HTTP-Referer": "https://openwebui.com/",
                "X-Title": "Open WebUI",
            }
            if "openrouter.ai" in url
            else {}
        ),
    }

    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)
        if metadata and metadata.get("chat_id"):
            headers["X-OpenWebUI-Chat-Id"] = metadata.get("chat_id")

    token = None
    auth_type = config.get("auth_type")

    if auth_type == "bearer" or auth_type is None:
        # Default to bearer if not specified
        token = f"{key}"
    elif auth_type == "none":
        token = None
    elif auth_type == "session":
        cookies = request.cookies
        token = request.state.token.credentials
    elif auth_type == "system_oauth":
        cookies = request.cookies

        oauth_token = None
        try:
            if request.cookies.get("oauth_session_id", None):
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id,
                    request.cookies.get("oauth_session_id", None),
                )
        except Exception as e:
            log.error(f"Error getting OAuth token: {e}")

        if oauth_token:
            token = f"{oauth_token.get('access_token', '')}"

    elif auth_type in ("azure_ad", "microsoft_entra_id"):
        token = get_microsoft_entra_id_access_token()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if config.get("headers") and isinstance(config.get("headers"), dict):
        headers = {**headers, **config.get("headers")}

    return headers, cookies


def get_microsoft_entra_id_access_token():
    """
    Get Microsoft Entra ID access token using DefaultAzureCredential for Azure OpenAI.
    Returns the token string or None if authentication fails.
    """
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        return token_provider()
    except Exception as e:
        log.error(f"Error getting Microsoft Entra ID access token: {e}")
        return None


async def make_gemini_llm_call(
    request_url: str,
    headers: dict,
    cookies: dict,
    base_payload: dict,
    system_prompt: str,
    query: str,
) -> dict:
    """
    Make a non-streaming LLM call to Gemini backend for tool gating Stage 1.

    Args:
        request_url: The Gemini API endpoint URL
        headers: Request headers
        cookies: Request cookies
        base_payload: Base payload dict (will be modified with system prompt)
        system_prompt: System prompt to use
        query: User query (already in messages)

    Returns:
        dict with 'success' and 'text' (or 'error') keys
    """
    try:
        # Create a copy of the payload for Stage 1
        payload = copy.deepcopy(base_payload)

        # Ensure stream is False for Stage 1
        payload["stream"] = False

        # Update system prompt in messages
        if payload.get("messages") and len(payload["messages"]) > 0:
            if payload["messages"][0].get("role") == "system":
                payload["messages"][0]["content"] = system_prompt
            else:
                # Insert system message at the beginning
                payload["messages"].insert(0, {
                    "role": "system",
                    "content": system_prompt
                })

        payload_json = json.dumps(payload)

        log.info(f"[OPENAI-TOOL-GATING] Making LLM call to: {request_url}")
        log.info(f"[OPENAI-TOOL-GATING] System prompt length: {len(system_prompt)} chars")

        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.post(
                request_url,
                data=payload_json,
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                if r.status >= 400:
                    error_text = await r.text()
                    log.error(f"[OPENAI-TOOL-GATING] LLM call failed: {r.status} - {error_text}")
                    return {"success": False, "error": f"HTTP {r.status}: {error_text}"}

                response = await r.json()

                # Extract text from OpenAI-compatible response format
                text = ""
                if response.get("choices") and len(response["choices"]) > 0:
                    choice = response["choices"][0]
                    if choice.get("message"):
                        text = choice["message"].get("content", "")
                    elif choice.get("text"):
                        text = choice["text"]

                log.info(f"[OPENAI-TOOL-GATING] LLM response received: {len(text)} chars")
                return {"success": True, "text": text}

    except Exception as e:
        log.error(f"[OPENAI-TOOL-GATING] LLM call exception: {e}")
        return {"success": False, "error": str(e)}


async def make_gemini_native_call_with_cache(
    api_key: str,
    model: str,
    system_prompt: str,
    query: str,
    cache_stage: Optional[str] = None,
    cache_manager: Optional[GeminiCacheManager] = None,
    temperature: float = 0.2,
) -> dict:
    """
    Make a non-streaming LLM call using Gemini native API with caching support.

    Args:
        api_key: Gemini API key
        model: Model ID (e.g., "gemini-2.5-flash")
        system_prompt: System prompt to use
        query: User query
        cache_stage: Optional cache stage ("gating" or "execution")
        cache_manager: Optional GeminiCacheManager instance
        temperature: Sampling temperature

    Returns:
        dict with 'success' and 'text' (or 'error') keys
    """
    try:
        from google import genai
        from google.genai import types

        log.info(f"[GEMINI-NATIVE-CACHE] Making LLM call with native API")
        log.info(f"  Model: {model}")
        log.info(f"  System prompt length: {len(system_prompt)} chars")
        log.info(f"  Cache stage: {cache_stage}")
        log.info(f"  Cache manager: {'SET' if cache_manager else 'NONE'}")

        # Create Gemini client
        client = genai.Client(api_key=api_key)

        # Get or create cache if cache_stage provided
        cached_content_name = None
        if cache_stage and cache_manager and system_prompt:
            cached_content_name = cache_manager.get_or_create_cache(
                model_id=model,
                system_prompt=system_prompt,
                stage=cache_stage
            )
            if cached_content_name:
                log.info(f"[GEMINI-NATIVE-CACHE] Using global cache: {cached_content_name}")

        # Build config
        config = types.GenerateContentConfig(
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,          # Enable automatic function calling
                maximum_remote_calls=5  # Limit to 5 calls (default is 10)
            )
        )

        # Use cached content OR system_instruction
        if cached_content_name:
            config.cached_content = cached_content_name
        elif system_prompt:
            config.system_instruction = system_prompt

        # Call Gemini native API
        response = client.models.generate_content(
            model=model,
            contents=query,
            config=config
        )

        # Extract text from native API response
        text = response.text if hasattr(response, 'text') else ""

        log.info(f"[GEMINI-NATIVE-CACHE] Response received: {len(text)} chars")
        return {"success": True, "text": text}

    except Exception as e:
        log.error(f"[GEMINI-NATIVE-CACHE] Call exception: {e}")
        log.exception(e)
        return {"success": False, "error": str(e)}


def get_or_create_gemini_cache_manager(request: Request, api_key: str) -> GeminiCacheManager:
    """
    Get or create a GeminiCacheManager for the given API key.
    Cache managers are stored in app.state per API key.

    Args:
        request: FastAPI request object
        api_key: Gemini API key

    Returns:
        GeminiCacheManager instance
    """
    from google import genai

    # Initialize cache managers dict if not exists
    if not hasattr(request.app.state, "gemini_cache_managers"):
        request.app.state.gemini_cache_managers = {}

    # Create cache manager if not exists for this API key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    if key_hash not in request.app.state.gemini_cache_managers:
        log.info(f"[CACHE] Creating new GeminiCacheManager for key: {key_hash}")
        client = genai.Client(api_key=api_key)
        request.app.state.gemini_cache_managers[key_hash] = GeminiCacheManager(client)

    return request.app.state.gemini_cache_managers[key_hash]


def convert_openai_messages_to_gemini_contents(messages: list) -> list:
    """
    Convert OpenAI-format messages to Gemini contents format.

    OpenAI format:
        [
            {"role": "system", "content": "..."},  # Excluded (use system_instruction)
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]

    Gemini format:
        [
            {"role": "user", "parts": [{"text": "Hello"}]},
            {"role": "model", "parts": [{"text": "Hi there"}]},
            {"role": "user", "parts": [{"text": "How are you?"}]}
        ]

    Args:
        messages: OpenAI-format messages list

    Returns:
        Gemini-format contents list
    """
    contents = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        # Skip system messages (handled by system_instruction)
        if role == "system":
            continue

        # Convert role: assistant → model
        gemini_role = "model" if role == "assistant" else role

        # Extract text content
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Handle multimodal content - extract text parts
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            text = "\n".join(text_parts) if text_parts else ""
        else:
            text = str(content)

        if text:  # Only add non-empty messages
            contents.append({
                "role": gemini_role,
                "parts": [{"text": text}]
            })

    return contents


async def handle_gemini_native_request(
    request: Request,
    api_key: str,
    model_id: str,
    payload: dict,
    final_system: Optional[str],
    cache_stage: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Handle chat completion request using unified Gemini service.

    This function routes all Gemini requests to GeminiRAGService for unified handling.
    Regular chat (no RAG) is handled by passing empty store_names.

    Args:
        request: FastAPI request object
        api_key: Gemini API key
        model_id: Model ID (e.g., "gemini-2.5-flash")
        payload: OpenAI-format payload with messages
        final_system: Final system prompt (may be cached)
        cache_stage: Optional cache stage ("execution", "gating", etc.)
        metadata: Optional metadata dict (for inline tool execution)

    Returns:
        OpenAI-compatible response dict or StreamingResponse
    """
    try:
        from open_webui.utils.gemini_rag import get_gemini_rag_service
        from open_webui.utils.misc import openai_chat_chunk_message_template

        log.info("=" * 80)
        log.info("[GEMINI-NATIVE] Routing to unified GeminiRAGService")
        log.info(f"  Model: {model_id}")
        log.info(f"  Cache stage: {cache_stage}")
        log.info(f"  System prompt length: {len(final_system) if final_system else 0} chars")
        log.info("=" * 80)

        # Convert OpenAI messages to Gemini contents (preserves conversation history)
        messages = payload.get("messages", [])
        gemini_contents = convert_openai_messages_to_gemini_contents(messages)

        if not gemini_contents:
            return {
                "error": {
                    "message": "No valid messages found in request",
                    "type": "invalid_request_error",
                    "code": "no_messages"
                }
            }

        log.info(f"[GEMINI-NATIVE] Converted {len(messages)} OpenAI messages to {len(gemini_contents)} Gemini contents")
        if gemini_contents:
            last_msg = gemini_contents[-1]
            if last_msg.get("parts"):
                preview = last_msg["parts"][0].get("text", "")[:100]
                log.info(f"[GEMINI-NATIVE] Last message preview: {preview}...")

        # Store metadata in request state for middleware access
        if metadata:
            if not hasattr(request.state, "_metadata"):
                request.state._metadata = {}
            request.state._metadata.update(metadata)
            log.info(f"[GEMINI-NATIVE] Metadata stored in request.state: {list(metadata.keys())}")

        # Get unified Gemini service
        service = get_gemini_rag_service(api_key)

        # Extract temperature and streaming flag from payload
        temperature = payload.get("temperature", 0.2)
        stream = payload.get("stream", False)

        # Handle streaming requests
        if stream:
            log.info("[GEMINI-NATIVE] Streaming mode enabled")

            async def stream_generator():
                """Generate OpenAI-compatible SSE chunks from Gemini stream"""
                try:
                    # Call streaming service with conversation history
                    async for chunk_text in service.query_stream(
                        contents=gemini_contents,  # Full conversation history
                        store_names=[],  # Empty = no RAG, just regular chat
                        model=model_id,
                        temperature=temperature,
                        system_instruction=final_system,
                        cache_stage=cache_stage
                    ):
                        # Format as OpenAI chunk
                        chunk_data = openai_chat_chunk_message_template(
                            model=model_id,
                            content=chunk_text
                        )
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    # Send final chunk with finish_reason
                    final_chunk = openai_chat_chunk_message_template(
                        model=model_id,
                        content=None  # No content = finish
                    )
                    yield f"data: {json.dumps(final_chunk)}\n\n"

                    # Send [DONE] marker
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    log.error(f"[GEMINI-NATIVE] Streaming error: {e}")
                    log.exception(e)
                    error_chunk = {
                        "error": {
                            "message": str(e),
                            "type": "api_error",
                            "code": "streaming_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

        # Non-streaming mode
        else:
            # Call unified service with conversation history
            # IMPORTANT: Empty store_names = regular chat (no RAG)
            result = service.query(
                contents=gemini_contents,  # Full conversation history
                store_names=[],  # Empty = no RAG, just regular chat
                model=model_id,
                temperature=temperature,
                system_instruction=final_system,
                cache_stage=cache_stage
            )

            if not result.get("success"):
                return {
                    "error": {
                        "message": result.get("error", "Unknown error"),
                        "type": "api_error",
                        "code": "gemini_service_error"
                    }
                }

            text = result.get("text", "")
            log.info(f"[GEMINI-NATIVE] Response received: {len(text)} chars")

            # Convert to OpenAI format
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,  # Gemini doesn't provide this
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

    except Exception as e:
        log.error(f"[GEMINI-NATIVE] Request handling error: {e}")
        log.exception(e)
        return {
            "error": {
                "message": str(e),
                "type": "api_error",
                "code": "gemini_native_error"
            }
        }


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
@get_role_based_limit
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post("/config/update")
@get_write_operation_limit
async def update_config(
    request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.OPENAI_API_KEYS) != len(
        request.app.state.config.OPENAI_API_BASE_URLS
    ):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(
            request.app.state.config.OPENAI_API_BASE_URLS
        ):
            request.app.state.config.OPENAI_API_KEYS = (
                request.app.state.config.OPENAI_API_KEYS[
                    : len(request.app.state.config.OPENAI_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS)
                - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.OPENAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post("/audio/speech")
@get_write_operation_limit
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = request.app.state.config.OPENAI_API_BASE_URLS.index(
            "https://api.openai.com/v1"
        )

        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = CACHE_DIR / "audio" / "speech"
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
        file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
        key = request.app.state.config.OPENAI_API_KEYS[idx]
        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        headers, cookies = await get_headers_and_cookies(
            request, url, key, api_config, user=user
        )

        r = None
        try:
            r = requests.post(
                url=f"{url}/audio/speech",
                data=body,
                headers=headers,
                cookies=cookies,
                stream=True,
            )

            r.raise_for_status()

            # Save the streaming content to a file
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            with open(file_body_path, "w") as f:
                json.dump(json.loads(body.decode("utf-8")), f)

            # Return the saved file
            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error']}"
                except Exception:
                    detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.OPENAI_API_KEYS[:num_urls]
            request.app.state.config.OPENAI_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.OPENAI_API_CONFIGS) and (
            url not in request.app.state.config.OPENAI_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.OPENAI_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
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
                            request.app.state.config.OPENAI_API_KEYS[idx],
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
                                "owned_by": "openai",
                                "openai": {"id": model_id},
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
            url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
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
                # Remove name key if its value is None #16689
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
    key=lambda _, user: f"openai_all_models_{user.id}" if user else "openai_all_models",
)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def is_supported_openai_models(model_id):
        if any(
            name in model_id
            for name in [
                "babbage",
                "dall-e",
                "davinci",
                "embedding",
                "tts",
                "whisper",
            ]
        ):
            return False
        return True

    def get_merged_models(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        models = {}

        for idx, model_list in enumerate(model_lists):
            if model_list is not None and "error" not in model_list:
                for model in model_list:
                    model_id = model.get("id") or model.get("name")

                    if (
                        "api.openai.com"
                        in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                        and not is_supported_openai_models(model_id)
                    ):
                        # Skip unwanted OpenAI models
                        continue

                    if model_id and model_id not in models:
                        models[model_id] = {
                            **model,
                            "name": model.get("name", model_id),
                            "owned_by": "openai",
                            "openai": model,
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }

        return models

    models = get_merged_models(map(extract_data, responses))
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = models
    return {"data": list(models.values())}


@router.get("/models")
@router.get("/models/{url_idx}")
@get_role_based_limit
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = request.app.state.config.OPENAI_API_KEYS[url_idx]

        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(url_idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        r = None
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                headers, cookies = await get_headers_and_cookies(
                    request, url, key, api_config, user=user
                )

                if api_config.get("azure", False):
                    models = {
                        "data": api_config.get("model_ids", []) or [],
                        "object": "list",
                    }
                else:
                    async with session.get(
                        f"{url}/models",
                        headers=headers,
                        cookies=cookies,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as r:
                        if r.status != 200:
                            # Extract response error details if available
                            error_detail = f"HTTP Error: {r.status}"
                            res = await r.json()
                            if "error" in res:
                                error_detail = f"External Error: {res['error']}"
                            raise Exception(error_detail)

                        response_data = await r.json()

                        # Check if we're calling OpenAI API based on the URL
                        if "api.openai.com" in url:
                            # Filter models according to the specified conditions
                            response_data["data"] = [
                                model
                                for model in response_data.get("data", [])
                                if not any(
                                    name in model["id"]
                                    for name in [
                                        "babbage",
                                        "dall-e",
                                        "davinci",
                                        "embedding",
                                        "tts",
                                        "whisper",
                                    ]
                                )
                            ]

                        models = response_data
            except aiohttp.ClientError as e:
                # ClientError covers all aiohttp requests issues
                log.exception(f"Client error: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Open WebUI: Server Connection Error"
                )
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                error_detail = f"Unexpected error: {str(e)}"
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role in {"user", "professor"} and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str

    config: Optional[dict] = None


@router.post("/verify")
@get_write_operation_limit
async def verify_connection(
    request: Request,
    form_data: ConnectionVerificationForm,
    user=Depends(get_admin_user),
):
    url = form_data.url
    key = form_data.key

    api_config = form_data.config or {}

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            headers, cookies = await get_headers_and_cookies(
                request, url, key, api_config, user=user
            )

            if api_config.get("azure", False):
                # Only set api-key header if not using Azure Entra ID authentication
                auth_type = api_config.get("auth_type", "bearer")
                if auth_type not in ("azure_ad", "microsoft_entra_id"):
                    headers["api-key"] = key

                api_version = api_config.get("api_version", "") or "2023-03-15-preview"
                async with session.get(
                    url=f"{url}/openai/models?api-version={api_version}",
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    try:
                        response_data = await r.json()
                    except Exception:
                        response_data = await r.text()

                    if r.status != 200:
                        if isinstance(response_data, (dict, list)):
                            return JSONResponse(
                                status_code=r.status, content=response_data
                            )
                        else:
                            return PlainTextResponse(
                                status_code=r.status, content=response_data
                            )

                    return response_data
            else:
                async with session.get(
                    f"{url}/models",
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    try:
                        response_data = await r.json()
                    except Exception:
                        response_data = await r.text()

                    if r.status != 200:
                        if isinstance(response_data, (dict, list)):
                            return JSONResponse(
                                status_code=r.status, content=response_data
                            )
                        else:
                            return PlainTextResponse(
                                status_code=r.status, content=response_data
                            )

                    return response_data

        except aiohttp.ClientError as e:
            # ClientError covers all aiohttp requests issues
            log.exception(f"Client error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )


def get_azure_allowed_params(api_version: str) -> set[str]:
    allowed_params = {
        "messages",
        "temperature",
        "role",
        "content",
        "contentPart",
        "contentPartImage",
        "enhancements",
        "dataSources",
        "n",
        "stream",
        "stop",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "user",
        "function_call",
        "functions",
        "tools",
        "tool_choice",
        "top_p",
        "log_probs",
        "top_logprobs",
        "response_format",
        "seed",
        "max_completion_tokens",
        "reasoning_effort",
    }

    try:
        if api_version >= "2024-09-01-preview":
            allowed_params.add("stream_options")
    except ValueError:
        log.debug(
            f"Invalid API version {api_version} for Azure OpenAI. Defaulting to allowed parameters."
        )

    return allowed_params


def is_openai_reasoning_model(model: str) -> bool:
    return model.lower().startswith(("o1", "o3", "o4", "gpt-5"))


def convert_to_azure_payload(url, payload: dict, api_version: str):
    model = payload.get("model", "")

    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = get_azure_allowed_params(api_version)

    # Special handling for o-series models
    if is_openai_reasoning_model(model):
        # Convert max_tokens to max_completion_tokens for o-series models
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]

        # Remove temperature if not 1 for o-series models
        if "temperature" in payload and payload["temperature"] != 1:
            log.debug(
                f"Removing temperature parameter for o-series model {model} as only default value (1) is supported"
            )
            del payload["temperature"]

    # Filter out unsupported parameters
    payload = {k: v for k, v in payload.items() if k in allowed_params}

    url = f"{url}/openai/deployments/{model}"
    return url, payload


@router.post("/chat/completions")
@get_role_based_limit
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

    # Initialize variables for tool handling (may be updated in model_info block)
    base_system = None
    tool_prompts = []

    # Check model info and override the payload
    # Model-level settings for tool handling
    model_tool_mode = None  # "gating" | "concat" | "none" | None
    tool_gating_model = None  # Optional: Model for Stage 1 tool gating

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()
        meta = model_info.meta.model_dump() if model_info.meta else {}

        # Extract tool_mode and prompt_group_id from meta (model settings)
        model_tool_mode = meta.get("tool_mode")  # "gating" | "concat" | "none" | None
        tool_gating_model = meta.get("tool_gating_model")  # Optional: Flash model for Stage 1 tool gating
        prompt_group_id_from_meta = meta.get("prompt_group_id")

        # Extract system and prompt_group_id from params (legacy support)
        system = None
        prompt_group_id_from_params = None
        if params:
            system = params.pop("system", None)
            prompt_group_id_from_params = params.pop("prompt_group_id", None)

        # Priority: meta.prompt_group_id > params.prompt_group_id
        prompt_group_id = prompt_group_id_from_meta or prompt_group_id_from_params

        log.info(f"[OPENAI] Model settings - tool_mode: {model_tool_mode}, tool_gating_model: {tool_gating_model}, prompt_group_id: {prompt_group_id}")

        # Always try to compose prompts (even if params is None)
        # Get persona values from metadata (stored in chat)
        proficiency_level = metadata.get("proficiency_level") if metadata else None
        response_style = metadata.get("response_style") if metadata else None

        # Compose prompts with fallback logic
        # Priority: prompt_group_id > system > DEFAULT_PROMPT_GROUP_ID > none
        # Note: First compose without tools, then decide based on tool_mode
        composed_system, tool_prompts = compose_with_fallback(
            group_id=prompt_group_id,
            system_prompt=system,
            default_group_id=getattr(
                request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
            ),
            proficiency_level=proficiency_level,
            response_style=response_style,
            include_tools=False,  # Don't auto-include tools, decide based on tool_mode
        )

        # Store base system for later use (tool handling done after URL resolution)
        base_system = composed_system if composed_system else system

        # Apply model params to payload (only if params exist)
        if params:
            payload = apply_model_params_to_body_openai(params, payload)

        # Note: System prompt application is deferred until after URL resolution
        # to determine if we should use tool gating (Gemini) or legacy mode (others)

        # Check if user has access to the model
        if not bypass_filter and user.role in {"user", "professor"}:
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    await get_all_models(request, user=user)
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # Add user info to the payload if the model is a pipeline
    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Determine backend type
    is_gemini_backend = "generativelanguage.googleapis.com" in url

    # Get headers and cookies early (needed for tool gating Stage 1)
    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, metadata, user=user
    )

    # Build request URL early
    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        azure_url, _ = convert_to_azure_payload(url, payload.copy(), api_version)

        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get("auth_type", "bearer")
        if auth_type not in ("azure_ad", "microsoft_entra_id"):
            headers["api-key"] = key

        headers["api-version"] = api_version
        request_url = f"{azure_url}/chat/completions?api-version={api_version}"
    else:
        request_url = f"{url}/chat/completions"

    # Tool handling based on backend type
    # Gemini backend: use FULL two-stage tool gating
    # Other backends: legacy mode (include full tool content)

    final_system = base_system

    # Detect utility requests that should skip tool gating (e.g., title generation)
    # These are identified by:
    # 1. metadata.task == "title_generation" or similar
    # 2. System prompt containing title generation keywords
    # 3. Short utility calls that don't need tool selection
    is_utility_request = False
    if metadata:
        task_type = metadata.get("task", "")
        if task_type in ("title_generation", "summary", "title"):
            is_utility_request = True
            log.info(f"[OPENAI] Utility request detected (task={task_type}), skipping tool gating")

    # Also check system prompt for title generation patterns
    if not is_utility_request and base_system:
        title_keywords = ["title", "제목", "generate a title", "Create a concise"]
        if any(keyword.lower() in base_system.lower() for keyword in title_keywords):
            is_utility_request = True
            log.info("[OPENAI] Title generation detected in system prompt, skipping tool gating")

    # Determine tool handling mode based on model settings
    # Priority: model_tool_mode > default behavior
    # - "gating": two-stage tool gating (select tools first, then generate)
    # - "concat": include all tool prompts in system prompt (legacy mode)
    # - "none": no tool prompts included
    # - "inline" or None: inline tool execution with short hints (default)
    effective_tool_mode = model_tool_mode if model_tool_mode else "inline"

    log.info("=" * 80)
    log.info(f"[OPENAI] Tool handling mode: {effective_tool_mode} (model_tool_mode={model_tool_mode})")
    log.info(f"[OPENAI] Available tools: {[t.command for t in tool_prompts]}")
    log.info("=" * 80)

    if is_utility_request:
        # Utility requests skip tool handling
        log.info("[OPENAI] Utility request - skipping tool handling")
        effective_tool_mode = "none"

    if effective_tool_mode == "gating" and tool_prompts:
        # Two-stage tool gating: select tools first, then generate with selected tools
        log.info(f"[OPENAI-TOOL-GATING] Starting two-stage tool gating")

        # Extract user query from messages (last user message)
        user_query = ""
        for msg in reversed(payload.get("messages", [])):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_query = content
                elif isinstance(content, list):
                    # Handle multimodal content
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            user_query = part.get("text", "")
                            break
                break

        log.info(f"[OPENAI-TOOL-GATING] User query: {user_query[:100]}...")

        # Stage 1: Tool selection with catalog + JSON instructions
        tool_catalog = build_tool_catalog(tool_prompts)
        stage1_system = build_tool_selection_system_prompt(base_system or "", tool_catalog)

        log.info(f"[OPENAI-TOOL-GATING] Stage 1 System Prompt Length: {len(stage1_system)} chars")

        # Make Stage 1 call
        # Use Gemini native API with cache if Gemini backend, otherwise OpenAI-compatible API
        # Use tool_gating_model if configured, otherwise use main model
        stage1_model = tool_gating_model if tool_gating_model else payload["model"]
        log.info(f"[OPENAI-TOOL-GATING] Stage 1 model: {stage1_model} (tool_gating_model={tool_gating_model})")

        if is_gemini_backend:
            log.info("[OPENAI-TOOL-GATING] Using Gemini native API for Stage 1")
            cache_manager = get_or_create_gemini_cache_manager(request, key)
            stage1_result = await make_gemini_native_call_with_cache(
                api_key=key,
                model=stage1_model,  # Use tool_gating_model if available
                system_prompt=stage1_system,
                query=user_query,
                cache_stage="gating",
                cache_manager=cache_manager,
                temperature=payload.get("temperature", 0.2),
            )
        else:
            log.info("[OPENAI-TOOL-GATING] Using OpenAI-compatible API for Stage 1")
            stage1_payload = payload.copy()
            stage1_payload["model"] = stage1_model  # Use tool_gating_model if available
            stage1_result = await make_gemini_llm_call(
                request_url=request_url,
                headers=headers.copy(),
                cookies=cookies,
                base_payload=stage1_payload,
                system_prompt=stage1_system,
                query=user_query,
            )

        if not stage1_result.get("success"):
            log.error(f"[OPENAI-TOOL-GATING] Stage 1 failed: {stage1_result.get('error')}")
            # Fallback: use base system without tools
            final_system = base_system
        else:
            stage1_text = stage1_result.get("text", "")
            log.info(f"[OPENAI-TOOL-GATING] Stage 1 response: {stage1_text[:300]}...")

            # Parse tool selection
            selected_tools, direct_answer = parse_tool_selection_response(stage1_text)

            if not selected_tools:
                # No tools needed - proceed to Stage 2 with base system only
                log.info("[OPENAI-TOOL-GATING] No tools needed, proceeding with base system only")
                final_system = base_system
            else:
                # Stage 2: Use selected tools' full content
                log.info(f"[OPENAI-TOOL-GATING] Stage 2 - Tools selected: {selected_tools}")

                selected_tool_prompts = get_tool_prompts_by_commands(tool_prompts, selected_tools)
                final_system = compose_stage2_system_prompt(base_system or "", selected_tool_prompts)

                log.info(f"[OPENAI-TOOL-GATING] Stage 2 System Prompt Length: {len(final_system)} chars")
                log.info(f"[OPENAI-TOOL-GATING] Selected tools: {[t.command for t in selected_tool_prompts]}")

                # Enable inline tool execution for Stage 2 (for streaming with tool markers)
                if metadata is None:
                    metadata = {}
                metadata["enable_tool_notifications"] = True
                metadata["tool_commands"] = {t.command for t in selected_tool_prompts}
                metadata["tool_prompts_dict"] = {
                    t.command.lstrip('/'): t.content for t in selected_tool_prompts
                }
                metadata["tool_validation_rules"] = {
                    t.command.lstrip('/'): t.validation_rules
                    for t in selected_tool_prompts
                    if t.prompt_type == "json_tool" and t.validation_rules
                }
                metadata["api_request_url"] = request_url
                metadata["api_headers"] = dict(headers)
                metadata["api_cookies"] = dict(cookies) if cookies else {}

                # Pass Gemini info for native SDK usage in inline tool execution
                metadata["is_gemini_backend"] = is_gemini_backend
                if is_gemini_backend:
                    metadata["gemini_api_key"] = key
                    metadata["gemini_model_id"] = payload["model"]
                    # Use tool_gating_model (Flash) for tool execution if configured
                    metadata["gemini_tool_model"] = tool_gating_model if tool_gating_model else payload["model"]
                    log.info(f"[OPENAI-TOOL-GATING] Stage 2 inline tool execution will use Gemini native SDK")
                    log.info(f"[OPENAI-TOOL-GATING] Tool execution model: {metadata['gemini_tool_model']}")

                log.info(f"[OPENAI-TOOL-GATING] Stage 2 inline tool execution enabled for: {metadata['tool_commands']}")
                log.info(f"[OPENAI-TOOL-GATING] Tool prompts dict keys: {list(metadata['tool_prompts_dict'].keys())}")

                # Store metadata in form_data for middleware access
                form_data["metadata"] = metadata
                log.info(f"[OPENAI-TOOL-GATING] Updated metadata stored in form_data")

    elif effective_tool_mode == "concat" and tool_prompts:
        # Legacy mode: include all tool prompts in system prompt
        final_system = compose_stage2_system_prompt(base_system or "", tool_prompts)
        log.info(f"[OPENAI] Concat mode: all {len(tool_prompts)} tool prompts included")
        log.info(f"[OPENAI] Final system prompt length: {len(final_system)} chars")

    elif effective_tool_mode == "none" or not tool_prompts:
        # No tools mode: just use base system
        final_system = base_system
        log.info(f"[OPENAI] No tools mode: base system only")

    else:
        # Default: Inline tool execution mode with short hints
        # When tool markers are detected in stream, ToolInlineExecutor will call LLM with full prompt
        tool_hints = build_tool_hints(tool_prompts)
        final_system = f"{base_system}\n\n{tool_hints}" if base_system else tool_hints
        log.info(f"[OPENAI] Inline tool execution mode with {len(tool_prompts)} tools (short hints)")
        log.info(f"[OPENAI] Tool hints length: {len(tool_hints)} chars")

    # Enable inline tool execution for streaming if using inline mode
    if effective_tool_mode == "inline" and tool_prompts:
        if metadata is None:
            metadata = {}
        metadata["enable_tool_notifications"] = True
        metadata["tool_commands"] = {t.command for t in tool_prompts}
        # Pass full tool prompts dict for inline execution
        metadata["tool_prompts_dict"] = {
            t.command.lstrip('/'): t.content for t in tool_prompts
        }
        # Pass validation rules for json_tool types
        metadata["tool_validation_rules"] = {
            t.command.lstrip('/'): t.validation_rules
            for t in tool_prompts
            if t.prompt_type == "json_tool" and t.validation_rules
        }
        # Pass API info for inline LLM calls
        metadata["api_request_url"] = request_url
        metadata["api_headers"] = dict(headers)
        metadata["api_cookies"] = dict(cookies) if cookies else {}

        # Pass Gemini info for native SDK usage in inline tool execution
        metadata["is_gemini_backend"] = is_gemini_backend
        if is_gemini_backend:
            metadata["gemini_api_key"] = key
            metadata["gemini_model_id"] = payload["model"]
            # Use tool_gating_model (Flash) for tool execution if configured
            metadata["gemini_tool_model"] = tool_gating_model if tool_gating_model else payload["model"]
            log.info(f"[OPENAI] Inline tool execution will use Gemini native SDK")
            log.info(f"[OPENAI] Tool execution model: {metadata['gemini_tool_model']}")

        log.info(f"[OPENAI] Inline tool execution enabled for: {metadata['tool_commands']}")
        log.info(f"[OPENAI] Tool prompts dict keys: {list(metadata['tool_prompts_dict'].keys())}")
        log.info(f"[OPENAI] Tool validation rules keys: {list(metadata['tool_validation_rules'].keys())}")

        # Store updated metadata back in form_data for middleware access
        form_data["metadata"] = metadata
        log.info(f"[OPENAI] Updated metadata stored in form_data")

    # Apply system prompt to payload
    payload = apply_system_prompt_to_body(final_system, payload, metadata, user)

    # Debug: Log the final system prompt being sent
    log.info("=" * 80)
    log.info(f"[OPENAI] Final system prompt length: {len(final_system) if final_system else 0} chars")
    log.info(f"[OPENAI] Backend URL: {url}")
    log.info(f"[OPENAI] Is Gemini backend: {is_gemini_backend}")
    log.info(f"[OPENAI] Tool prompts count: {len(tool_prompts)}")
    log.info(f"[OPENAI] Inline tool execution: {tool_prompts and not is_utility_request}")
    log.info("=" * 80)

    # CRITICAL: If Gemini backend, use native SDK for ALL requests
    # This enables context caching and improves performance
    if is_gemini_backend:
        log.info("[OPENAI] Gemini backend detected - routing to native SDK")

        # Determine cache stage based on tool mode
        # - "gating" mode: Stage 1 already used "gating" cache, Stage 2 uses "execution" cache
        # - "concat" mode: uses "execution" cache (includes all tools)
        # - "none"/"inline" mode: uses "execution" cache (no tools or short hints)
        cache_stage = "execution"

        # Use tool_gating_model (Flash) for inline mode to improve speed
        selected_model = payload["model"]
        if effective_tool_mode == "inline" and tool_gating_model:
            selected_model = tool_gating_model
            log.info(f"[OPENAI] Inline mode: using Flash model for first call: {selected_model}")

        return await handle_gemini_native_request(
            request=request,
            api_key=key,
            model_id=selected_model,
            payload=payload,
            final_system=final_system,
            cache_stage=cache_stage,
            metadata=metadata,
        )

    # For non-Gemini backends, continue with OpenAI-compatible flow
    log.info("[OPENAI] Using OpenAI-compatible API flow")

    # Check if model is a reasoning model that needs special handling
    if is_openai_reasoning_model(payload["model"]):
        payload = openai_reasoning_model_handler(payload)
    elif "api.openai.com" not in url:
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    if "max_tokens" in payload and "max_completion_tokens" in payload:
        del payload["max_tokens"]

    # Convert the modified body back to JSON
    if "logit_bias" in payload:
        payload["logit_bias"] = json.loads(
            convert_logit_bias_input_to_json(payload["logit_bias"])
        )

    # Re-apply Azure conversion if needed (payload was modified)
    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        request_url, payload = convert_to_azure_payload(url, payload, api_version)
        request_url = f"{request_url}/chat/completions?api-version={api_version}"

    payload = json.dumps(payload)

    r = None
    session = None
    streaming = False
    response = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.request(
            method="POST",
            url=request_url,
            data=payload,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            # Filter out encoding headers to prevent ERR_CONTENT_DECODING_FAILED
            # aiohttp already handles decompression, so we shouldn't pass these headers
            filtered_headers = {
                k: v for k, v in r.headers.items()
                if k.lower() not in ('content-encoding', 'transfer-encoding', 'content-length')
            }
            return StreamingResponse(
                stream_chunks_handler(r.content),
                status_code=r.status,
                headers=filtered_headers,
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            return response
    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


async def embeddings(request: Request, form_data: dict, user):
    """
    Calls the embeddings endpoint for OpenAI-compatible providers.

    Args:
        request (Request): The FastAPI request context.
        form_data (dict): OpenAI-compatible embeddings payload.
        user (UserModel): The authenticated user.

    Returns:
        dict: OpenAI-compatible embeddings response.
    """
    idx = 0
    # Prepare payload/body
    body = json.dumps(form_data)
    # Find correct backend url/key based on model
    await get_all_models(request, user=user)
    model_id = form_data.get("model")
    models = request.app.state.OPENAI_MODELS
    if model_id in models:
        idx = models[model_id]["urlIdx"]

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, user=user
    )
    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method="POST",
            url=f"{url}/embeddings",
            data=body,
            headers=headers,
            cookies=cookies,
        )

        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(
                        status_code=r.status, content=response_data
                    )

            return response_data
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Deprecated: proxy all requests to OpenAI API
    """

    body = await request.body()

    idx = 0
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    try:
        headers, cookies = await get_headers_and_cookies(
            request, url, key, api_config, user=user
        )

        if api_config.get("azure", False):
            api_version = api_config.get("api_version", "2023-03-15-preview")

            # Only set api-key header if not using Azure Entra ID authentication
            auth_type = api_config.get("auth_type", "bearer")
            if auth_type not in ("azure_ad", "microsoft_entra_id"):
                headers["api-key"] = key

            headers["api-version"] = api_version

            payload = json.loads(body)
            url, payload = convert_to_azure_payload(url, payload, api_version)
            body = json.dumps(payload).encode()

            request_url = f"{url}/{path}?api-version={api_version}"
        else:
            request_url = f"{url}/{path}"

        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=request_url,
            data=body,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(
                        status_code=r.status, content=response_data
                    )

            return response_data

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


# ============================================================
# Gemini Cache Management API
# ============================================================

@router.get("/gemini/cache/stats")
@get_role_based_limit
async def get_gemini_cache_stats(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Get Gemini global cache statistics.

    Admin only endpoint to monitor cache usage for Gemini native SDK.

    Returns:
        - total_caches: Total number of cached contents
        - max_caches: Maximum allowed caches
        - by_stage: Count of caches by stage (gating/execution)
        - by_model: Count of caches by model ID
        - tool_spec_version: Current tool spec version
    """
    if not hasattr(request.app.state, "gemini_cache_managers"):
        return {
            "status": "ok",
            "total_caches": 0,
            "max_caches": 50,
            "by_stage": {"gating": 0, "execution": 0},
            "by_model": {},
            "tool_spec_version": "v1.0.0",
            "message": "No cache managers initialized yet"
        }

    # Aggregate stats from all cache managers
    total_caches = 0
    by_stage = {"gating": 0, "execution": 0}
    by_model = {}

    for cache_manager in request.app.state.gemini_cache_managers.values():
        stats = cache_manager.get_stats()
        total_caches += stats["total_caches"]
        for stage, count in stats["by_stage"].items():
            by_stage[stage] = by_stage.get(stage, 0) + count
        for model, count in stats["by_model"].items():
            by_model[model] = by_model.get(model, 0) + count

    return {
        "status": "ok",
        "total_caches": total_caches,
        "max_caches": 50,
        "by_stage": by_stage,
        "by_model": by_model,
        "tool_spec_version": "v1.0.0",
        "cache_managers_count": len(request.app.state.gemini_cache_managers)
    }


@router.delete("/gemini/cache")
@get_write_operation_limit
async def clear_all_gemini_caches(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Clear all Gemini cached system prompts.

    Admin only endpoint. Use this when you modify prompts and want to
    force cache regeneration across all cache managers.

    Returns:
        - deleted_count: Number of caches successfully deleted
        - failed_count: Number of caches that failed to delete
        - errors: List of error messages (if any)
    """
    if not hasattr(request.app.state, "gemini_cache_managers"):
        return {
            "status": "ok",
            "deleted_count": 0,
            "failed_count": 0,
            "errors": [],
            "message": "No cache managers initialized yet"
        }

    total_deleted = 0
    total_failed = 0
    all_errors = []

    for key_hash, cache_manager in request.app.state.gemini_cache_managers.items():
        log.info(f"[CACHE] Clearing caches for manager: {key_hash}")
        result = cache_manager.clear_all_caches()
        total_deleted += result["deleted_count"]
        total_failed += result["failed_count"]
        all_errors.extend(result["errors"])

    return {
        "status": "ok",
        "deleted_count": total_deleted,
        "failed_count": total_failed,
        "errors": all_errors,
        "cache_managers_count": len(request.app.state.gemini_cache_managers)
    }


@router.delete("/gemini/cache/{stage}")
@get_write_operation_limit
async def clear_gemini_caches_by_stage(
    request: Request,
    stage: str,
    user=Depends(get_admin_user)
):
    """
    Clear Gemini caches for a specific stage.

    Admin only endpoint. Clears only caches for the specified stage
    (gating or execution) across all cache managers.

    Args:
        stage: Stage to clear ("gating" or "execution")

    Returns:
        - stage: The stage that was cleared
        - deleted_count: Number of caches successfully deleted
        - failed_count: Number of caches that failed to delete
        - errors: List of error messages (if any)
    """
    if stage not in ("gating", "execution"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage}. Must be 'gating' or 'execution'"
        )

    if not hasattr(request.app.state, "gemini_cache_managers"):
        return {
            "status": "ok",
            "stage": stage,
            "deleted_count": 0,
            "failed_count": 0,
            "errors": [],
            "message": "No cache managers initialized yet"
        }

    total_deleted = 0
    total_failed = 0
    all_errors = []

    for key_hash, cache_manager in request.app.state.gemini_cache_managers.items():
        log.info(f"[CACHE] Clearing {stage} caches for manager: {key_hash}")
        result = cache_manager.clear_caches_by_stage(stage)
        total_deleted += result["deleted_count"]
        total_failed += result["failed_count"]
        all_errors.extend(result["errors"])

    return {
        "status": "ok",
        "stage": stage,
        "deleted_count": total_deleted,
        "failed_count": total_failed,
        "errors": all_errors,
        "cache_managers_count": len(request.app.state.gemini_cache_managers)
    }

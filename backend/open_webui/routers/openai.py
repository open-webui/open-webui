import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, Optional, overload, Dict, Any, AsyncGenerator
import fnmatch

import aiohttp
from aiocache import cached
import requests
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
    OPENROUTER_API_KEY,
    OPENROUTER_HOST,
    OPENROUTER_EXTERNAL_USER,
    ORGANIZATION_NAME,
    SPENDING_LIMIT,
)
from open_webui.utils.user_mapping import get_external_user_id, user_mapping_service
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
from open_webui.env import ENV, SRC_LOG_LEVELS


from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access


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


def has_wildcards(model_ids):
    """
    Check if any model ID contains wildcard patterns
    """
    return any('*' in model_id or '?' in model_id for model_id in model_ids)


def filter_models_by_patterns(models, patterns):
    """
    Filter models based on wildcard patterns using fnmatch
    """
    filtered_models = []
    for model in models:
        model_id = model.get('id', '')
        if any(fnmatch.fnmatch(model_id, pattern) for pattern in patterns):
            filtered_models.append(model)
    return filtered_models


def openai_o_series_handler(payload):
    """
    Handle "o" series specific parameters
    """
    if "max_tokens" in payload:
        # Convert "max_tokens" to "max_completion_tokens" for all o-series models
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


class UsageCapturingStreamingResponse:
    """
    Custom streaming response class that captures usage data from the final SSE chunk
    while preserving normal streaming functionality for the client.
    
    This solves the critical issue where streaming OpenRouter responses were not
    being captured in the usage tracking system, ensuring 100% coverage.
    """
    
    def __init__(
        self,
        content: AsyncGenerator[bytes, None],
        status_code: int,
        headers: Dict[str, str],
        user_id: str,
        model_name: str,
        client_context: Optional[Dict[str, Any]] = None,
        payload: Optional[str] = None,
        background_task: Optional[BackgroundTask] = None
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers
        self.user_id = user_id
        self.model_name = model_name
        self.client_context = client_context
        self.payload = payload
        self.background_task = background_task
        
        # Usage data captured from final SSE chunk
        self.captured_usage = None
        self.last_chunk_data = None
    
    async def parse_sse_chunk(self, chunk_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse SSE (Server-Sent Events) chunk to extract JSON data
        
        SSE format:
        data: {"key": "value"}
        
        Returns:
            Parsed JSON dict if valid, None otherwise
        """
        try:
            chunk_str = chunk_data.decode('utf-8').strip()
            
            # Handle SSE format - look for 'data: ' prefix
            if chunk_str.startswith('data: '):
                json_str = chunk_str[6:]  # Remove 'data: ' prefix
                
                # Skip [DONE] markers and empty data
                if json_str.strip() in ['[DONE]', '']:
                    return None
                
                # Parse JSON
                return json.loads(json_str)
                
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
            log.debug(f"Could not parse SSE chunk: {e}")
            return None
        
        return None
    
    def extract_usage_data(self, parsed_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract usage information from parsed OpenRouter response
        
        OpenRouter returns usage data in the final SSE chunk when usage: {include: true} is set
        """
        try:
            if not isinstance(parsed_data, dict):
                return None
            
            # Check for usage data in the response
            usage_data = parsed_data.get('usage')
            if not usage_data:
                return None
            
            # Extract required fields
            input_tokens = usage_data.get('prompt_tokens', 0)
            output_tokens = usage_data.get('completion_tokens', 0)
            
            # Extract cost - OpenRouter provides this when usage accounting is enabled
            raw_cost = 0.0
            if isinstance(usage_data, dict) and 'cost' in usage_data:
                raw_cost = float(usage_data['cost'])
            elif 'cost' in parsed_data:
                raw_cost = float(parsed_data['cost'])
            elif 'total_cost' in usage_data:
                raw_cost = float(usage_data['total_cost'])
            
            # Extract additional metadata
            provider = None
            provider_info = parsed_data.get('provider')
            if isinstance(provider_info, dict):
                provider = provider_info.get('name')
            
            generation_time = parsed_data.get('generation_time')
            external_user = parsed_data.get('external_user')
            generation_id = parsed_data.get('generation_id') or parsed_data.get('id')
            
            return {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'raw_cost': raw_cost,
                'provider': provider,
                'generation_time': generation_time,
                'external_user': external_user,
                'generation_id': generation_id
            }
            
        except (ValueError, TypeError, KeyError) as e:
            log.debug(f"Error extracting usage data: {e}")
            return None
    
    async def record_usage_async(self, usage_data: Dict[str, Any]):
        """
        Record usage data asynchronously without blocking the streaming response
        """
        try:
            if not self.client_context:
                log.debug("No client context available for usage recording")
                return
            
            from open_webui.utils.openrouter_client_manager import openrouter_client_manager
            
            log.info(f"Recording streaming usage: {usage_data['input_tokens'] + usage_data['output_tokens']} tokens, ${usage_data['raw_cost']:.6f}")
            
            await openrouter_client_manager.record_real_time_usage(
                user_id=self.user_id,
                model_name=self.model_name,
                input_tokens=usage_data['input_tokens'],
                output_tokens=usage_data['output_tokens'],
                raw_cost=usage_data['raw_cost'],
                generation_id=usage_data.get('generation_id'),
                provider=usage_data.get('provider'),
                generation_time=usage_data.get('generation_time'),
                external_user=usage_data.get('external_user'),
                client_context=self.client_context
            )
            
        except Exception as e:
            log.error(f"Failed to record streaming usage for user {self.user_id}: {e}")
    
    async def stream_with_usage_capture(self) -> AsyncGenerator[bytes, None]:
        """
        Stream content while capturing usage data from the final chunk
        """
        buffered_chunks = []
        
        try:
            async for chunk in self.content:
                # Always yield the chunk immediately for real-time streaming
                yield chunk
                
                # Buffer the last few chunks to catch usage data
                buffered_chunks.append(chunk)
                
                # Keep only the last 10 chunks to avoid memory issues
                if len(buffered_chunks) > 10:
                    buffered_chunks.pop(0)
            
            # After streaming is complete, analyze buffered chunks for usage data
            await self.process_buffered_chunks(buffered_chunks)
            
        except Exception as e:
            log.error(f"Error in streaming with usage capture: {e}")
            # Continue streaming even if usage capture fails
            async for chunk in self.content:
                yield chunk
    
    async def process_buffered_chunks(self, chunks: list[bytes]):
        """
        Process the final buffered chunks to find and extract usage data
        """
        try:
            # Process chunks in reverse order (most recent first) to find usage data quickly
            for chunk in reversed(chunks):
                parsed_data = await self.parse_sse_chunk(chunk)
                if parsed_data:
                    usage_data = self.extract_usage_data(parsed_data)
                    if usage_data:
                        # Found usage data - record it asynchronously
                        self.captured_usage = usage_data
                        log.debug(f"Captured usage data from streaming response: {usage_data}")
                        
                        # Record usage in background (don't await to avoid blocking)
                        asyncio.create_task(self.record_usage_async(usage_data))
                        return
            
            log.debug("No usage data found in streaming response chunks")
            
        except Exception as e:
            log.error(f"Error processing buffered chunks for usage data: {e}")


def create_usage_capturing_streaming_response(
    content: AsyncGenerator[bytes, None],
    status_code: int,
    headers: Dict[str, str],
    user_id: str,
    model_name: str,
    client_context: Optional[Dict[str, Any]] = None,
    payload: Optional[str] = None,
    background_task: Optional[BackgroundTask] = None
) -> StreamingResponse:
    """
    Factory function to create a StreamingResponse with usage capture capabilities
    """
    usage_capturer = UsageCapturingStreamingResponse(
        content=content,
        status_code=status_code,
        headers=headers,
        user_id=user_id,
        model_name=model_name,
        client_context=client_context,
        payload=payload,
        background_task=background_task
    )
    
    return StreamingResponse(
        content=usage_capturer.stream_with_usage_capture(),
        status_code=status_code,
        headers=headers,
        background=background_task
    )


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
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

    # Auto-sync OpenRouter API key to user's organization in database
    try:
        # Check if any URL is OpenRouter and sync the corresponding API key
        for idx, base_url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
            if "openrouter.ai" in base_url and idx < len(request.app.state.config.OPENAI_API_KEYS):
                api_key = request.app.state.config.OPENAI_API_KEYS[idx]
                
                # Only sync if there's actually an API key
                if api_key and api_key.strip():
                    from open_webui.utils.openrouter_client_manager import openrouter_client_manager
                    
                    sync_result = openrouter_client_manager.sync_ui_key_to_organization(
                        user_id=user.id,
                        api_key=api_key.strip()
                    )
                    
                    if sync_result["success"]:
                        log.info(f"✅ API key auto-sync: {sync_result['message']} (user: {user.email})")
                    else:
                        # Log the failure but don't prevent config update
                        log.warning(f"⚠️ API key auto-sync failed: {sync_result['message']} (user: {user.email})")
                    
                    # Only sync the first OpenRouter URL found
                    break
                    
    except Exception as e:
        # Log error but don't fail the config update
        log.error(f"❌ API key auto-sync error for user {user.email}: {e}")

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post("/audio/speech")
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

        r = None
        try:
            r = requests.post(
                url=f"{url}/audio/speech",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {request.app.state.config.OPENAI_API_KEYS[idx]}",
                    **(
                        {
                            "HTTP-Referer": "https://openwebui.com/",
                            "X-Title": "Open WebUI",
                        }
                        if "openrouter.ai" in url
                        else {}
                    ),
                    **(
                        {
                            "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS
                        else {}
                    ),
                },
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
            
            # Debug logging
            log.info(f"OpenRouter config for idx {idx}: enable={enable}, model_ids={model_ids}")

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                elif has_wildcards(model_ids):
                    # If model_ids contains wildcards, fetch models and filter
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    # No wildcards, use exact model IDs
                    log.info(f"Using exact model IDs for idx {idx}: {model_ids}")
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
            model_ids = api_config.get("model_ids", [])
            
            # Debug logging for response processing
            log.info(f"Processing response for idx {idx}, URL: {url}")
            log.info(f"Config: {api_config}")
            log.info(f"Response type: {type(response)}, has 'data' key: {'data' in response if isinstance(response, dict) else 'N/A'}")

            # Get the models list
            models = response if isinstance(response, list) else response.get("data", [])
            
            log.info(f"Models count before filtering: {len(models) if models else 0}")
            
            # Filter models if wildcard patterns are present
            if model_ids and has_wildcards(model_ids) and models:
                log.info(f"Filtering models with wildcard patterns: {model_ids}")
                filtered_models = filter_models_by_patterns(models, model_ids)
                log.info(f"Models count after wildcard filtering: {len(filtered_models)}")
                models = filtered_models
                if "data" in response:
                    response["data"] = models
                else:
                    responses[idx] = models

            for model in models:
                if prefix_id:
                    model["id"] = f"{prefix_id}.{model['id']}"

                if tags:
                    model["tags"] = tags

                if connection_type:
                    model["connection_type"] = connection_type

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user):
    """Filter models based on user's organization access"""
    # No admin bypass - all users should see only their organization's models
    
    # Get models accessible through organizations
    from open_webui.models.models import Models
    org_accessible_models = Models.get_models_by_user_id(user.id)
    org_model_ids = {m.id for m in org_accessible_models}
    
    filtered_models = []
    for model in models.get("data", []):
        model_id = model.get("id", "")
        
        # Check if model is in user's organization models
        if model_id in org_model_ids:
            filtered_models.append(model)
            continue
            
        # Legacy check for individual model access
        model_info = Models.get_model_by_id(model_id)
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    
    return filtered_models


@cached(ttl=MODELS_CACHE_TTL)
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
                            "owned_by": "openai",
                            "openai": model,
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }
                        for model in models
                        if (model.get("id") or model.get("name"))
                        and (
                            "api.openai.com"
                            not in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                            or not any(
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
                        )
                    ]
                )

        return merged_list

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = {model["id"]: model for model in models["data"]}
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
                headers = {
                    "Content-Type": "application/json",
                    **(
                        {
                            "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS
                        else {}
                    ),
                }

                if api_config.get("azure", False):
                    models = {
                        "data": api_config.get("model_ids", []) or [],
                        "object": "list",
                    }
                else:
                    headers["Authorization"] = f"Bearer {key}"

                    async with session.get(
                        f"{url}/models",
                        headers=headers,
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

    # Apply filtering for all users (including admins) unless bypass is enabled
    if not BYPASS_MODEL_ACCESS_CONTROL:
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

    api_config = form_data.config or {}

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            headers = {
                "Content-Type": "application/json",
                **(
                    {
                        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            }

            if api_config.get("azure", False):
                headers["api-key"] = key
                api_version = api_config.get("api_version", "") or "2023-03-15-preview"

                async with session.get(
                    url=f"{url}/openai/models?api-version={api_version}",
                    headers=headers,
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
                    return response_data
            else:
                headers["Authorization"] = f"Bearer {key}"

                async with session.get(
                    f"{url}/models",
                    headers=headers,
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
                    return response_data

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
    }

    try:
        if api_version >= "2024-09-01-preview":
            allowed_params.add("stream_options")
    except ValueError:
        log.debug(
            f"Invalid API version {api_version} for Azure OpenAI. Defaulting to allowed parameters."
        )

    return allowed_params


def convert_to_azure_payload(url, payload: dict, api_version: str):
    model = payload.get("model", "")

    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = get_azure_allowed_params(api_version)

    # Special handling for o-series models
    if model.startswith("o") and model.endswith("-mini"):
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

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

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
    
    # Handle OpenRouter client-specific API keys and user tracking
    client_context = None
    if "openrouter.ai" in request.app.state.config.OPENAI_API_BASE_URLS[idx]:
        log.info(f"DEBUG: OpenRouter detected for user {user.id}, model {payload.get('model', 'unknown')}")
        
        # Check if environment-based OpenRouter configuration is available
        if OPENROUTER_API_KEY and OPENROUTER_EXTERNAL_USER:
            log.info(f"DEBUG: Using environment-based OpenRouter configuration for {ORGANIZATION_NAME}")
            key = OPENROUTER_API_KEY
            
            # Generate user-specific external_user_id for proper tracking
            try:
                user_external_id = get_external_user_id(user.id, user.name)
                payload["user"] = user_external_id
                log.info(f"DEBUG: Generated user-specific external_user_id: {user_external_id} for user {user.name}")
            except Exception as e:
                # Fallback to organization-wide ID for backward compatibility
                log.warning(f"Failed to generate user-specific external_user_id: {e}, using fallback")
                payload["user"] = user_mapping_service.get_fallback_external_user_id()
            
            # Enable OpenRouter usage accounting for detailed cost tracking
            payload["usage"] = {"include": True}
            log.info(f"DEBUG: Enabled OpenRouter usage accounting for detailed cost tracking")
            
            # Create client context for usage tracking compatibility
            client_context = {
                "api_key": OPENROUTER_API_KEY,
                "openrouter_user_id": payload["user"],  # Use the generated user ID
                "mai_user_id": user.id,  # Store original mAI user ID
                "mai_user_name": user.name,  # Store user name for logging
                "client_org_id": ORGANIZATION_NAME or "env-client",
                "is_env_based": True,
                "user_mapping_enabled": True
            }
        else:
            # Fallback to database-based client management
            from open_webui.utils.openrouter_client_manager import openrouter_client_manager
            client_context = openrouter_client_manager.get_user_client_context(user.id)
            
            if client_context:
                # Use client-specific API key and add user tracking
                log.info(f"DEBUG: Client context found - using org {client_context['client_org_id']}")
                key = client_context["api_key"]
                payload["user"] = client_context["openrouter_user_id"]
            else:
                # Fallback to original configuration if no client context
                log.warning(f"No client context found for user {user.id}, using default OpenRouter config")
                key = request.app.state.config.OPENAI_API_KEYS[idx]
    else:
        key = request.app.state.config.OPENAI_API_KEYS[idx]

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]

    # Check if model is from "o" series
    is_o_series = payload["model"].lower().startswith(("o1", "o3", "o4"))
    if is_o_series:
        payload = openai_o_series_handler(payload)
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

    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        request_url, payload = convert_to_azure_payload(url, payload, api_version)
        headers["api-key"] = key
        headers["api-version"] = api_version
        request_url = f"{request_url}/chat/completions?api-version={api_version}"
    else:
        request_url = f"{url}/chat/completions"
        headers["Authorization"] = f"Bearer {key}"

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
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            
            # For OpenRouter requests with client context, use usage capturing streaming response
            if client_context and "openrouter.ai" in url:
                log.info(f"Using usage capturing streaming response for user {user.id}")
                return create_usage_capturing_streaming_response(
                    content=r.content,
                    status_code=r.status,
                    headers=dict(r.headers),
                    user_id=user.id,
                    model_name=json.loads(payload).get("model", "unknown"),
                    client_context=client_context,
                    payload=payload,
                    background_task=BackgroundTask(
                        cleanup_response, response=r, session=session
                    )
                )
            else:
                # Standard streaming response for non-OpenRouter or non-tracked requests
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
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            r.raise_for_status()
            
            # Record real-time usage for OpenRouter client requests
            log.info(f"DEBUG: Usage recording check - client_context: {bool(client_context)}, response type: {type(response)}, has usage: {'usage' in response if isinstance(response, dict) else False}")
            if client_context and isinstance(response, dict) and "usage" in response:
                try:
                    log.info(f"DEBUG: Recording usage for user {user.id}")
                    from open_webui.utils.openrouter_client_manager import openrouter_client_manager
                    usage_data = response["usage"]
                    
                    # Extract token counts and cost
                    input_tokens = usage_data.get("prompt_tokens", 0)
                    output_tokens = usage_data.get("completion_tokens", 0)
                    
                    # Get cost from OpenRouter response with usage accounting enabled
                    raw_cost = 0.0
                    if "usage" in response:
                        usage_response = response["usage"]
                        if isinstance(usage_response, dict) and "cost" in usage_response:
                            # OpenRouter usage accounting enabled - structured response
                            raw_cost = float(usage_response["cost"])
                        elif isinstance(usage_response, (int, float)):
                            # OpenRouter usage accounting disabled - simple cost field
                            raw_cost = float(usage_response)
                    elif "cost" in response:
                        raw_cost = float(response["cost"])
                    elif "total_cost" in usage_data:
                        raw_cost = float(usage_data["total_cost"])
                    
                    log.info(f"DEBUG: Usage data - tokens: {input_tokens + output_tokens}, cost: {raw_cost}")
                    
                    # Get provider and timing info with safe access
                    provider = None
                    generation_time = None
                    external_user = None
                    generation_id = None
                    
                    if isinstance(response, dict):
                        provider_info = response.get("provider")
                        if isinstance(provider_info, dict):
                            provider = provider_info.get("name")
                        generation_time = response.get("generation_time")
                        
                        # Capture the external_user from OpenRouter response
                        external_user = response.get("external_user")
                        if external_user and client_context.get("is_temporary_user_id"):
                            log.info(f"DEBUG: Detected external_user from OpenRouter: {external_user}")
                        
                        # Extract generation_id for duplicate prevention
                        # OpenRouter returns generation_id, not just id
                        generation_id = response.get("generation_id") or response.get("id")
                        if generation_id:
                            log.debug(f"OpenRouter generation_id: {generation_id}")
                    
                    # Record usage asynchronously (don't block response)
                    # Always record to database for subscription billing (both env-based and database-based)
                    asyncio.create_task(
                        openrouter_client_manager.record_real_time_usage(
                            user_id=user.id,
                            model_name=json.loads(payload).get("model", "unknown"),
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            raw_cost=raw_cost,
                            generation_id=generation_id,
                            provider=provider,
                            generation_time=generation_time,
                            external_user=external_user,
                            client_context=client_context
                        )
                    )
                    log.info(f"DEBUG: Usage recording task created successfully")
                except Exception as usage_error:
                    log.error(f"Failed to record usage for user {user.id}: {usage_error}")
            else:
                log.info(f"DEBUG: Skipping usage recording - conditions not met")
            
            return response
    except Exception as e:
        log.exception(e)

        detail = None
        if isinstance(response, dict):
            if "error" in response:
                detail = f"{response['error']['message'] if 'message' in response['error'] else response['error']}"
        elif isinstance(response, str):
            detail = response

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "Open WebUI: Server Connection Error",
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
    r = None
    session = None
    streaming = False
    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method="POST",
            url=f"{url}/embeddings",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
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
        )
        r.raise_for_status()
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
            response_data = await r.json()
            return response_data
    except Exception as e:
        log.exception(e)
        detail = None
        if r is not None:
            try:
                res = await r.json()
                if "error" in res:
                    detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except Exception:
                detail = f"External: {e}"
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "Open WebUI: Server Connection Error",
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
        headers = {
            "Content-Type": "application/json",
            **(
                {
                    "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                    "X-OpenWebUI-User-Id": user.id,
                    "X-OpenWebUI-User-Email": user.email,
                    "X-OpenWebUI-User-Role": user.role,
                }
                if ENABLE_FORWARD_USER_INFO_HEADERS
                else {}
            ),
        }

        if api_config.get("azure", False):
            api_version = api_config.get("api_version", "2023-03-15-preview")
            headers["api-key"] = key
            headers["api-version"] = api_version

            payload = json.loads(body)
            url, payload = convert_to_azure_payload(url, payload, api_version)
            body = json.dumps(payload).encode()

            request_url = f"{url}/{path}?api-version={api_version}"
        else:
            headers["Authorization"] = f"Bearer {key}"
            request_url = f"{url}/{path}"

        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=request_url,
            data=body,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        r.raise_for_status()

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
            response_data = await r.json()
            return response_data

    except Exception as e:
        log.exception(e)

        detail = None
        if r is not None:
            try:
                res = await r.json()
                log.error(res)
                if "error" in res:
                    detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except Exception:
                detail = f"External: {e}"
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)

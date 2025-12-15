import asyncio
import hashlib
import json
import logging
from typing import Optional

import aiohttp
from aiocache import cached
import requests
from urllib.parse import quote

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
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access
from open_webui.socket.main import process_token_usage
from open_webui.models.chats import Chats
from open_webui.models.files import Files
from open_webui.storage.provider import Storage
from open_webui.constants import TASKS
from open_webui.utils.task import title_generation_template, tags_generation_template
from open_webui.config import (
    DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE,
)
import base64
import re

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


##########################################
#
# Utility functions
#
##########################################

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


def normalize_image_mime_type(mime_type: Optional[str]) -> Optional[str]:
    if not mime_type:
        return None

    normalized = mime_type.strip().lower()
    # Strip any optional parameters (e.g. "image/jpeg; charset=binary")
    normalized = normalized.split(";", 1)[0].strip()

    if normalized == "image/jpg":
        return "image/jpeg"
    if normalized == "image/pjpeg":
        return "image/jpeg"
    if normalized == "image/x-png":
        return "image/png"

    return normalized


def sniff_image_mime_type(image_data: bytes) -> Optional[str]:
    if not image_data:
        return None

    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
        return "image/gif"

    if len(image_data) >= 12 and image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        return "image/webp"

    if image_data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"

    return None


def infer_image_mime_type_from_filename(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None

    lower = filename.lower()

    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"

    return None


def resolve_image_mime_type(
    mime_type: Optional[str],
    filename: Optional[str],
    image_data: bytes,
) -> str:
    normalized = normalize_image_mime_type(mime_type)
    if normalized in SUPPORTED_IMAGE_MIME_TYPES:
        return normalized

    sniffed = sniff_image_mime_type(image_data)
    if sniffed:
        return sniffed

    inferred = infer_image_mime_type_from_filename(filename)
    if inferred:
        return inferred

    # Preserve an explicit image/* content-type if present (even if unsupported by a provider)
    if normalized and normalized.startswith("image/"):
        return normalized

    # Final fallback for providers that require an image/* type.
    return "image/jpeg"


def user_can_read_file(file, user: UserModel) -> bool:
    if not file or not user:
        return False

    if getattr(file, "user_id", None) == user.id or user.role == "admin":
        return True

    access_control = getattr(file, "access_control", None)
    if access_control:
        return has_access(user.id, type="read", access_control=access_control)

    return False


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

    # Filter out unsupported parameters
    payload = {k: v for k, v in payload.items() if k in allowed_params}

    url = f"{url}/openai/deployments/{model}"
    return url, payload


async def trigger_title_generation(request, user, model_id, messages, chat_id):
    try:
        chat = Chats.get_chat_by_id(chat_id)
        if not chat:
            return

        # If title is already set (not "New Chat"), probably skip?
        # But let's just try to generate if it's short history?
        # Simplest: Only if title is "New Chat"
        # If title is not default "New Chat", skip generation
        if chat.title and chat.title != "New Chat":
            return

        template = DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE
        # Title generation
        if request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE:
            template = request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE

        content = title_generation_template(template, messages, user)

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": content}],
            "stream": False,
            "metadata": {"task": str(TASKS.TITLE_GENERATION), "chat_id": chat_id},
        }

        response = await generate_chat_completion(
            request, payload, user, bypass_filter=True
        )

        title = ""
        if isinstance(response, dict) and "choices" in response:
            title = response["choices"][0]["message"]["content"]

        if title:
            # Clean up title similar to frontend logic
            title = title.strip().replace('"', "")
            # Update DB
            Chats.update_chat_by_id(chat.id, {"title": title})

        # Tags generation (server-side parity with frontend)
        try:
            # Tags template
            tags_template = (
                request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE
                if request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE
                else DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE
            )

            tags_content = tags_generation_template(tags_template, messages, user)

            tags_payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": tags_content}],
                "stream": False,
                "metadata": {"task": str(TASKS.TAGS_GENERATION), "chat_id": chat_id},
            }

            tags_response = await generate_chat_completion(
                request, tags_payload, user, bypass_filter=True
            )

            tags_string = ""
            if isinstance(tags_response, dict) and "choices" in tags_response:
                if len(tags_response.get("choices", [])) >= 1:
                    resp_msg = tags_response["choices"][0].get("message", {})
                    tags_string = resp_msg.get("content") or resp_msg.get("reasoning_content", "")

            if tags_string:
                # Extract JSON object from the model output (frontend does the same)
                start = tags_string.find("{")
                end = tags_string.rfind("}")
                if start != -1 and end != -1 and end > start:
                    json_part = tags_string[start : end + 1]
                    try:
                        tags_json = json.loads(json_part)
                        tags = tags_json.get("tags", [])
                        if tags:
                            Chats.update_chat_tags_by_id(chat_id, tags, user)
                    except Exception:
                        log.debug("Could not parse tags response")
        except Exception as e:
            log.error(f"Error generating tags: {e}")

    except Exception as e:
        log.error(f"Error generating title: {e}")


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

    has_pdf_files = False

    # Resolve image URLs to base64
    # IMPORTANT: Local file URLs (like /api/v1/files/{id}/content) MUST be converted to base64
    # because external providers like OpenRouter cannot access them. If conversion fails,
    # we must either remove the image or raise an error to prevent hanging requests.
    if "messages" in payload:
        for message in payload["messages"]:
            if isinstance(message.get("content"), list):
                parts_to_remove = []
                for part_idx, part in enumerate(message["content"]):
                    if part.get("type") == "image_url":
                        url = part["image_url"]["url"]
                        
                        # Skip if already a data URL (base64)
                        if url.startswith("data:"):
                            continue
                            
                        # Check if it's a local file URL (e.g. /api/v1/files/{id} or /api/v1/files/{id}/content)
                        # We look for the file ID pattern - match both with and without /content
                        match = re.search(r"/api/v1/files/([^/]+)(?:/content)?(?:\?|$)", url)
                        if not match:
                            match = re.search(r"/api/v1/files/([a-f0-9-]+)", url)
                        if match:
                            file_id = match.group(1)
                            log.debug(f"Resolving local file URL to base64: file_id={file_id}")
                            file = Files.get_file_by_id(file_id)
                            if not file:
                                log.warning(f"File not found in database: {file_id}. Removing image from message.")
                                parts_to_remove.append(part_idx)
                                continue
                            if not user_can_read_file(file, user):
                                log.warning(f"User {user.id} does not have permission to read file {file_id}. Removing image from message.")
                                parts_to_remove.append(part_idx)
                                continue
                            try:
                                file_path = Storage.get_file(file.path)
                                log.debug(f"Reading file from storage: {file_path}")
                                with open(file_path, "rb") as f:
                                    image_data = f.read()
                                    if not image_data:
                                        log.warning(f"File is empty: {file_path}. Removing image from message.")
                                        parts_to_remove.append(part_idx)
                                        continue
                                    base64_image = base64.b64encode(image_data).decode("utf-8")
                                    mime_type = resolve_image_mime_type(
                                        (file.meta or {}).get("content_type"),
                                        getattr(file, "filename", None),
                                        image_data,
                                    )
                                    part["image_url"]["url"] = f"data:{mime_type};base64,{base64_image}"
                                    log.debug(f"Successfully converted image to base64: mime_type={mime_type}, size={len(image_data)} bytes")
                            except FileNotFoundError as e:
                                log.error(f"File not found on disk: {file_path}. Removing image from message. Error: {e}")
                                parts_to_remove.append(part_idx)
                            except Exception as e:
                                log.error(f"Error resolving image URL {url}: {e}. Removing image from message.")
                                parts_to_remove.append(part_idx)
                        # If it's a non-local URL (http/https), keep it as-is - provider may be able to fetch it
                        elif not url.startswith(("http://", "https://")):
                            # Unknown URL format that's not a public URL - remove to prevent issues
                            log.warning(f"Unknown image URL format (not data:, http:, https:, or local file): {url[:100]}. Removing image from message.")
                            parts_to_remove.append(part_idx)
                
                # Remove failed images in reverse order to preserve indices
                for idx in reversed(parts_to_remove):
                    removed_part = message["content"].pop(idx)
                    log.debug(f"Removed image part at index {idx}")
                    elif part.get("type") == "file":
                        file_obj = part.get("file") or {}
                        file_data = file_obj.get("file_data")
                        filename = file_obj.get("filename") or ""

                        if isinstance(file_data, str):
                            if file_data.startswith("data:application/pdf"):
                                has_pdf_files = True
                            if file_data.lower().endswith(".pdf"):
                                has_pdf_files = True
                            if filename.lower().endswith(".pdf"):
                                has_pdf_files = True

                            # Match both /api/v1/files/{id} and /api/v1/files/{id}/content
                            match = re.search(r"/api/v1/files/([^/]+)(?:/content)?(?:\?|$)", file_data)
                            if not match:
                                # Also try without query string (simpler match for /api/v1/files/{id})
                                match = re.search(r"/api/v1/files/([a-f0-9-]+)", file_data)
                            if match:
                                file_id = match.group(1)
                                file = Files.get_file_by_id(file_id)
                                if file and user_can_read_file(file, user):
                                    try:
                                        file_path = Storage.get_file(file.path)
                                        with open(file_path, "rb") as f:
                                            raw = f.read()

                                        base64_file = base64.b64encode(raw).decode(
                                            "utf-8"
                                        )

                                        content_type = (
                                            (file.meta or {}).get("content_type")
                                            or "application/octet-stream"
                                        )
                                        if isinstance(content_type, str):
                                            content_type = (
                                                content_type.split(";", 1)[0]
                                                .strip()
                                                .lower()
                                            )
                                        else:
                                            content_type = "application/octet-stream"

                                        is_pdf = (
                                            content_type == "application/pdf"
                                            or (file.filename or "")
                                            .lower()
                                            .endswith(".pdf")
                                            or filename.lower().endswith(".pdf")
                                        )
                                        if is_pdf:
                                            has_pdf_files = True
                                            content_type = "application/pdf"

                                        file_obj["file_data"] = (
                                            f"data:{content_type};base64,{base64_file}"
                                        )
                                        file_obj["filename"] = (
                                            filename
                                            or file.filename
                                            or (file.meta or {}).get("name")
                                            or "file"
                                        )
                                        part["file"] = file_obj
                                    except Exception as e:
                                        log.error(
                                            f"Error resolving file URL {file_data}: {e}"
                                        )

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
            payload = apply_system_prompt_to_body(system, payload, metadata, user)

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

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # OpenRouter PDF inputs: prefer native file processing for vision-capable models.
    if has_pdf_files and "openrouter.ai" in url:
        plugins = payload.get("plugins")
        if not isinstance(plugins, list):
            plugins = []

        file_parser_plugin = None
        for plugin in plugins:
            if isinstance(plugin, dict) and plugin.get("id") == "file-parser":
                file_parser_plugin = plugin
                break

        if file_parser_plugin is None:
            file_parser_plugin = {"id": "file-parser"}
            plugins.append(file_parser_plugin)

        pdf_plugin_config = file_parser_plugin.get("pdf")
        if not isinstance(pdf_plugin_config, dict):
            pdf_plugin_config = {}

        pdf_plugin_config["engine"] = "native"
        file_parser_plugin["pdf"] = pdf_plugin_config
        payload["plugins"] = plugins

        # Always prioritize frontend 'reasoning' object over model 'reasoning_effort'
    # reasoning_effort is deprecated in favor of reasoning object
    if "reasoning" in payload and isinstance(payload["reasoning"], dict):
        payload.pop("reasoning_effort", None)
    elif "reasoning_effort" in payload:
        payload["reasoning"] = {"effort": payload.pop("reasoning_effort")}

    # Convert the modified body back to JSON
    if "logit_bias" in payload:
        payload["logit_bias"] = json.loads(
            convert_logit_bias_input_to_json(payload["logit_bias"])
        )

    # Ensure usage is returned when streaming
    if payload.get("stream", False):
        if "stream_options" not in payload:
            payload["stream_options"] = {"include_usage": True}
        elif isinstance(payload["stream_options"], dict):
            payload["stream_options"]["include_usage"] = True

    # Background Tasks: Title Generation
    task_type = None
    chat_id = None
    if metadata:
        task_type = metadata.get("task")
        chat_id = metadata.get("chat_id")

    if not chat_id and "chat_id" in payload:
        chat_id = payload["chat_id"]

    if chat_id and task_type is None:
        asyncio.create_task(
            trigger_title_generation(
                request, user, model_id, payload["messages"], chat_id
            )
        )

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, metadata, user=user
    )

    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        request_url, payload = convert_to_azure_payload(url, payload, api_version)

        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get("auth_type", "bearer")
        if auth_type not in ("azure_ad", "microsoft_entra_id"):
            headers["api-key"] = key

        headers["api-version"] = api_version
        request_url = f"{request_url}/chat/completions?api-version={api_version}"
    else:
        request_url = f"{url}/chat/completions"

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
            # Check status code before streaming - error responses may have SSE content-type
            # but empty/malformed body which causes infinite hang when iterating
            if r.status >= 400:
                try:
                    error_data = await r.json()
                except Exception:
                    error_data = await r.text()

                await cleanup_response(r, session)

                if isinstance(error_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=error_data)
                else:
                    return PlainTextResponse(status_code=r.status, content=error_data)

            streaming = True

            async def stream_wrapper(stream):
                async for chunk in stream:
                    yield chunk
                    try:
                        # Attempt to extract usage from the chunk
                        decoded = chunk.decode("utf-8", errors="ignore")
                        if '"usage"' in decoded:
                            for line in decoded.split("\n"):
                                if line.startswith("data: "):
                                    try:
                                        # Skip "data: [DONE]"
                                        if line.strip() == "data: [DONE]":
                                            continue
                                        
                                        data = json.loads(line[6:])
                                        if "usage" in data:
                                            await process_token_usage(model_id, data["usage"])
                                    except Exception:
                                        pass
                    except Exception:
                        pass

            return StreamingResponse(
                stream_wrapper(r.content),
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

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            if isinstance(response, dict) and "usage" in response:
                await process_token_usage(model_id, response["usage"])

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
            # Check status code before streaming - error responses may have SSE content-type
            # but empty/malformed body which causes infinite hang when iterating
            if r.status >= 400:
                try:
                    error_data = await r.json()
                except Exception:
                    error_data = await r.text()

                await cleanup_response(r, session)

                if isinstance(error_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=error_data)
                else:
                    return PlainTextResponse(status_code=r.status, content=error_data)

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

            if isinstance(response_data, dict) and "usage" in response_data:
                await process_token_usage(model_id, response_data["usage"])

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

    model_id = None
    try:
        body_json = json.loads(body)
        model_id = body_json.get("model")

        # Ensure usage is returned when streaming
        if body_json.get("stream", False):
            if "stream_options" not in body_json:
                body_json["stream_options"] = {"include_usage": True}
                body = json.dumps(body_json).encode()
            elif isinstance(body_json["stream_options"], dict):
                body_json["stream_options"]["include_usage"] = True
                body = json.dumps(body_json).encode()
    except Exception:
        pass

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
            # Check status code before streaming - error responses may have SSE content-type
            # but empty/malformed body which causes infinite hang when iterating
            if r.status >= 400:
                try:
                    error_data = await r.json()
                except Exception:
                    error_data = await r.text()

                await cleanup_response(r, session)

                if isinstance(error_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=error_data)
                else:
                    return PlainTextResponse(status_code=r.status, content=error_data)

            streaming = True

            # Only wrap if we have a model_id to attribute to
            if model_id:

                async def stream_wrapper(stream):
                    async for chunk in stream:
                        yield chunk
                        try:
                            # Attempt to extract usage from the chunk
                            decoded = chunk.decode("utf-8", errors="ignore")
                            if '"usage"' in decoded:
                                for line in decoded.split("\n"):
                                    if line.startswith("data: "):
                                        try:
                                            # Skip "data: [DONE]"
                                            if line.strip() == "data: [DONE]":
                                                continue

                                            data = json.loads(line[6:])
                                            if "usage" in data:
                                                await process_token_usage(
                                                    model_id, data["usage"]
                                                )
                                        except Exception:
                                            pass
                        except Exception:
                            pass

                return StreamingResponse(
                    stream_wrapper(r.content),
                    status_code=r.status,
                    headers=dict(r.headers),
                    background=BackgroundTask(
                        cleanup_response, response=r, session=session
                    ),
                )
            else:
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

            if model_id and isinstance(response_data, dict) and "usage" in response_data:
                await process_token_usage(model_id, response_data["usage"])

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

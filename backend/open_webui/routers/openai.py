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
from open_webui.memory.cross_window_memory import last_process_payload
from open_webui.utils.misc import extract_timestamped_messages

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
                "X-Title": "CyberLover",
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
                detail=detail if detail else "CyberLover: Server Connection Error",
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
                    status_code=500, detail="CyberLover: Server Connection Error"
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
                status_code=500, detail="CyberLover: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail="CyberLover: Server Connection Error"
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
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
    chatting_completion: bool = False
):
    """
    OpenAI 兼容的聊天完成端点 - 直接转发请求到 OpenAI API 或兼容服务

    这是 OpenAI router 中的底层 API 调用函数，负责：
    1. 应用模型配置（base_model_id, system prompt, 参数覆盖）
    2. 验证用户权限（模型访问控制）
    3. 处理 Azure OpenAI 特殊格式转换
    4. 处理推理模型（reasoning model）特殊逻辑
    5. 转发 HTTP 请求到上游 API（支持流式和非流式）

    Args:
        request: FastAPI Request 对象
        form_data: OpenAI 格式的聊天请求
            - model: 模型 ID
            - messages: 消息列表
            - stream: 是否流式响应
            - temperature, max_tokens 等参数
        user: 已验证的用户对象
        bypass_filter: 是否绕过权限检查

    Returns:
        - 流式: StreamingResponse (SSE)
        - 非流式: dict (OpenAI JSON 格式)

    Raises:
        HTTPException 403: 无权限访问模型
        HTTPException 404: 模型不存在
        HTTPException 500: 上游 API 连接失败
    """

    # print("user:", user)
    # user: 
    #     id='55f85fb0-4aca-48bc-aea1-afce50ac989e' 
    #     name='gaofeng1' 
    #     email='h.summit1628935449@gmail.com' 
    #     username=None 
    #     role='user' 
    #     profile_image_url='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAEa0lEQVR4Xu2aW0hUQRzG/7vr7noLSZGgIIMsobAgjRKCrhSJD0EXgpSCopcK6qmCHgyC6Kmo6CGMiAgqeqgQ6SG7EYhoQQpdSCKppBARMXUv7m47C7vr2ZX2XHa378S3b8uZmfPN95tvzpw54xhvK48IfzAOOAgEhkVMCIFg8SAQMB4EQiBoDoDp4TOEQMAcAJPDhBAImANgcpgQAgFzAEwOE0IgYA6AyWFCCATMATA5TAiBgDkAJocJIRAwB8DkMCEEAuYAmBwmhEDAHACTw4QQCJgDYHKYEAIBcwBMDhNCIGAOgMlhQggEzAEwOUwIgVh3wF3TIq55a8VZvlwchRXiKJmvaTQyMSQR34iEfnVLcOC+hIffWL9pnlqwVUK8DRekoKoxDUAmr2Jg+q/K9GBHpqL//LotgDgr66Ro/TVxlFWbNyw0JcFPd8TfddJ8G3moCQ9ETU/ehvMirqI0O8Ij/RIeH5TQcG/imsNTJs6yJeKqXDVrkoLv26ChQANR01PhxutaGNGRPv2tUwJ9lzM+G9wrjolnaXNasvyvj0fTcjsP4934LaCBlOzq1prpHxV/z1nDZhY1dUQXAWsS7kTGBmTiQfK/cdtyVwMWiHqAu5cdSvY8mgx/12nDMOINlOzt10xhvqctkA95WCClzQMi3rkJIIF3FyXQe8700PTUnxHPyhOJ+qEfz2TqyW7T7eWqIiSQVPOyNcWolMTfT0JDL5kQvaMqdc5HXxnp7ZeecpAJSZ2uJh9vzbii0tNZO5SBAxJb6m5JLknVNsjE3Vo7eJkVjXBA1LuDd3VronPq5W/y4YasdNYOjcADmf7aLr7O/XbwMisa/ysgpQdHDJny+0aFofL5KEwg+XDZwD3ggait86n2Rl1dYkJ02WSsUGx3d90lU/tOakHwt1/Bwu2aPS1OWTrZlB74rtnhzZZxhZtvScGipoSKbLWrs1u6isFNWUp18Y4X4qxIvntY3ceKO0EgusZEeqHUnd5s7WURiEkgqlrq9om/p1WCfVcstChCIBbsm+17iO/5YUs7tARiAYiqmvbF0MJHqhjgmn05WSxY7KamOuRDPa5QnTYp3nZP86FKXdN7rEfVd1fvEffinWltqHa4yjIxlNTurxrdqYfhVFNqJzg0/FbCY58lEhhLtO6qrBfnnCrNSk1za3VQ4ssj8b06YkJRbqtAJ2RmUrx1p8S1YJNlN/Smy/KNTDZgCyDxvqm0uGuPat62dfU7mojQzy4JfrhpaVGg614WC9kKyMzEqGeDenl0qrO9qScao8eFYt/ORz/GDtFZXS5b9NhQdVsCMdRDmxUmEDBgBEIgYA6AyWFCCATMATA5TAiBgDkAJocJIRAwB8DkMCEEAuYAmBwmhEDAHACTw4QQCJgDYHKYEAIBcwBMDhNCIGAOgMlhQggEzAEwOUwIgYA5ACaHCSEQMAfA5DAhBALmAJgcJoRAwBwAk8OEEAiYA2BymBACAXMATA4TQiBgDoDJYUIIBMwBMDl/AP79PANEXNbbAAAAAElFTkSuQmCC' 
    #     bio=None 
    #     gender=None 
    #     date_of_birth=None 
    #     info=None 
    #     settings=UserSettings(ui={'memory': True}) 
    #     api_key=None 
    #     oauth_sub=None 
    #     last_active_at=1763997832 
    #     updated_at=1763971141 
    #     created_at=1763874812

    # === 1. 权限检查配置 ===
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0  # 用于标识使用哪个 OPENAI_API_BASE_URL

    # === 2. 准备 Payload 和提取元数据 ===
    payload = {**form_data}
    metadata = payload.pop("metadata", None)  # 移除内部元数据，不发送给上游 API

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # === 3. 应用模型配置和权限检查 ===
    # Check model info and override the payload
    if model_info:
        # 3.1 如果配置了 base_model_id，替换为底层模型 ID
        # 例如：自定义模型 "my-gpt4" → 实际调用 "gpt-4-turbo"
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        # 3.2 应用模型参数（temperature, max_tokens 等）
        params = model_info.params.model_dump()

        if params:
            system = params.pop("system", None)  # 提取 system prompt

            # 应用模型参数到 payload（覆盖用户传入的参数）
            payload = apply_model_params_to_body_openai(params, payload)
            # 注入或替换 system prompt
            payload = apply_system_prompt_to_body(system, payload, metadata, user)

        # 3.3 权限检查：验证用户是否有权限访问该模型
        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id  # 用户是模型创建者
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )  # 或用户在访问控制列表中
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        # 如果模型信息不存在且未绕过过滤器，只有管理员可访问
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    # === 4. 查找 OpenAI API 配置 ===
    await get_all_models(request, user=user)  # 刷新模型列表
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]  # 获取 API 基础 URL 索引
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # === 5. 获取 API 配置并处理 prefix_id ===
    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    # 移除模型 ID 前缀（如果配置了 prefix_id）
    # 例如：模型 ID "custom.gpt-4" → 发送给 API 的是 "gpt-4"
    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # === 6. Pipeline 模式：注入用户信息 ===
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

    # === 7. 推理模型特殊处理 ===
    # Check if model is a reasoning model that needs special handling
    if is_openai_reasoning_model(payload["model"]):
        # 推理模型（如 o1）使用 max_completion_tokens 而非 max_tokens
        payload = openai_reasoning_model_handler(payload)
    elif "api.openai.com" not in url:
        # 非 OpenAI 官方 API：向后兼容，将 max_completion_tokens 转为 max_tokens
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    # 避免同时存在 max_tokens 和 max_completion_tokens
    if "max_tokens" in payload and "max_completion_tokens" in payload:
        del payload["max_tokens"]

    # === 8. 转换 logit_bias 格式 ===
    # Convert the modified body back to JSON
    if "logit_bias" in payload:
        payload["logit_bias"] = json.loads(
            convert_logit_bias_input_to_json(payload["logit_bias"])
        )

    # === 9. 准备请求头和 Cookies ===
    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, metadata, user=user
    )

    # === 10. Azure OpenAI 特殊处理 ===
    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        request_url, payload = convert_to_azure_payload(url, payload, api_version)

        # 只有在非 Azure Entra ID 认证时才设置 api-key header
        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get("auth_type", "bearer")
        if auth_type not in ("azure_ad", "microsoft_entra_id"):
            headers["api-key"] = key

        headers["api-version"] = api_version
        request_url = f"{request_url}/chat/completions?api-version={api_version}"
    else:
        # 标准 OpenAI 兼容 API
        request_url = f"{url}/chat/completions"

    if chatting_completion:
        try:
            # 可选钩子：在发送到上游前记录/审计 payload，需自行实现 last_process_payload
            log.debug(
                f"chatting_completion hook user={user.id} chat_id={metadata.get('chat_id')} model={payload.get('model')}"
            )
        except Exception as e:
            log.debug(f"chatting_completion 钩子执行失败: {e}")

    
    # 移除上游不识别的内部参数
    for key in [
        "is_user_model",
        "variables",
        "model_item",
        "background_tasks",
        "chat_id",
        "id",
        "message_id",
        "session_id",
        "filter_ids",
        "tool_servers",
    ]:
        payload.pop(key, None)

    payload = json.dumps(payload)  # 序列化为 JSON 字符串

    # === 11. 预扣费：流式请求启动前 ===
    precharge_id = None
    estimated_prompt = 0
    if form_data.get("stream", False):  # 只对流式请求预扣费
        from open_webui.utils.billing import estimate_prompt_tokens, precharge_balance

        try:
            # 1. tiktoken预估prompt tokens
            messages = form_data.get("messages", [])
            estimated_prompt = estimate_prompt_tokens(messages, model_id)

            # 2. 获取max_tokens参数（默认4096）
            max_completion = form_data.get("max_completion_tokens") or form_data.get("max_tokens", 4096)

            # 3. 预扣费
            precharge_id, precharged_cost, balance_after = precharge_balance(
                user_id=user.id,
                model_id=model_id,
                estimated_prompt_tokens=estimated_prompt,
                max_completion_tokens=max_completion
            )

            log.info(
                f"预扣费成功: user={user.id} model={model_id} "
                f"estimated={estimated_prompt}+{max_completion}tokens "
                f"cost={precharged_cost / 10000:.4f}元 precharge_id={precharge_id}"
            )
        except HTTPException as e:
            # 余额不足或账户冻结，直接抛出阻止请求
            raise e
        except Exception as e:
            # 预扣费失败（如数据库错误、计费服务异常），降级为后付费
            log.error(
                f"预扣费失败，降级为后付费: user={user.id} model={model_id} "
                f"estimated={estimated_prompt}+{max_completion}tokens "
                f"error={type(e).__name__}: {str(e)}",
                exc_info=True  # 打印完整堆栈
            )
            precharge_id = None

    # === 12. 初始化请求状态变量 ===
    r = None
    session = None
    streaming = False
    response = None

    try:
        # === 12. 发起 HTTP 请求到上游 API ===
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

        # === 13. 处理响应 ===
        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            # 流式响应：添加计费包装器
            streaming = True

            # 创建计费包装的流式生成器
            async def stream_with_billing(
                user_id: str,
                model_id: str,
                stream,
                precharge_id: Optional[str],
                estimated_prompt: int = 0
            ):
                """
                流式响应计费包装器：预扣费模式下精确结算

                Args:
                    precharge_id: 预扣费事务ID（None表示降级为后付费）
                    estimated_prompt: 预估的prompt tokens（用于fallback）
                """
                import asyncio
                from open_webui.utils.billing import deduct_balance, settle_precharge

                accumulated = {"prompt": 0, "completion": 0}
                has_usage_data = False

                try:
                    # 1. 转发流式数据，累积 tokens
                    async for chunk in stream:
                        if b"data: " in chunk:
                            try:
                                data_str = chunk.decode().replace("data: ", "").strip()
                                if data_str and data_str != "[DONE]":
                                    data = json.loads(data_str)
                                    if "usage" in data:
                                        has_usage_data = True
                                        # 修复bug：使用max()避免覆盖
                                        accumulated["prompt"] = max(
                                            accumulated["prompt"],
                                            data["usage"].get("prompt_tokens", 0)
                                        )
                                        accumulated["completion"] += data["usage"].get("completion_tokens", 0)
                            except Exception:
                                pass
                        yield chunk

                except asyncio.CancelledError:
                    # 客户端断开连接（用户取消）
                    log.info(f"流式请求被取消: user={user_id} model={model_id}")
                    raise  # 继续抛出，确保finally块执行

                finally:
                    # 2. 精确结算（无论正常结束还是中断）
                    try:
                        if precharge_id:
                            # === 预扣费模式：精确结算 ===

                            # Fallback：如果没有收到usage，使用预估值
                            if not has_usage_data or accumulated["prompt"] == 0:
                                log.warning(f"未收到usage信息，使用预估值: precharge_id={precharge_id}")
                                accumulated["prompt"] = estimated_prompt

                            # 结算
                            actual_cost, refund, balance_after = settle_precharge(
                                precharge_id=precharge_id,
                                actual_prompt_tokens=accumulated["prompt"],
                                actual_completion_tokens=accumulated["completion"]
                            )

                            log.info(
                                f"结算完成: user={user_id} precharge_id={precharge_id} "
                                f"actual={accumulated['prompt']}+{accumulated['completion']}tokens "
                                f"cost={actual_cost / 10000:.4f}元 refund={refund / 10000:.4f}元"
                            )

                        elif accumulated["prompt"] > 0 or accumulated["completion"] > 0:
                            # === 降级后付费模式：直接扣费 ===
                            # 注意：此分支说明预扣费失败，使用后付费降级方案
                            cost, balance_after = deduct_balance(
                                user_id=user_id,
                                model_id=model_id,
                                prompt_tokens=accumulated["prompt"],
                                completion_tokens=accumulated["completion"],
                                log_type="deduct"
                            )
                            log.warning(
                                f"降级后付费扣费（预扣费失败）: user={user_id} model={model_id} "
                                f"actual={accumulated['prompt']}+{accumulated['completion']}tokens "
                                f"cost={cost / 10000:.4f}元 balance={balance_after / 10000:.4f}元"
                            )

                    except Exception as e:
                        log.error(f"计费结算异常: {e}", exc_info=True)

            return StreamingResponse(
                stream_with_billing(
                    user.id,
                    form_data.get("model", "unknown"),
                    r.content,
                    precharge_id,
                    estimated_prompt
                ),
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            # 非流式响应：解析 JSON
            try:
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()  # 如果 JSON 解析失败，返回纯文本

            # 处理错误响应
            if r.status >= 400:
                # 回滚预扣费（如果已预扣）
                if precharge_id:
                    from open_webui.utils.billing import settle_precharge
                    try:
                        settle_precharge(precharge_id, 0, 0)  # 全额退款
                        log.info(f"API错误，预扣费已退款: precharge_id={precharge_id}")
                    except Exception as e:
                        log.error(f"预扣费回滚失败: {e}")

                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            # === 计费：非流式响应 ===
            if isinstance(response, dict) and "usage" in response:
                try:
                    from open_webui.utils.billing import deduct_balance

                    usage = response["usage"]
                    cost, balance = deduct_balance(
                        user_id=user.id,
                        model_id=form_data.get("model", "unknown"),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                    )
                    # 添加计费信息到响应（可选）
                    response["billing"] = {
                        "cost": float(cost),
                        "balance": float(balance),
                    }
                    log.info(
                        f"非流式请求计费成功: user={user.id} model={form_data.get('model')} "
                        f"tokens={usage.get('prompt_tokens', 0)}+{usage.get('completion_tokens', 0)} "
                        f"cost={cost / 10000:.4f}元 balance={balance / 10000:.4f}元"
                    )
                except HTTPException as e:
                    # 余额不足等错误直接抛出，中断响应
                    log.error(f"非流式请求计费失败（业务异常）: {e.detail}")
                    raise e
                except Exception as e:
                    # 其他计费错误仅记录日志，不中断响应
                    log.error(
                        f"非流式请求计费异常（系统异常）: user={user.id} model={form_data.get('model')} "
                        f"error={type(e).__name__}: {str(e)}",
                        exc_info=True
                    )

            return response  # 成功响应

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=r.status if r else 500,
            detail="CyberLover: Server Connection Error",
        )
    finally:
        # === 14. 清理资源 ===
        # 非流式响应需要手动关闭连接（流式响应在 BackgroundTask 中处理）
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
            detail="CyberLover: Server Connection Error",
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
            detail="CyberLover: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)

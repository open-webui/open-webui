import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, Optional, overload

import aiohttp
from aiocache import cached
import requests


from open_webui.apps.webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URLS,
    OPENAI_API_KEYS,
    OPENAI_API_CONFIGS,
    AppConfig,
)
from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENV, SRC_LOG_LEVELS
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)

from open_webui.utils.utils import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


app = FastAPI(
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()

app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS
app.state.config.OPENAI_API_KEYS = OPENAI_API_KEYS
app.state.config.OPENAI_API_CONFIGS = OPENAI_API_CONFIGS


@app.get("/config")
async def get_config(user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@app.post("/config/update")
async def update_config(form_data: OpenAIConfigForm, user=Depends(get_admin_user)):
    app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API

    app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(app.state.config.OPENAI_API_KEYS) != len(
        app.state.config.OPENAI_API_BASE_URLS
    ):
        if len(app.state.config.OPENAI_API_KEYS) > len(
            app.state.config.OPENAI_API_BASE_URLS
        ):
            app.state.config.OPENAI_API_KEYS = app.state.config.OPENAI_API_KEYS[
                : len(app.state.config.OPENAI_API_BASE_URLS)
            ]
        else:
            app.state.config.OPENAI_API_KEYS += [""] * (
                len(app.state.config.OPENAI_API_BASE_URLS)
                - len(app.state.config.OPENAI_API_KEYS)
            )

    app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove any extra configs
    config_urls = app.state.config.OPENAI_API_CONFIGS.keys()
    for idx, url in enumerate(app.state.config.OPENAI_API_BASE_URLS):
        if url not in config_urls:
            app.state.config.OPENAI_API_CONFIGS.pop(url, None)

    return {
        "ENABLE_OPENAI_API": app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": app.state.config.OPENAI_API_CONFIGS,
    }


@app.post("/audio/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = app.state.config.OPENAI_API_BASE_URLS.index("https://api.openai.com/v1")
        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
        file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        headers = {}
        headers["Authorization"] = f"Bearer {app.state.config.OPENAI_API_KEYS[idx]}"
        headers["Content-Type"] = "application/json"
        if "openrouter.ai" in app.state.config.OPENAI_API_BASE_URLS[idx]:
            headers["HTTP-Referer"] = "https://openwebui.com/"
            headers["X-Title"] = "Open WebUI"
        if ENABLE_FORWARD_USER_INFO_HEADERS:
            headers["X-OpenWebUI-User-Name"] = user.name
            headers["X-OpenWebUI-User-Id"] = user.id
            headers["X-OpenWebUI-User-Email"] = user.email
            headers["X-OpenWebUI-User-Role"] = user.role
        r = None
        try:
            r = requests.post(
                url=f"{app.state.config.OPENAI_API_BASE_URLS[idx]}/audio/speech",
                data=body,
                headers=headers,
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
            error_detail = "Open WebUI: Server Connection Error"
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        error_detail = f"External: {res['error']}"
                except Exception:
                    error_detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500, detail=error_detail
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def aiohttp_get(url, key=None):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST)
    try:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(url, headers=headers) as response:
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
                        "urlIdx": idx,
                    }
                    for model in models
                    if "api.openai.com"
                    not in app.state.config.OPENAI_API_BASE_URLS[idx]
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
                ]
            )

    return merged_list


async def get_all_models_responses() -> list:
    if not app.state.config.ENABLE_OPENAI_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = app.state.config.OPENAI_API_KEYS[:num_urls]
            app.state.config.OPENAI_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    tasks = []
    for idx, url in enumerate(app.state.config.OPENAI_API_BASE_URLS):
        if url not in app.state.config.OPENAI_API_CONFIGS:
            tasks.append(
                aiohttp_get(f"{url}/models", app.state.config.OPENAI_API_KEYS[idx])
            )
        else:
            api_config = app.state.config.OPENAI_API_CONFIGS.get(url, {})

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    tasks.append(
                        aiohttp_get(
                            f"{url}/models", app.state.config.OPENAI_API_KEYS[idx]
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

                    tasks.append(asyncio.ensure_future(asyncio.sleep(0, model_list)))
            else:
                tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*tasks)

    for idx, response in enumerate(responses):
        if response:
            url = app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = app.state.config.OPENAI_API_CONFIGS.get(url, {})

            prefix_id = api_config.get("prefix_id", None)

            if prefix_id:
                for model in (
                    response if isinstance(response, list) else response.get("data", [])
                ):
                    model["id"] = f"{prefix_id}.{model['id']}"

    log.debug(f"get_all_models:responses() {responses}")

    return responses


@cached(ttl=3)
async def get_all_models() -> dict[str, list]:
    log.info("get_all_models()")

    if not app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses()

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    return models


@app.get("/models")
@app.get("/models/{url_idx}")
async def get_models(url_idx: Optional[int] = None, user=Depends(get_verified_user)):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models()
    else:
        url = app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = app.state.config.OPENAI_API_KEYS[url_idx]

        headers = {}
        headers["Authorization"] = f"Bearer {key}"
        headers["Content-Type"] = "application/json"

        if ENABLE_FORWARD_USER_INFO_HEADERS:
            headers["X-OpenWebUI-User-Name"] = user.name
            headers["X-OpenWebUI-User-Id"] = user.id
            headers["X-OpenWebUI-User-Email"] = user.email
            headers["X-OpenWebUI-User-Role"] = user.role

        r = None

        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{url}/models", headers=headers) as r:
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
                # Handle aiohttp-specific connection issues, timeout etc.
                raise HTTPException(
                    status_code=500, detail="Open WebUI: Server Connection Error"
                )
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                # Generic error handler in case parsing JSON or other steps fail
                error_detail = f"Unexpected error: {str(e)}"
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role == "user":
        # Filter models based on user access control
        filtered_models = []
        for model in models.get("data", []):
            model_info = Models.get_model_by_id(model["id"])
            if model_info:
                if user.id == model_info.user_id or has_access(
                    user.id, type="read", access_control=model_info.access_control
                ):
                    filtered_models.append(model)
        models["data"] = filtered_models

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str


@app.post("/verify")
async def verify_connection(
    form_data: ConnectionVerificationForm, user=Depends(get_admin_user)
):
    url = form_data.url
    key = form_data.key

    headers = {}
    headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"

    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(f"{url}/models", headers=headers) as r:
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
            # Handle aiohttp-specific connection issues, timeout etc.
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            # Generic error handler in case parsing JSON or other steps fail
            error_detail = f"Unexpected error: {str(e)}"
            raise HTTPException(status_code=500, detail=error_detail)


@app.post("/chat/completions")
async def generate_chat_completion(
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    idx = 0
    payload = {**form_data}

    if "metadata" in payload:
        del payload["metadata"]

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        payload = apply_model_params_to_body_openai(params, payload)
        payload = apply_model_system_prompt_to_body(params, payload, user)

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

    # Attemp to get urlIdx from the model
    models = await get_all_models()

    # Find the model from the list
    model = next(
        (model for model in models["data"] if model["id"] == payload.get("model")),
        None,
    )

    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = app.state.config.OPENAI_API_CONFIGS.get(
        app.state.config.OPENAI_API_BASE_URLS[idx], {}
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

    url = app.state.config.OPENAI_API_BASE_URLS[idx]
    key = app.state.config.OPENAI_API_KEYS[idx]

    # Fix: O1 does not support the "max_tokens" parameter, Modify "max_tokens" to "max_completion_tokens"
    is_o1 = payload["model"].lower().startswith("o1-")
    # Change max_completion_tokens to max_tokens (Backward compatible)
    if "api.openai.com" not in url and not is_o1:
        if "max_completion_tokens" in payload:
            # Remove "max_completion_tokens" from the payload
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]
    else:
        if is_o1 and "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]
        if "max_tokens" in payload and "max_completion_tokens" in payload:
            del payload["max_tokens"]

    # Fix: O1 does not support the "system" parameter, Modify "system" to "user"
    if is_o1 and payload["messages"][0]["role"] == "system":
        payload["messages"][0]["role"] = "user"

    # Convert the modified body back to JSON
    payload = json.dumps(payload)

    log.debug(payload)

    headers = {}
    headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"
    if "openrouter.ai" in app.state.config.OPENAI_API_BASE_URLS[idx]:
        headers["HTTP-Referer"] = "https://openwebui.com/"
        headers["X-Title"] = "Open WebUI"
    if ENABLE_FORWARD_USER_INFO_HEADERS:
        headers["X-OpenWebUI-User-Name"] = user.name
        headers["X-OpenWebUI-User-Id"] = user.id
        headers["X-OpenWebUI-User-Email"] = user.email
        headers["X-OpenWebUI-User-Role"] = user.role

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
            url=f"{url}/chat/completions",
            data=payload,
            headers=headers,
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
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            r.raise_for_status()
            return response
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if isinstance(response, dict):
            if "error" in response:
                error_detail = f"{response['error']['message'] if 'message' in response['error'] else response['error']}"
        elif isinstance(response, str):
            error_detail = response

        raise HTTPException(status_code=r.status if r else 500, detail=error_detail)
    finally:
        if not streaming and session:
            if r:
                r.close()
            await session.close()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    idx = 0

    body = await request.body()

    url = app.state.config.OPENAI_API_BASE_URLS[idx]
    key = app.state.config.OPENAI_API_KEYS[idx]

    target_url = f"{url}/{path}"

    headers = {}
    headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"
    if ENABLE_FORWARD_USER_INFO_HEADERS:
        headers["X-OpenWebUI-User-Name"] = user.name
        headers["X-OpenWebUI-User-Id"] = user.id
        headers["X-OpenWebUI-User-Email"] = user.email
        headers["X-OpenWebUI-User-Role"] = user.role

    r = None
    session = None
    streaming = False

    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=target_url,
            data=body,
            headers=headers,
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
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = await r.json()
                print(res)
                if "error" in res:
                    error_detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except Exception:
                error_detail = f"External: {e}"
        raise HTTPException(status_code=r.status if r else 500, detail=error_detail)
    finally:
        if not streaming and session:
            if r:
                r.close()
            await session.close()

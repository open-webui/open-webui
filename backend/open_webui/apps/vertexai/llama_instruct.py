import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, Optional, overload

import aiohttp
import requests
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from open_webui.apps.webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    ENABLE_MODEL_FILTER,
    MODEL_FILTER_LIST,
    AppConfig,
)
from open_webui.env import AIOHTTP_CLIENT_TIMEOUT

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
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

from .config import (
    VERTEXAI_API_BASE_URLS,
    ENABLE_VERTEXAI_API,
    VERTEXAI_SERVICE_ACCOUNT_JSON,
    VERTEXAI_API_ACCESS_TOKEN
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["VERTEXAI_LLAMA_INSTRUCT"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()

app.state.config.ENABLE_MODEL_FILTER = ENABLE_MODEL_FILTER
app.state.config.MODEL_FILTER_LIST = MODEL_FILTER_LIST

app.state.config.ENABLE_VERTEXAI_API = ENABLE_VERTEXAI_API
app.state.config.VERTEXAI_API_BASE_URLS = VERTEXAI_API_BASE_URLS
app.state.config.VERTEXAI_SERVICE_ACCOUNT_JSON = VERTEXAI_SERVICE_ACCOUNT_JSON
app.state.config.VERTEXAI_API_ACCESS_TOKEN = VERTEXAI_API_ACCESS_TOKEN
# app.state.config.VERTEXAI_API_KEYS = VERTEXAI_API_KEYS

app.state.MODELS = {}

print("llama config ",app.state.config)


# if app.state.config.VERTEXAI_SERVICE_ACCOUNT_JSON != '':
#     # Load the service account credentials
#     credentials = service_account.Credentials.from_service_account_file(app.state.config.VERTEXAI_SERVICE_ACCOUNT_JSON)

#     # Set the scope required for your service (here, we use a general Google Cloud scope)
#     scoped_credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])


@app.middleware("http")
async def check_url(request: Request, call_next):
    if len(app.state.MODELS) == 0:
        await get_all_models()

    response = await call_next(request)
    return response


@app.get("/config")
async def get_config(user=Depends(get_admin_user)):
    return {"ENABLE_VERTEXAI_API": app.state.config.ENABLE_VERTEXAI_API}


class VertexAIConfigForm(BaseModel):
    enable_vertexai_api: Optional[bool] = None


@app.post("/config/update")
async def update_config(form_data: VertexAIConfigForm, user=Depends(get_admin_user)):
    app.state.config.ENABLE_VERTEXAI_API = form_data.enable_vertexai_api
    return {"ENABLE_VERTEXAI_API": app.state.config.ENABLE_VERTEXAI_API}


class UrlsUpdateForm(BaseModel):
    urls: list[str]


class KeysUpdateForm(BaseModel):
    keys: list[str]


@app.get("/urls")
async def get_vertexai_urls(user=Depends(get_admin_user)):
    return {"VERTEXAI_API_BASE_URLS": app.state.config.VERTEXAI_API_BASE_URLS}


## TO DO:
##############################
'''
@app.post("/urls/update")
async def update_openai_urls(form_data: UrlsUpdateForm, user=Depends(get_admin_user)):
    await get_all_models()
    app.state.config.VERTEXAI_API_BASE_URLS = form_data.urls
    return {"VERTEXAI_API_BASE_URLS": app.state.config.VERTEXAI_API_BASE_URLS}
'''
##############################

##TO DO:
##############################

""" 
@app.get("/keys")
async def get_openai_keys(user=Depends(get_admin_user)):
    return {"VERTEXAI_API_KEYS": app.state.config.VERTEXAI_API_KEYS}
 

@app.post("/keys/update")
async def update_openai_key(form_data: KeysUpdateForm, user=Depends(get_admin_user)):
    app.state.config.VERTEXAI_API_KEYS = form_data.keys
    return {"VERTEXAI_API_KEYS": app.state.config.VERTEXAI_API_KEYS}



@app.post("/audio/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = app.state.config.VERTEXAI_API_BASE_URLS.index("https://api.openai.com/v1")
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
        headers["Authorization"] = f"Bearer {app.state.config.VERTEXAI_API_KEYS[idx]}"
        headers["Content-Type"] = "application/json"
        if "openrouter.ai" in app.state.config.VERTEXAI_API_BASE_URLS[idx]:
            headers["HTTP-Referer"] = "https://openwebui.com/"
            headers["X-Title"] = "Open WebUI"
        r = None
        try:
            r = requests.post(
                url=f"{app.state.config.VERTEXAI_API_BASE_URLS[idx]}/audio/speech",
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
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.VERTEXAI_NOT_FOUND)
"""
##############################




async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()







def is_vertexai_api_disabled():
    urls = app.state.config.VERTEXAI_API_BASE_URLS
    if urls=='':
        return True
    return False

def is_token_valid(url, token):
    # Attempt a basic request to check if the token is valid
    # health_check_url = "https://REGION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/REGION"
    health_check_url = url[:url.find('endpoints')] # Change to your project details
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(health_check_url, headers=headers)
    return response.status_code == 200

def fetch_key(url=None, token=''):
    # Check if the token needs to be refreshed
    # Load the service account credentials
    if url is not None:
        if is_token_valid(url, token):
            return token
    credentials = service_account.Credentials.from_service_account_file(app.state.config.VERTEXAI_SERVICE_ACCOUNT_JSON)
    # print(vars(credentials))
    # Set the scope required for your service (here, we use a general Google Cloud scope)
    scoped_credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    if not scoped_credentials.valid:
        # Refresh the token if it's expired or close to expiring
        scoped_credentials.refresh(GoogleAuthRequest())

    # Get the current access token
    access_token = scoped_credentials.token
    app.state.config.VERTEXAI_API_ACCESS_TOKEN = access_token
    print("access token ", app.state.config.VERTEXAI_API_ACCESS_TOKEN )

    return access_token




async def get_all_models(raw=False) -> dict[str, list] | list:
    log.info("get_all_models()")
    if is_vertexai_api_disabled():
        return [] if raw else {"data": []}

    from .config import VERTEXAI_MODEL_LIST
    responses = VERTEXAI_MODEL_LIST
    if raw:
        return responses

    def extract_data(response):
        response_list = []
        if isinstance(response, dict):
            for id,name in response.items():
                response_list.append({
                    "id":id,
                    "name":name,
                    "created": 1692901427,
                    "owned_by": "openai",
                    "object": "model",
                    "urlIdx": 0,
                    "actions": []
                })
        return response_list

    models = {"data": extract_data(responses)}

    log.debug(f"models: {models}")
    app.state.MODELS = {model["id"]: model for model in models["data"]}
    token = fetch_key()
    return models


@app.get("/models")
@app.get("/models/{url_idx}")
async def get_models(url_idx: Optional[int] = None, user=Depends(get_verified_user)):
    if url_idx is None:
        models = await get_all_models()
        if app.state.config.ENABLE_MODEL_FILTER:
            if user.role == "user":
                models["data"] = list(
                    filter(
                        lambda model: model["id"] in app.state.config.MODEL_FILTER_LIST,
                        models["data"],
                    )
                )
                return models
        return models
    else:
        return None


@app.post("/chat/completions")
@app.post("/chat/completions/{url_idx}")
async def generate_chat_completion(
    form_data: dict,
    url_idx: Optional[int] = None,
    user=Depends(get_verified_user),
):
    idx = 0
    payload = {**form_data}

    if "metadata" in payload:
        del payload["metadata"]

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        payload = apply_model_params_to_body_openai(params, payload)
        payload = apply_model_system_prompt_to_body(params, payload, user)

    model = app.state.MODELS[payload.get("model")]
    idx = model["urlIdx"]

    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = app.state.config.VERTEXAI_API_BASE_URLS[idx]
    key = fetch_key(url, app.state.config.VERTEXAI_API_ACCESS_TOKEN)
    # key = app.state.config.VERTEXAI_API_KEYS[idx]
    # is_o1 = payload["model"].lower().startswith("o1-")

    # Change max_completion_tokens to max_tokens (Backward compatible)
    # if "api.openai.com" not in url and not is_o1:
    #     if "max_completion_tokens" in payload:
    #         # Remove "max_completion_tokens" from the payload
    #         payload["max_tokens"] = payload["max_completion_tokens"]
    #         del payload["max_completion_tokens"]
    # else:
    #     if is_o1 and "max_tokens" in payload:
    #         payload["max_completion_tokens"] = payload["max_tokens"]
    #         del payload["max_tokens"]
    #     if "max_tokens" in payload and "max_completion_tokens" in payload:
    #         del payload["max_tokens"]

    # Fix: O1 does not support the "system" parameter, Modify "system" to "user"
    # if is_o1 and payload["messages"][0]["role"] == "system":
    #     payload["messages"][0]["role"] = "user"

    # Convert the modified body back to JSON
    del payload['model']
    payload = json.dumps(payload)

    log.debug(payload)

    headers = {}
    headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"
    # if "openrouter.ai" in app.state.config.VERTEXAI_API_BASE_URLS[idx]:
    #     headers["HTTP-Referer"] = "https://openwebui.com/"
    #     headers["X-Title"] = "Open WebUI"

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
        # print("response", vars(r.headers))
        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", "") or payload['stream']:
            print("Streaming")
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

    url = app.state.config.VERTEXAI_API_BASE_URLS[idx]
    # key = app.state.config.VERTEXAI_API_KEYS[idx]
    key = fetch_key(url, app.state.config.VERTEXAI_API_ACCESS_TOKEN)

    target_url = f"{url}/{path}"

    headers = {}
    headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"

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

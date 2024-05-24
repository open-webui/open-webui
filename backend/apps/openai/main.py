from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse

import requests
import aiohttp
import asyncio
import json
import logging

from pydantic import BaseModel


from apps.web.models.users import Users
from constants import ERROR_MESSAGES
from utils.utils import (
    decode_token,
    get_current_user,
    get_verified_user,
    get_admin_user,
)
from config import (
    SRC_LOG_LEVELS,
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URLS,
    OPENAI_API_KEYS,
    CACHE_DIR,
    ENABLE_MODEL_FILTER,
    MODEL_FILTER_LIST,
    AppConfig,
)
from typing import List, Optional


import hashlib
from pathlib import Path

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.state.config = AppConfig()

app.state.config.ENABLE_MODEL_FILTER = ENABLE_MODEL_FILTER
app.state.config.MODEL_FILTER_LIST = MODEL_FILTER_LIST


app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS
app.state.config.OPENAI_API_KEYS = OPENAI_API_KEYS

app.state.MODELS = {}


@app.middleware("http")
async def check_url(request: Request, call_next):
    if len(app.state.MODELS) == 0:
        await get_all_models()
    else:
        pass

    response = await call_next(request)
    return response


@app.get("/config")
async def get_config(user=Depends(get_admin_user)):
    return {"ENABLE_OPENAI_API": app.state.config.ENABLE_OPENAI_API}


class OpenAIConfigForm(BaseModel):
    enable_openai_api: Optional[bool] = None


@app.post("/config/update")
async def update_config(form_data: OpenAIConfigForm, user=Depends(get_admin_user)):
    app.state.config.ENABLE_OPENAI_API = form_data.enable_openai_api
    return {"ENABLE_OPENAI_API": app.state.config.ENABLE_OPENAI_API}


class UrlsUpdateForm(BaseModel):
    urls: List[str]


class KeysUpdateForm(BaseModel):
    keys: List[str]


@app.get("/urls")
async def get_openai_urls(user=Depends(get_admin_user)):
    return {"OPENAI_API_BASE_URLS": app.state.config.OPENAI_API_BASE_URLS}


@app.post("/urls/update")
async def update_openai_urls(form_data: UrlsUpdateForm, user=Depends(get_admin_user)):
    await get_all_models()
    app.state.config.OPENAI_API_BASE_URLS = form_data.urls
    return {"OPENAI_API_BASE_URLS": app.state.config.OPENAI_API_BASE_URLS}


@app.get("/keys")
async def get_openai_keys(user=Depends(get_admin_user)):
    return {"OPENAI_API_KEYS": app.state.config.OPENAI_API_KEYS}


@app.post("/keys/update")
async def update_openai_key(form_data: KeysUpdateForm, user=Depends(get_admin_user)):
    app.state.config.OPENAI_API_KEYS = form_data.keys
    return {"OPENAI_API_KEYS": app.state.config.OPENAI_API_KEYS}


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
                except:
                    error_detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500, detail=error_detail
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def fetch_url(url, key):
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        if key != "":
            headers = {"Authorization": f"Bearer {key}"}
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    return await response.json()
        else:
            return None
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


def merge_models_lists(model_lists):
    log.info(f"merge_models_lists {model_lists}")
    merged_list = []

    for idx, models in enumerate(model_lists):
        if models is not None and "error" not in models:
            merged_list.extend(
                [
                    {**model, "urlIdx": idx}
                    for model in models
                    if "api.openai.com"
                    not in app.state.config.OPENAI_API_BASE_URLS[idx]
                    or "gpt" in model["id"]
                ]
            )

    return merged_list


async def get_all_models():
    log.info("get_all_models()")

    if (
        len(app.state.config.OPENAI_API_KEYS) == 1
        and app.state.config.OPENAI_API_KEYS[0] == ""
    ) or not app.state.config.ENABLE_OPENAI_API:
        models = {"data": []}
    else:
        tasks = [
            fetch_url(f"{url}/models", app.state.config.OPENAI_API_KEYS[idx])
            for idx, url in enumerate(app.state.config.OPENAI_API_BASE_URLS)
        ]

        responses = await asyncio.gather(*tasks)
        log.info(f"get_all_models:responses() {responses}")

        models = {
            "data": merge_models_lists(
                list(
                    map(
                        lambda response: (
                            response["data"]
                            if (response and "data" in response)
                            else (response if isinstance(response, list) else None)
                        ),
                        responses,
                    )
                )
            )
        }

        log.info(f"models: {models}")
        app.state.MODELS = {model["id"]: model for model in models["data"]}

        return models


@app.get("/models")
@app.get("/models/{url_idx}")
async def get_models(url_idx: Optional[int] = None, user=Depends(get_current_user)):
    if url_idx == None:
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
        url = app.state.config.OPENAI_API_BASE_URLS[url_idx]

        r = None

        try:
            r = requests.request(method="GET", url=f"{url}/models")
            r.raise_for_status()

            response_data = r.json()
            if "api.openai.com" in url:
                response_data["data"] = list(
                    filter(lambda model: "gpt" in model["id"], response_data["data"])
                )

            return response_data
        except Exception as e:
            log.exception(e)
            error_detail = "Open WebUI: Server Connection Error"
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        error_detail = f"External: {res['error']}"
                except:
                    error_detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=error_detail,
            )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    idx = 0

    body = await request.body()
    # TODO: Remove below after gpt-4-vision fix from Open AI
    # Try to decode the body of the request from bytes to a UTF-8 string (Require add max_token to fix gpt-4-vision)
    try:
        body = body.decode("utf-8")
        body = json.loads(body)

        model = app.state.MODELS[body.get("model")]

        idx = model["urlIdx"]

        if "pipeline" in model and model.get("pipeline"):
            body["user"] = {"name": user.name, "id": user.id}
            body["title"] = (
                True if body["stream"] == False and body["max_tokens"] == 50 else False
            )

        # Check if the model is "gpt-4-vision-preview" and set "max_tokens" to 4000
        # This is a workaround until OpenAI fixes the issue with this model
        if body.get("model") == "gpt-4-vision-preview":
            if "max_tokens" not in body:
                body["max_tokens"] = 4000
            log.debug("Modified body_dict:", body)

        # Fix for ChatGPT calls failing because the num_ctx key is in body
        if "num_ctx" in body:
            # If 'num_ctx' is in the dictionary, delete it
            # Leaving it there generates an error with the
            # OpenAI API (Feb 2024)
            del body["num_ctx"]

        # Convert the modified body back to JSON
        body = json.dumps(body)
    except json.JSONDecodeError as e:
        log.error("Error loading request body into a dictionary:", e)

    url = app.state.config.OPENAI_API_BASE_URLS[idx]
    key = app.state.config.OPENAI_API_KEYS[idx]

    target_url = f"{url}/{path}"

    if key == "":
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    headers = {}
    headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"

    r = None

    try:
        r = requests.request(
            method=request.method,
            url=target_url,
            data=body,
            headers=headers,
            stream=True,
        )

        r.raise_for_status()

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            return StreamingResponse(
                r.iter_content(chunk_size=8192),
                status_code=r.status_code,
                headers=dict(r.headers),
            )
        else:
            response_data = r.json()
            return response_data
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500, detail=error_detail
        )

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse

import requests
import asyncio
import json
import logging

from pydantic import BaseModel


from constants import ERROR_MESSAGES
from utils.utils import (
    decode_token,
    get_current_user,
    get_verified_user,
    get_admin_user,
)
from config import (
    SRC_LOG_LEVELS,
    AZURE_OPENAI_API_BASE_URLS,
    AZURE_OPENAI_API_KEYS,
    AZURE_OPENAI_API_VERSIONS,
    AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES,
    CACHE_DIR,
    AZURE_MODEL_FILTER_ENABLED,
    AZURE_MODEL_FILTER_LIST,
)
from typing import List, Optional


import hashlib
from pathlib import Path

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AZUREOPENAI"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.MODEL_FILTER_ENABLED = AZURE_MODEL_FILTER_ENABLED
app.state.MODEL_FILTER_LIST = AZURE_MODEL_FILTER_LIST

app.state.AZURE_OPENAI_API_BASE_URLS = AZURE_OPENAI_API_BASE_URLS
app.state.AZURE_OPENAI_API_KEYS = AZURE_OPENAI_API_KEYS
app.state.AZURE_OPENAI_API_VERSIONS = AZURE_OPENAI_API_VERSIONS
app.state.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES = AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES

app.state.MODELS = {}


@app.middleware("http")
async def check_url(request: Request, call_next):
    if len(app.state.MODELS) == 0:
        await get_all_models()
    else:
        pass

    response = await call_next(request)
    return response


class UrlsUpdateForm(BaseModel):
    urls: List[str]


class KeysUpdateForm(BaseModel):
    keys: List[str]

class ApiVersionsUpdateForm(BaseModel):
    apiversions: List[str]

class DeploymentModelNamesUpdateForm(BaseModel):
    deploymentmodelnames: List[list[str]]

@app.get("/urls")
async def get_azure_openai_urls(user=Depends(get_admin_user)):
    return {"AZURE_OPENAI_API_BASE_URLS": app.state.AZURE_OPENAI_API_BASE_URLS}


@app.post("/urls/update")
async def update_azure_openai_urls(form_data: UrlsUpdateForm, user=Depends(get_admin_user)):
    app.state.AZURE_OPENAI_API_BASE_URLS = form_data.urls
    return {"AZURE_OPENAI_API_BASE_URLS": app.state.AZURE_OPENAI_API_BASE_URLS}


@app.get("/keys")
async def get_azure_openai_keys(user=Depends(get_admin_user)):
    return {"AZURE_OPENAI_API_KEYS": app.state.AZURE_OPENAI_API_KEYS}


@app.post("/keys/update")
async def update_azure_openai_key(form_data: KeysUpdateForm, user=Depends(get_admin_user)):
    app.state.AZURE_OPENAI_API_KEYS = form_data.keys
    return {"AZURE_OPENAI_API_KEYS": app.state.AZURE_OPENAI_API_KEYS}

@app.get("/apiversions")
async def get_azure_openai_apiversions(user=Depends(get_admin_user)):
    return {"AZURE_OPENAI_API_VERSIONS": app.state.AZURE_OPENAI_API_VERSIONS}


@app.post("/apiversions/update")
async def update_azure_openai_apiversions(form_data: ApiVersionsUpdateForm, user=Depends(get_admin_user)):
    app.state.AZURE_OPENAI_API_VERSIONS = form_data.apiversions
    return {"AZURE_OPENAI_API_VERSIONS": app.state.AZURE_OPENAI_API_VERSIONS}

@app.get("/deploymentmodelnames")
async def get_azure_openai_deployment_model_names(user=Depends(get_admin_user)):
    return {"AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES": app.state.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES}

@app.post("/deploymentmodelnames/update")
async def update_azure_openai_deployment_model_names(form_data: DeploymentModelNamesUpdateForm, user=Depends(get_admin_user)):
    app.state.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES = form_data.deploymentmodelnames
    return {"AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES": app.state.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES}


async def fetch_url(url_idx):
    level_models= []
    try:
        for model_idx, model_name in enumerate(app.state.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES[url_idx]):
            level_model = {}
            level_model["id"] = model_name
            level_model["name"] = model_name
            level_model["model_idx"] = model_idx
            level_models.append(level_model)
        return {"data": level_models}
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


def merge_models_lists(model_lists):
    merged_list = []

    for idx, models in enumerate(model_lists):
        if models is not None and "error" not in models:
            merged_list.extend(
                [
                    {**model, "urlIdx": idx}
                    for model in models
                    if "openai.com" not in app.state.AZURE_OPENAI_API_BASE_URLS[idx]
                    or "gpt" in model["id"]
                ]
            )

    return merged_list


async def get_all_models():
    log.info("Azure OpenAI get_all_models()")

    if app.state.AZURE_OPENAI_API_KEYS[0] == "":
        return {"data": []}

    tasks = [fetch_url(idx) for idx in range(len(app.state.AZURE_OPENAI_API_BASE_URLS))]
    responses = await asyncio.gather(*tasks)

    models_data = [response.get("data", None) for response in responses if response]
    models = {"data": merge_models_lists(models_data)}

    log.info(f"models: {models}")
    app.state.MODELS = {model["id"]: model for model in models["data"]}

    return models


@app.get("/models")
@app.get("/models/{url_idx}")
async def get_models(url_idx: Optional[int] = None, user=Depends(get_current_user)):
    if url_idx == None:
        models = await get_all_models()
        if app.state.MODEL_FILTER_ENABLED:
            if user.role == "user":
                models["data"] = list(
                    filter(
                        lambda model: model["id"] in app.state.MODEL_FILTER_LIST,
                        models["data"],
                    )
                )
                return models
        return models
    else:
        url = app.state.AZURE_OPENAI_API_BASE_URLS[url_idx]

        r = None

        try:
            response_data = fetch_url(url_idx=url_idx)
            if "openai.com" in url:
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
    log.info(f"Proxying request to {path}")
    idx = 0

    body = await request.body()
    # TODO: Remove below after gpt-4-vision fix from Open AI
    # Try to decode the body of the request from bytes to a UTF-8 string (Require add max_token to fix gpt-4-vision)
    try:
        body = body.decode("utf-8")
        body = json.loads(body)
        deployment_model_name = body.get("model").strip()

        idx = app.state.MODELS[deployment_model_name]["urlIdx"]

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

    url = app.state.AZURE_OPENAI_API_BASE_URLS[idx].rstrip("/")
    key = app.state.AZURE_OPENAI_API_KEYS[idx]
    api_version = app.state.AZURE_OPENAI_API_VERSIONS[idx]

    target_url = f"{url}/openai/deployments/{deployment_model_name}/{path}?api-version={api_version}"

    if key == "":
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    headers = {}
    headers["api-key"] = f"{key}"
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
                    error_detail = f"External: {res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500, detail=error_detail
        )
from bs4 import BeautifulSoup
import json
import markdown
import time
import os
import sys
import requests

from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware


from apps.ollama.main import app as ollama_app
from apps.openai.main import app as openai_app
from apps.litellm.main import app as litellm_app, startup as litellm_app_startup
from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app
from apps.web.main import app as webui_app

from pydantic import BaseModel
from typing import List


from utils.utils import get_admin_user
from apps.rag.utils import rag_messages

from config import (
    WEBUI_NAME,
    ENV,
    VERSION,
    CHANGELOG,
    FRONTEND_BUILD_DIR,
    MODEL_FILTER_ENABLED,
    MODEL_FILTER_LIST,
    WEBHOOK_URL,
)
from constants import ERROR_MESSAGES


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex


app = FastAPI(docs_url="/docs" if ENV == "dev" else None, redoc_url=None)

app.state.MODEL_FILTER_ENABLED = MODEL_FILTER_ENABLED
app.state.MODEL_FILTER_LIST = MODEL_FILTER_LIST

app.state.WEBHOOK_URL = WEBHOOK_URL


origins = ["*"]


class RAGMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and (
            "/api/chat" in request.url.path or "/chat/completions" in request.url.path
        ):
            print(request.url.path)

            # Read the original request body
            body = await request.body()
            # Decode body to string
            body_str = body.decode("utf-8")
            # Parse string to JSON
            data = json.loads(body_str) if body_str else {}

            # Example: Add a new key-value pair or modify existing ones
            # data["modified"] = True  # Example modification
            if "docs" in data:

                data = {**data}
                data["messages"] = rag_messages(
                    data["docs"],
                    data["messages"],
                    rag_app.state.RAG_TEMPLATE,
                    rag_app.state.TOP_K,
                    rag_app.state.sentence_transformer_ef,
                )
                del data["docs"]

                print(data["messages"])

            modified_body_bytes = json.dumps(data).encode("utf-8")

            # Replace the request body with the modified one
            request._body = modified_body_bytes

            # Set custom header to ensure content-length matches new body length
            request.headers.__dict__["_list"] = [
                (b"content-length", str(len(modified_body_bytes)).encode("utf-8")),
                *[
                    (k, v)
                    for k, v in request.headers.raw
                    if k.lower() != b"content-length"
                ],
            ]

        response = await call_next(request)
        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}


app.add_middleware(RAGMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.on_event("startup")
async def on_startup():
    await litellm_app_startup()


app.mount("/api/v1", webui_app)
app.mount("/litellm/api", litellm_app)

app.mount("/ollama", ollama_app)
app.mount("/openai/api", openai_app)

app.mount("/images/api/v1", images_app)
app.mount("/audio/api/v1", audio_app)
app.mount("/rag/api/v1", rag_app)


@app.get("/api/config")
async def get_app_config():

    return {
        "status": True,
        "name": WEBUI_NAME,
        "version": VERSION,
        "images": images_app.state.ENABLED,
        "default_models": webui_app.state.DEFAULT_MODELS,
        "default_prompt_suggestions": webui_app.state.DEFAULT_PROMPT_SUGGESTIONS,
    }


@app.get("/api/config/model/filter")
async def get_model_filter_config(user=Depends(get_admin_user)):
    return {
        "enabled": app.state.MODEL_FILTER_ENABLED,
        "models": app.state.MODEL_FILTER_LIST,
    }


class ModelFilterConfigForm(BaseModel):
    enabled: bool
    models: List[str]


@app.post("/api/config/model/filter")
async def update_model_filter_config(
    form_data: ModelFilterConfigForm, user=Depends(get_admin_user)
):

    app.state.MODEL_FILTER_ENABLED = form_data.enabled
    app.state.MODEL_FILTER_LIST = form_data.models

    ollama_app.state.MODEL_FILTER_ENABLED = app.state.MODEL_FILTER_ENABLED
    ollama_app.state.MODEL_FILTER_LIST = app.state.MODEL_FILTER_LIST

    openai_app.state.MODEL_FILTER_ENABLED = app.state.MODEL_FILTER_ENABLED
    openai_app.state.MODEL_FILTER_LIST = app.state.MODEL_FILTER_LIST

    return {
        "enabled": app.state.MODEL_FILTER_ENABLED,
        "models": app.state.MODEL_FILTER_LIST,
    }


@app.get("/api/webhook")
async def get_webhook_url(user=Depends(get_admin_user)):
    return {
        "url": app.state.WEBHOOK_URL,
    }


class UrlForm(BaseModel):
    url: str


@app.post("/api/webhook")
async def update_webhook_url(form_data: UrlForm, user=Depends(get_admin_user)):
    app.state.WEBHOOK_URL = form_data.url

    webui_app.state.WEBHOOK_URL = app.state.WEBHOOK_URL

    return {
        "url": app.state.WEBHOOK_URL,
    }


@app.get("/api/version")
async def get_app_config():

    return {
        "version": VERSION,
    }


@app.get("/api/changelog")
async def get_app_changelog():
    return CHANGELOG


@app.get("/api/version/updates")
async def get_app_latest_release_version():
    try:
        response = requests.get(
            f"https://api.github.com/repos/open-webui/open-webui/releases/latest"
        )
        response.raise_for_status()
        latest_version = response.json()["tag_name"]

        return {"current": VERSION, "latest": latest_version[1:]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
        )


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/cache", StaticFiles(directory="data/cache"), name="cache")


app.mount(
    "/",
    SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
    name="spa-static-files",
)

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
from apps.rag.utils import query_doc, query_collection, rag_template

from config import (
    WEBUI_NAME,
    ENV,
    VERSION,
    CHANGELOG,
    FRONTEND_BUILD_DIR,
    MODEL_FILTER_ENABLED,
    MODEL_FILTER_LIST,
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

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await litellm_app_startup()


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
                docs = data["docs"]
                print(docs)

                last_user_message_idx = None
                for i in range(len(data["messages"]) - 1, -1, -1):
                    if data["messages"][i]["role"] == "user":
                        last_user_message_idx = i
                        break

                user_message = data["messages"][last_user_message_idx]

                if isinstance(user_message["content"], list):
                    # Handle list content input
                    content_type = "list"
                    query = ""
                    for content_item in user_message["content"]:
                        if content_item["type"] == "text":
                            query = content_item["text"]
                            break
                elif isinstance(user_message["content"], str):
                    # Handle text content input
                    content_type = "text"
                    query = user_message["content"]
                else:
                    # Fallback in case the input does not match expected types
                    content_type = None
                    query = ""

                relevant_contexts = []

                for doc in docs:
                    context = None

                    try:
                        if doc["type"] == "collection":
                            context = query_collection(
                                collection_names=doc["collection_names"],
                                query=query,
                                k=rag_app.state.TOP_K,
                                embedding_function=rag_app.state.sentence_transformer_ef,
                            )
                        else:
                            context = query_doc(
                                collection_name=doc["collection_name"],
                                query=query,
                                k=rag_app.state.TOP_K,
                                embedding_function=rag_app.state.sentence_transformer_ef,
                            )
                    except Exception as e:
                        print(e)
                        context = None

                    relevant_contexts.append(context)

                context_string = ""
                for context in relevant_contexts:
                    if context:
                        context_string += " ".join(context["documents"][0]) + "\n"

                ra_content = rag_template(
                    template=rag_app.state.RAG_TEMPLATE,
                    context=context_string,
                    query=query,
                )

                if content_type == "list":
                    new_content = []
                    for content_item in user_message["content"]:
                        if content_item["type"] == "text":
                            # Update the text item's content with ra_content
                            new_content.append({"type": "text", "text": ra_content})
                        else:
                            # Keep other types of content as they are
                            new_content.append(content_item)
                    new_user_message = {**user_message, "content": new_content}
                else:
                    new_user_message = {
                        **user_message,
                        "content": ra_content,
                    }

                data["messages"][last_user_message_idx] = new_user_message
                del data["docs"]

                print(data["messages"])

            modified_body_bytes = json.dumps(data).encode("utf-8")

            # Create a new request with the modified body
            scope = request.scope
            scope["body"] = modified_body_bytes
            request = Request(scope, receive=lambda: self._receive(modified_body_bytes))

        response = await call_next(request)
        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}


app.add_middleware(RAGMiddleware)


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


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
async def get_model_filter_config(
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

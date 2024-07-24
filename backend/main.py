from bs4 import BeautifulSoup
import json
import markdown
import time
import os
import sys
import logging
import aiohttp
import requests

from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from apps.ollama.main import (
    app as ollama_app,
    OpenAIChatCompletionForm,
    generate_openai_chat_completion as generate_ollama_chat_completion,
)
from apps.openai.main import app as openai_app

from apps.litellm.main import (
    app as litellm_app,
    start_litellm_background,
    shutdown_litellm_background,
)


from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app
from apps.web.main import app as webui_app

import asyncio
from pydantic import BaseModel
from typing import List


from utils.utils import (
    get_admin_user,
    get_verified_user,
    get_current_user,
    get_http_authorization_cred,
)
from apps.rag.utils import rag_messages

from utils.misc import get_last_user_message

from apps.web.models.tools import Tools
from apps.web.utils import load_toolkit_module_by_id, tools_function_calling_generation_template

from config import (
    CONFIG_DATA,
    WEBUI_NAME,
    ENV,
    VERSION,
    CHANGELOG,
    FRONTEND_BUILD_DIR,
    CACHE_DIR,
    STATIC_DIR,
    ENABLE_LITELLM,
    ENABLE_MODEL_FILTER,
    MODEL_FILTER_LIST,
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
    WEBHOOK_URL,
    ENABLE_ADMIN_EXPORT,
    MAX_CITATION_DISTANCE,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    INITIAL_TOOLKITS
)
from constants import ERROR_MESSAGES

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex


print(
    rf"""
  ___                    __        __   _     _   _ ___ 
 / _ \ _ __   ___ _ __   \ \      / /__| |__ | | | |_ _|
| | | | '_ \ / _ \ '_ \   \ \ /\ / / _ \ '_ \| | | || | 
| |_| | |_) |  __/ | | |   \ V  V /  __/ |_) | |_| || | 
 \___/| .__/ \___|_| |_|    \_/\_/ \___|_.__/ \___/|___|
      |_|                                               

      
v{VERSION} - building the best open-source AI user interface.      
https://github.com/open-webui/open-webui
"""
)

app = FastAPI(docs_url="/docs" if ENV == "dev" else None, redoc_url=None)

app.state.ENABLE_MODEL_FILTER = ENABLE_MODEL_FILTER
app.state.MODEL_FILTER_LIST = MODEL_FILTER_LIST

app.state.WEBHOOK_URL = WEBHOOK_URL

origins = ["*"]

async def initialize_toolkits():
    toolkits_data = [INITIAL_TOOLKITS]  # List of toolkits

    # Fetch existing toolkits
    existing_toolkits = Tools.get_tools()
    existing_tool_ids = {toolkit.id for toolkit in existing_toolkits}

    client = TestClient(app)  # Use TestClient to make requests

    for data in toolkits_data:
        toolkit_id = data["id"].lower()

        # Check if toolkit already exists
        if toolkit_id not in existing_tool_ids:
            # Prepare form data for toolkit creation
            form_data = {
                "id": toolkit_id,
                "name": data["name"],
                "meta": data["meta"],
                "content": data["content"]
            }

            # Call the create_new_toolkit endpoint
            try:
                response = client.post("/api/v1/tools/create", json=form_data)
                log.info(f"Toolkit {toolkit_id} created successfully.")
            except Exception as e:
                log.error(f"An error occurred while creating toolkit {toolkit_id}: {e}")
        else:
            log.info(f"{toolkit_id} toolkit already exists.")

async def get_function_call_response(prompt, tool_id, template, task_model_id, user):
    tool = Tools.get_tool_by_id(tool_id)
    tools_specs = json.dumps(tool.specs, indent=2)
    content = tools_function_calling_generation_template(template, tools_specs)

    payload = {
        "model": task_model_id,
        "messages": [
            {"role": "system", "content": content},
            {"role": "user", "content": f"Query: {prompt}"},
        ],
        "stream": False,
    }

    response = None
    try:
        response = await generate_ollama_chat_completion(
            OpenAIChatCompletionForm(**payload), user=user
        )

        content = None
        async for chunk in response.body_iterator:
            data = json.loads(chunk.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        log.info(f'the data from the call: {data}')
        # Cleanup any remaining background tasks if necessary
        if response.background is not None:
            await response.background()

        # Parse the function response
        if content is not None:
            result = json.loads(content)

            # Call the function
            if "name" in result:
                if tool_id in webui_app.state.TOOLS:
                    toolkit_module = webui_app.state.TOOLS[tool_id]
                else:
                    toolkit_module = load_toolkit_module_by_id(tool_id)
                    webui_app.state.TOOLS[tool_id] = toolkit_module

                function = getattr(toolkit_module, result["name"])
                function_result = None
                try:
                    if result["name"] == 'display_annual_leave_form' or "user_type" in result["parameters"]:
                        result["parameters"] = {}
                        result["parameters"]["user_type"] = 'contractual'
                        log.info(f'final resuls: {result}')
                    function_result = function(**result["parameters"])
                except Exception as e:
                    print(e)

                if function_result:
                    response = {
                        "model": data.get('model'),
                        "created_at": data.get('created'),
                        "message": {
                            "role": "assistant",
                            "content": function_result
                        },
                        "done_reason": "stop",
                        "done": True,
                    }
                    return response
    except Exception as e:
        print(f"Error from the function call response: {e}")

    return None


class RAGMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        return_citations = False

        if request.method == "POST" and (
            "/api/chat" in request.url.path or "/chat/completions" in request.url.path
        ):
            log.debug(f"request.url.path: {request.url.path}")

            # Read the original request body
            body = await request.body()
            # Decode body to string
            body_str = body.decode("utf-8")
            # Parse string to JSON
            data = json.loads(body_str) if body_str else {}

            return_citations = data.get("citations", False)
            if "citations" in data:
                del data["citations"]

            tools = Tools.get_tools()

            if tools:
                task_model_id = data["model"]
                
                user = get_current_user(
                    get_http_authorization_cred(request.headers.get("Authorization"))
                )
                prompt = get_last_user_message(data["messages"])
                context = ""

                for tool in tools:
                    response = await get_function_call_response(
                        prompt=prompt,
                        tool_id=tool.id,
                        template=TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
                        task_model_id=task_model_id,
                        user=user,
                    )

                    if response:
                        async def response_stream():
                            # Yield the response as a single JSON object
                            yield json.dumps(response)

                        # Return as StreamingResponse
                        return StreamingResponse(response_stream())

            if "docs" in data:
                data = {**data}
                data["messages"], citations = rag_messages(
                    docs=data["docs"],
                    messages=data["messages"],
                    template=rag_app.state.RAG_TEMPLATE,
                    embedding_function=rag_app.state.EMBEDDING_FUNCTION,
                    k=rag_app.state.TOP_K,
                    reranking_function=rag_app.state.sentence_transformer_rf,
                    r=rag_app.state.RELEVANCE_THRESHOLD,
                    hybrid_search=rag_app.state.ENABLE_RAG_HYBRID_SEARCH,
                )
                del data["docs"]

                log.debug(
                    f"data['messages']: {data['messages']}, citations: {citations}"
                )

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

        if return_citations:
          
            log.info(f"check score: {citations}")

            # Function to remove indices from a list if it is not None
            def remove_indices(lst, indices):
                return [item for i, item in enumerate(lst) if i not in indices]

            # Get the indices where distances are greater than 1
            indices_to_remove = [i for i, distance in enumerate(citations[0]['distances']) if distance > MAX_CITATION_DISTANCE]

            # List of keys to check and filter
            keys_to_filter = ['metadata', 'document']

            # Loop through each key and remove indices if the list is not None
            for key in keys_to_filter:
                if citations[0][key] is not None:
                    if isinstance(citations[0][key], list):
                        citations[0][key] = remove_indices(citations[0][key], indices_to_remove)

            
            # Inject the citations into the response
            if isinstance(response, StreamingResponse):
                # If it's a streaming response, inject it as SSE event or NDJSON line
                content_type = response.headers.get("Content-Type")
                if "text/event-stream" in content_type:
                    return StreamingResponse(
                        self.openai_stream_wrapper(response.body_iterator, citations),
                    )
                if "application/x-ndjson" in content_type:
                    return StreamingResponse(
                        self.ollama_stream_wrapper(response.body_iterator, citations),
                    )

        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}

    async def openai_stream_wrapper(self, original_generator, citations):
        yield f"data: {json.dumps({'citations': citations})}\n\n"
        async for data in original_generator:
            yield data

    async def ollama_stream_wrapper(self, original_generator, citations):
        yield f"{json.dumps({'citations': citations})}\n"
        async for data in original_generator:
            yield data


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
    if ENABLE_LITELLM:
        asyncio.create_task(start_litellm_background())
    # Initialize toolkits
    await initialize_toolkits()



app.mount("/api/v1", webui_app)
app.mount("/litellm/api", litellm_app)

app.mount("/ollama", ollama_app)
app.mount("/openai/api", openai_app)

app.mount("/images/api/v1", images_app)
app.mount("/audio/api/v1", audio_app)
app.mount("/rag/api/v1", rag_app)


@app.get("/api/config")
async def get_app_config():
    # Checking and Handling the Absence of 'ui' in CONFIG_DATA

    default_locale = "en-US"
    if "ui" in CONFIG_DATA:
        default_locale = CONFIG_DATA["ui"].get("default_locale", "en-US")

    # The Rest of the Function Now Uses the Variables Defined Above
    return {
        "status": True,
        "name": WEBUI_NAME,
        "version": VERSION,
        "default_locale": default_locale,
        "images": images_app.state.ENABLED,
        "default_models": webui_app.state.DEFAULT_MODELS,
        "default_prompt_suggestions": webui_app.state.DEFAULT_PROMPT_SUGGESTIONS,
        "trusted_header_auth": bool(webui_app.state.AUTH_TRUSTED_EMAIL_HEADER),
        "admin_export_enabled": ENABLE_ADMIN_EXPORT,
    }


@app.get("/api/config/model/filter")
async def get_model_filter_config(user=Depends(get_admin_user)):
    return {
        "enabled": app.state.ENABLE_MODEL_FILTER,
        "models": app.state.MODEL_FILTER_LIST,
    }


class ModelFilterConfigForm(BaseModel):
    enabled: bool
    models: List[str]


@app.post("/api/config/model/filter")
async def update_model_filter_config(
    form_data: ModelFilterConfigForm, user=Depends(get_admin_user)
):
    app.state.ENABLE_MODEL_FILTER = form_data.enabled
    app.state.MODEL_FILTER_LIST = form_data.models

    ollama_app.state.ENABLE_MODEL_FILTER = app.state.ENABLE_MODEL_FILTER
    ollama_app.state.MODEL_FILTER_LIST = app.state.MODEL_FILTER_LIST

    openai_app.state.ENABLE_MODEL_FILTER = app.state.ENABLE_MODEL_FILTER
    openai_app.state.MODEL_FILTER_LIST = app.state.MODEL_FILTER_LIST

    litellm_app.state.ENABLE_MODEL_FILTER = app.state.ENABLE_MODEL_FILTER
    litellm_app.state.MODEL_FILTER_LIST = app.state.MODEL_FILTER_LIST

    return {
        "enabled": app.state.ENABLE_MODEL_FILTER,
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
    return {key: CHANGELOG[key] for idx, key in enumerate(CHANGELOG) if idx < 5}


@app.get("/api/version/updates")
async def get_app_latest_release_version():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/repos/open-webui/open-webui/releases/latest"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["tag_name"]

                return {"current": VERSION, "latest": latest_version[1:]}
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
        )


@app.get("/manifest.json")
async def get_manifest_json():
    return {
        "name": WEBUI_NAME,
        "short_name": WEBUI_NAME,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#343541",
        "theme_color": "#343541",
        "orientation": "portrait-primary",
        "icons": [{"src": "/static/logo.png", "type": "image/png", "sizes": "500x500"}],
    }


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")

if os.path.exists(FRONTEND_BUILD_DIR):
    app.mount(
        "/",
        SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
        name="spa-static-files",
    )
else:
    log.warning(
        f"Frontend build directory not found at '{FRONTEND_BUILD_DIR}'. Serving API only."
    )


@app.on_event("shutdown")
async def shutdown_event():
    if ENABLE_LITELLM:
        await shutdown_litellm_background()

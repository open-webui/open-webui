import base64
import uuid
from contextlib import asynccontextmanager

from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
from bs4 import BeautifulSoup
import json
import markdown
import time
import os
import sys
import logging
import aiohttp
import requests
import mimetypes
import shutil
import os
import uuid
import inspect
import asyncio

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, Request, Depends, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import StreamingResponse, Response, RedirectResponse


from apps.socket.main import app as socket_app
from apps.ollama.main import (
    app as ollama_app,
    OpenAIChatCompletionForm,
    get_all_models as get_ollama_models,
    generate_openai_chat_completion as generate_ollama_chat_completion,
)
from apps.openai.main import (
    app as openai_app,
    get_all_models as get_openai_models,
    generate_chat_completion as generate_openai_chat_completion,
)

from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app
from apps.webui.main import (
    app as webui_app,
    get_pipe_models,
    generate_function_chat_completion,
)


from pydantic import BaseModel
from typing import List, Optional, Iterator, Generator, Union

from apps.webui.models.auths import Auths
from apps.webui.models.models import Models, ModelModel
from apps.webui.models.tools import Tools
from apps.webui.models.functions import Functions
from apps.webui.models.users import Users

from apps.webui.utils import load_toolkit_module_by_id, load_function_module_by_id

from utils.utils import (
    get_admin_user,
    get_verified_user,
    get_current_user,
    get_http_authorization_cred,
    get_password_hash,
    create_token,
)
from utils.task import (
    title_generation_template,
    search_query_generation_template,
    tools_function_calling_generation_template,
)
from utils.misc import (
    get_last_user_message,
    add_or_update_system_message,
    stream_message_template,
    parse_duration,
)

from apps.rag.utils import get_rag_context, rag_template

from config import (
    CONFIG_DATA,
    WEBUI_NAME,
    WEBUI_URL,
    WEBUI_AUTH,
    ENV,
    VERSION,
    CHANGELOG,
    FRONTEND_BUILD_DIR,
    UPLOAD_DIR,
    CACHE_DIR,
    STATIC_DIR,
    DEFAULT_LOCALE,
    ENABLE_OPENAI_API,
    ENABLE_OLLAMA_API,
    ENABLE_MODEL_FILTER,
    MODEL_FILTER_LIST,
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
    WEBHOOK_URL,
    ENABLE_ADMIN_EXPORT,
    WEBUI_BUILD_HASH,
    TASK_MODEL,
    TASK_MODEL_EXTERNAL,
    TITLE_GENERATION_PROMPT_TEMPLATE,
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
    SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    SAFE_MODE,
    OAUTH_PROVIDERS,
    ENABLE_OAUTH_SIGNUP,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    WEBUI_SECRET_KEY,
    WEBUI_SESSION_COOKIE_SAME_SITE,
    WEBUI_SESSION_COOKIE_SECURE,
    AppConfig,
)
from constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from utils.webhook import post_webhook

if SAFE_MODE:
    print("SAFE MODE ENABLED")
    Functions.deactivate_all_functions()


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
{f"Commit: {WEBUI_BUILD_HASH}" if WEBUI_BUILD_HASH != "dev-build" else ""}
https://github.com/open-webui/open-webui
"""
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    docs_url="/docs" if ENV == "dev" else None, redoc_url=None, lifespan=lifespan
)

app.state.config = AppConfig()

app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.ENABLE_OLLAMA_API = ENABLE_OLLAMA_API

app.state.config.ENABLE_MODEL_FILTER = ENABLE_MODEL_FILTER
app.state.config.MODEL_FILTER_LIST = MODEL_FILTER_LIST

app.state.config.WEBHOOK_URL = WEBHOOK_URL


app.state.config.TASK_MODEL = TASK_MODEL
app.state.config.TASK_MODEL_EXTERNAL = TASK_MODEL_EXTERNAL
app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = TITLE_GENERATION_PROMPT_TEMPLATE
app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE = (
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE
)
app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD = (
    SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD
)
app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
)

app.state.MODELS = {}

origins = ["*"]


##################################
#
# ChatCompletion Middleware
#
##################################


async def get_function_call_response(
    messages, files, tool_id, template, task_model_id, user
):
    tool = Tools.get_tool_by_id(tool_id)
    tools_specs = json.dumps(tool.specs, indent=2)
    content = tools_function_calling_generation_template(template, tools_specs)

    user_message = get_last_user_message(messages)
    prompt = (
        "History:\n"
        + "\n".join(
            [
                f"{message['role'].upper()}: \"\"\"{message['content']}\"\"\""
                for message in messages[::-1][:4]
            ]
        )
        + f"\nQuery: {user_message}"
    )

    print(prompt)

    payload = {
        "model": task_model_id,
        "messages": [
            {"role": "system", "content": content},
            {"role": "user", "content": f"Query: {prompt}"},
        ],
        "stream": False,
    }

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        raise e

    model = app.state.MODELS[task_model_id]

    response = None
    try:
        response = await generate_chat_completions(form_data=payload, user=user)

        content = None

        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:
                data = json.loads(chunk.decode("utf-8"))
                content = data["choices"][0]["message"]["content"]

            # Cleanup any remaining background tasks if necessary
            if response.background is not None:
                await response.background()
        else:
            content = response["choices"][0]["message"]["content"]

        # Parse the function response
        if content is not None:
            print(f"content: {content}")
            result = json.loads(content)
            print(result)

            citation = None
            # Call the function
            if "name" in result:
                if tool_id in webui_app.state.TOOLS:
                    toolkit_module = webui_app.state.TOOLS[tool_id]
                else:
                    toolkit_module, frontmatter = load_toolkit_module_by_id(tool_id)
                    webui_app.state.TOOLS[tool_id] = toolkit_module

                file_handler = False
                # check if toolkit_module has file_handler self variable
                if hasattr(toolkit_module, "file_handler"):
                    file_handler = True
                    print("file_handler: ", file_handler)

                if hasattr(toolkit_module, "valves") and hasattr(
                    toolkit_module, "Valves"
                ):
                    valves = Tools.get_tool_valves_by_id(tool_id)
                    toolkit_module.valves = toolkit_module.Valves(
                        **(valves if valves else {})
                    )

                function = getattr(toolkit_module, result["name"])
                function_result = None
                try:
                    # Get the signature of the function
                    sig = inspect.signature(function)
                    params = result["parameters"]

                    if "__user__" in sig.parameters:
                        # Call the function with the '__user__' parameter included
                        __user__ = {
                            "id": user.id,
                            "email": user.email,
                            "name": user.name,
                            "role": user.role,
                        }

                        try:
                            if hasattr(toolkit_module, "UserValves"):
                                __user__["valves"] = toolkit_module.UserValves(
                                    **Tools.get_user_valves_by_id_and_user_id(
                                        tool_id, user.id
                                    )
                                )
                        except Exception as e:
                            print(e)

                        params = {**params, "__user__": __user__}
                    if "__messages__" in sig.parameters:
                        # Call the function with the '__messages__' parameter included
                        params = {
                            **params,
                            "__messages__": messages,
                        }

                    if "__files__" in sig.parameters:
                        # Call the function with the '__files__' parameter included
                        params = {
                            **params,
                            "__files__": files,
                        }

                    if "__model__" in sig.parameters:
                        # Call the function with the '__model__' parameter included
                        params = {
                            **params,
                            "__model__": model,
                        }

                    if "__id__" in sig.parameters:
                        # Call the function with the '__id__' parameter included
                        params = {
                            **params,
                            "__id__": tool_id,
                        }

                    if inspect.iscoroutinefunction(function):
                        function_result = await function(**params)
                    else:
                        function_result = function(**params)

                    if hasattr(toolkit_module, "citation") and toolkit_module.citation:
                        citation = {
                            "source": {"name": f"TOOL:{tool.name}/{result['name']}"},
                            "document": [function_result],
                            "metadata": [{"source": result["name"]}],
                        }
                except Exception as e:
                    print(e)

                # Add the function result to the system prompt
                if function_result is not None:
                    return function_result, citation, file_handler
    except Exception as e:
        print(f"Error: {e}")

    return None, None, False


class ChatCompletionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        data_items = []

        show_citations = False
        citations = []

        if request.method == "POST" and any(
            endpoint in request.url.path
            for endpoint in ["/ollama/api/chat", "/chat/completions"]
        ):
            log.debug(f"request.url.path: {request.url.path}")

            # Read the original request body
            body = await request.body()
            body_str = body.decode("utf-8")
            data = json.loads(body_str) if body_str else {}

            user = get_current_user(
                request,
                get_http_authorization_cred(request.headers.get("Authorization")),
            )
            # Flag to skip RAG completions if file_handler is present in tools/functions
            skip_files = False
            if data.get("citations"):
                show_citations = True
                del data["citations"]

            model_id = data["model"]
            if model_id not in app.state.MODELS:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model not found",
                )
            model = app.state.MODELS[model_id]

            def get_priority(function_id):
                function = Functions.get_function_by_id(function_id)
                if function is not None and hasattr(function, "valves"):
                    return (function.valves if function.valves else {}).get(
                        "priority", 0
                    )
                return 0

            filter_ids = [
                function.id for function in Functions.get_global_filter_functions()
            ]
            if "info" in model and "meta" in model["info"]:
                filter_ids.extend(model["info"]["meta"].get("filterIds", []))
                filter_ids = list(set(filter_ids))

            enabled_filter_ids = [
                function.id
                for function in Functions.get_functions_by_type(
                    "filter", active_only=True
                )
            ]
            filter_ids = [
                filter_id for filter_id in filter_ids if filter_id in enabled_filter_ids
            ]

            filter_ids.sort(key=get_priority)
            for filter_id in filter_ids:
                filter = Functions.get_function_by_id(filter_id)
                if filter:
                    if filter_id in webui_app.state.FUNCTIONS:
                        function_module = webui_app.state.FUNCTIONS[filter_id]
                    else:
                        function_module, function_type, frontmatter = (
                            load_function_module_by_id(filter_id)
                        )
                        webui_app.state.FUNCTIONS[filter_id] = function_module

                    # Check if the function has a file_handler variable
                    if hasattr(function_module, "file_handler"):
                        skip_files = function_module.file_handler

                    if hasattr(function_module, "valves") and hasattr(
                        function_module, "Valves"
                    ):
                        valves = Functions.get_function_valves_by_id(filter_id)
                        function_module.valves = function_module.Valves(
                            **(valves if valves else {})
                        )

                    try:
                        if hasattr(function_module, "inlet"):
                            inlet = function_module.inlet

                            # Get the signature of the function
                            sig = inspect.signature(inlet)
                            params = {"body": data}

                            if "__user__" in sig.parameters:
                                __user__ = {
                                    "id": user.id,
                                    "email": user.email,
                                    "name": user.name,
                                    "role": user.role,
                                }

                                try:
                                    if hasattr(function_module, "UserValves"):
                                        __user__["valves"] = function_module.UserValves(
                                            **Functions.get_user_valves_by_id_and_user_id(
                                                filter_id, user.id
                                            )
                                        )
                                except Exception as e:
                                    print(e)

                                params = {**params, "__user__": __user__}

                            if "__id__" in sig.parameters:
                                params = {
                                    **params,
                                    "__id__": filter_id,
                                }

                            if inspect.iscoroutinefunction(inlet):
                                data = await inlet(**params)
                            else:
                                data = inlet(**params)

                    except Exception as e:
                        print(f"Error: {e}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": str(e)},
                        )

            # Set the task model
            task_model_id = data["model"]
            # Check if the user has a custom task model and use that model
            if app.state.MODELS[task_model_id]["owned_by"] == "ollama":
                if (
                    app.state.config.TASK_MODEL
                    and app.state.config.TASK_MODEL in app.state.MODELS
                ):
                    task_model_id = app.state.config.TASK_MODEL
            else:
                if (
                    app.state.config.TASK_MODEL_EXTERNAL
                    and app.state.config.TASK_MODEL_EXTERNAL in app.state.MODELS
                ):
                    task_model_id = app.state.config.TASK_MODEL_EXTERNAL

            prompt = get_last_user_message(data["messages"])
            context = ""

            # If tool_ids field is present, call the functions
            if "tool_ids" in data:
                print(data["tool_ids"])
                for tool_id in data["tool_ids"]:
                    print(tool_id)
                    try:
                        response, citation, file_handler = (
                            await get_function_call_response(
                                messages=data["messages"],
                                files=data.get("files", []),
                                tool_id=tool_id,
                                template=app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
                                task_model_id=task_model_id,
                                user=user,
                            )
                        )

                        print(file_handler)
                        if isinstance(response, str):
                            context += ("\n" if context != "" else "") + response

                        if citation:
                            citations.append(citation)
                            show_citations = True

                        if file_handler:
                            skip_files = True

                    except Exception as e:
                        print(f"Error: {e}")
                del data["tool_ids"]

                print(f"tool_context: {context}")

            # If files field is present, generate RAG completions
            # If skip_files is True, skip the RAG completions
            if "files" in data:
                if not skip_files:
                    data = {**data}
                    rag_context, rag_citations = get_rag_context(
                        files=data["files"],
                        messages=data["messages"],
                        embedding_function=rag_app.state.EMBEDDING_FUNCTION,
                        k=rag_app.state.config.TOP_K,
                        reranking_function=rag_app.state.sentence_transformer_rf,
                        r=rag_app.state.config.RELEVANCE_THRESHOLD,
                        hybrid_search=rag_app.state.config.ENABLE_RAG_HYBRID_SEARCH,
                    )
                    if rag_context:
                        context += ("\n" if context != "" else "") + rag_context

                    log.debug(f"rag_context: {rag_context}, citations: {citations}")

                    if rag_citations:
                        citations.extend(rag_citations)

                del data["files"]

            if show_citations and len(citations) > 0:
                data_items.append({"citations": citations})

            if context != "":
                system_prompt = rag_template(
                    rag_app.state.config.RAG_TEMPLATE, context, prompt
                )
                print(system_prompt)
                data["messages"] = add_or_update_system_message(
                    system_prompt, data["messages"]
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
            if isinstance(response, StreamingResponse):
                # If it's a streaming response, inject it as SSE event or NDJSON line
                content_type = response.headers.get("Content-Type")
                if "text/event-stream" in content_type:
                    return StreamingResponse(
                        self.openai_stream_wrapper(response.body_iterator, data_items),
                    )
                if "application/x-ndjson" in content_type:
                    return StreamingResponse(
                        self.ollama_stream_wrapper(response.body_iterator, data_items),
                    )

                return response
            else:
                return response

        # If it's not a chat completion request, just pass it through
        response = await call_next(request)
        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}

    async def openai_stream_wrapper(self, original_generator, data_items):
        for item in data_items:
            yield f"data: {json.dumps(item)}\n\n"

        async for data in original_generator:
            yield data

    async def ollama_stream_wrapper(self, original_generator, data_items):
        for item in data_items:
            yield f"{json.dumps(item)}\n"

        async for data in original_generator:
            yield data


app.add_middleware(ChatCompletionMiddleware)

##################################
#
# Pipeline Middleware
#
##################################


def filter_pipeline(payload, user):
    user = {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    model_id = payload["model"]
    filters = [
        model
        for model in app.state.MODELS.values()
        if "pipeline" in model
        and "type" in model["pipeline"]
        and model["pipeline"]["type"] == "filter"
        and (
            model["pipeline"]["pipelines"] == ["*"]
            or any(
                model_id == target_model_id
                for target_model_id in model["pipeline"]["pipelines"]
            )
        )
    ]
    sorted_filters = sorted(filters, key=lambda x: x["pipeline"]["priority"])

    model = app.state.MODELS[model_id]

    if "pipeline" in model:
        sorted_filters.append(model)

    for filter in sorted_filters:
        r = None
        try:
            urlIdx = filter["urlIdx"]

            url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
            key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

            if key != "":
                headers = {"Authorization": f"Bearer {key}"}
                r = requests.post(
                    f"{url}/{filter['id']}/filter/inlet",
                    headers=headers,
                    json={
                        "user": user,
                        "body": payload,
                    },
                )

                r.raise_for_status()
                payload = r.json()
        except Exception as e:
            # Handle connection error here
            print(f"Connection error: {e}")

            if r is not None:
                try:
                    res = r.json()
                except:
                    pass
                if "detail" in res:
                    raise Exception(r.status_code, res["detail"])

            else:
                pass

    if "pipeline" not in app.state.MODELS[model_id]:
        if "chat_id" in payload:
            del payload["chat_id"]

        if "title" in payload:
            del payload["title"]

        if "task" in payload:
            del payload["task"]

    return payload


class PipelineMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and (
            "/ollama/api/chat" in request.url.path
            or "/chat/completions" in request.url.path
        ):
            log.debug(f"request.url.path: {request.url.path}")

            # Read the original request body
            body = await request.body()
            # Decode body to string
            body_str = body.decode("utf-8")
            # Parse string to JSON
            data = json.loads(body_str) if body_str else {}

            user = get_current_user(
                request,
                get_http_authorization_cred(request.headers.get("Authorization")),
            )

            try:
                data = filter_pipeline(data, user)
            except Exception as e:
                return JSONResponse(
                    status_code=e.args[0],
                    content={"detail": e.args[1]},
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
        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}


app.add_middleware(PipelineMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_url(request: Request, call_next):
    if len(app.state.MODELS) == 0:
        await get_all_models()
    else:
        pass

    start_time = int(time.time())
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.middleware("http")
async def update_embedding_function(request: Request, call_next):
    response = await call_next(request)
    if "/embedding/update" in request.url.path:
        webui_app.state.EMBEDDING_FUNCTION = rag_app.state.EMBEDDING_FUNCTION
    return response


app.mount("/ws", socket_app)

app.mount("/ollama", ollama_app)
app.mount("/openai", openai_app)

app.mount("/images/api/v1", images_app)
app.mount("/audio/api/v1", audio_app)
app.mount("/rag/api/v1", rag_app)

app.mount("/api/v1", webui_app)

webui_app.state.EMBEDDING_FUNCTION = rag_app.state.EMBEDDING_FUNCTION


async def get_all_models():
    pipe_models = []
    openai_models = []
    ollama_models = []

    pipe_models = await get_pipe_models()

    if app.state.config.ENABLE_OPENAI_API:
        openai_models = await get_openai_models()
        openai_models = openai_models["data"]

    if app.state.config.ENABLE_OLLAMA_API:
        ollama_models = await get_ollama_models()
        ollama_models = [
            {
                "id": model["model"],
                "name": model["name"],
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama",
                "ollama": model,
            }
            for model in ollama_models["models"]
        ]

    models = pipe_models + openai_models + ollama_models

    custom_models = Models.get_all_models()
    for custom_model in custom_models:
        if custom_model.base_model_id == None:
            for model in models:
                if (
                    custom_model.id == model["id"]
                    or custom_model.id == model["id"].split(":")[0]
                ):
                    model["name"] = custom_model.name
                    model["info"] = custom_model.model_dump()
        else:
            owned_by = "openai"
            for model in models:
                if (
                    custom_model.base_model_id == model["id"]
                    or custom_model.base_model_id == model["id"].split(":")[0]
                ):
                    owned_by = model["owned_by"]
                    break

            models.append(
                {
                    "id": custom_model.id,
                    "name": custom_model.name,
                    "object": "model",
                    "created": custom_model.created_at,
                    "owned_by": owned_by,
                    "info": custom_model.model_dump(),
                    "preset": True,
                }
            )

    app.state.MODELS = {model["id"]: model for model in models}

    webui_app.state.MODELS = app.state.MODELS

    return models


@app.get("/api/models")
async def get_models(user=Depends(get_verified_user)):
    models = await get_all_models()

    # Filter out filter pipelines
    models = [
        model
        for model in models
        if "pipeline" not in model or model["pipeline"].get("type", None) != "filter"
    ]

    if app.state.config.ENABLE_MODEL_FILTER:
        if user.role == "user":
            models = list(
                filter(
                    lambda model: model["id"] in app.state.config.MODEL_FILTER_LIST,
                    models,
                )
            )
            return {"data": models}

    return {"data": models}


@app.post("/api/chat/completions")
async def generate_chat_completions(form_data: dict, user=Depends(get_verified_user)):
    model_id = form_data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    model = app.state.MODELS[model_id]

    pipe = model.get("pipe")
    if pipe:
        return await generate_function_chat_completion(form_data, user=user)
    if model["owned_by"] == "ollama":
        return await generate_ollama_chat_completion(form_data, user=user)
    else:
        return await generate_openai_chat_completion(form_data, user=user)


@app.post("/api/chat/completed")
async def chat_completed(form_data: dict, user=Depends(get_verified_user)):
    data = form_data
    model_id = data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    model = app.state.MODELS[model_id]

    filters = [
        model
        for model in app.state.MODELS.values()
        if "pipeline" in model
        and "type" in model["pipeline"]
        and model["pipeline"]["type"] == "filter"
        and (
            model["pipeline"]["pipelines"] == ["*"]
            or any(
                model_id == target_model_id
                for target_model_id in model["pipeline"]["pipelines"]
            )
        )
    ]

    sorted_filters = sorted(filters, key=lambda x: x["pipeline"]["priority"])
    if "pipeline" in model:
        sorted_filters = [model] + sorted_filters

    for filter in sorted_filters:
        r = None
        try:
            urlIdx = filter["urlIdx"]

            url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
            key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

            if key != "":
                headers = {"Authorization": f"Bearer {key}"}
                r = requests.post(
                    f"{url}/{filter['id']}/filter/outlet",
                    headers=headers,
                    json={
                        "user": {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role,
                        },
                        "body": data,
                    },
                )

                r.raise_for_status()
                data = r.json()
        except Exception as e:
            # Handle connection error here
            print(f"Connection error: {e}")

            if r is not None:
                try:
                    res = r.json()
                    if "detail" in res:
                        return JSONResponse(
                            status_code=r.status_code,
                            content=res,
                        )
                except:
                    pass

            else:
                pass

    def get_priority(function_id):
        function = Functions.get_function_by_id(function_id)
        if function is not None and hasattr(function, "valves"):
            return (function.valves if function.valves else {}).get("priority", 0)
        return 0

    filter_ids = [function.id for function in Functions.get_global_filter_functions()]
    if "info" in model and "meta" in model["info"]:
        filter_ids.extend(model["info"]["meta"].get("filterIds", []))
        filter_ids = list(set(filter_ids))

    enabled_filter_ids = [
        function.id
        for function in Functions.get_functions_by_type("filter", active_only=True)
    ]
    filter_ids = [
        filter_id for filter_id in filter_ids if filter_id in enabled_filter_ids
    ]

    # Sort filter_ids by priority, using the get_priority function
    filter_ids.sort(key=get_priority)

    for filter_id in filter_ids:
        filter = Functions.get_function_by_id(filter_id)
        if filter:
            if filter_id in webui_app.state.FUNCTIONS:
                function_module = webui_app.state.FUNCTIONS[filter_id]
            else:
                function_module, function_type, frontmatter = (
                    load_function_module_by_id(filter_id)
                )
                webui_app.state.FUNCTIONS[filter_id] = function_module

            if hasattr(function_module, "valves") and hasattr(
                function_module, "Valves"
            ):
                valves = Functions.get_function_valves_by_id(filter_id)
                function_module.valves = function_module.Valves(
                    **(valves if valves else {})
                )

            try:
                if hasattr(function_module, "outlet"):
                    outlet = function_module.outlet

                    # Get the signature of the function
                    sig = inspect.signature(outlet)
                    params = {"body": data}

                    if "__user__" in sig.parameters:
                        __user__ = {
                            "id": user.id,
                            "email": user.email,
                            "name": user.name,
                            "role": user.role,
                        }

                        try:
                            if hasattr(function_module, "UserValves"):
                                __user__["valves"] = function_module.UserValves(
                                    **Functions.get_user_valves_by_id_and_user_id(
                                        filter_id, user.id
                                    )
                                )
                        except Exception as e:
                            print(e)

                        params = {**params, "__user__": __user__}

                    if "__id__" in sig.parameters:
                        params = {
                            **params,
                            "__id__": filter_id,
                        }

                    if inspect.iscoroutinefunction(outlet):
                        data = await outlet(**params)
                    else:
                        data = outlet(**params)

            except Exception as e:
                print(f"Error: {e}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": str(e)},
                )

    return data


##################################
#
# Task Endpoints
#
##################################


# TODO: Refactor task API endpoints below into a separate file


@app.get("/api/task/config")
async def get_task_config(user=Depends(get_verified_user)):
    return {
        "TASK_MODEL": app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": app.state.config.TASK_MODEL_EXTERNAL,
        "TITLE_GENERATION_PROMPT_TEMPLATE": app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE": app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
        "SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD": app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


class TaskConfigForm(BaseModel):
    TASK_MODEL: Optional[str]
    TASK_MODEL_EXTERNAL: Optional[str]
    TITLE_GENERATION_PROMPT_TEMPLATE: str
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE: str
    SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD: int
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: str


@app.post("/api/task/config/update")
async def update_task_config(form_data: TaskConfigForm, user=Depends(get_admin_user)):
    app.state.config.TASK_MODEL = form_data.TASK_MODEL
    app.state.config.TASK_MODEL_EXTERNAL = form_data.TASK_MODEL_EXTERNAL
    app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = (
        form_data.TITLE_GENERATION_PROMPT_TEMPLATE
    )
    app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE = (
        form_data.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE
    )
    app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD = (
        form_data.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD
    )
    app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
        form_data.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    )

    return {
        "TASK_MODEL": app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": app.state.config.TASK_MODEL_EXTERNAL,
        "TITLE_GENERATION_PROMPT_TEMPLATE": app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE": app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
        "SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD": app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


@app.post("/api/task/title/completions")
async def generate_title(form_data: dict, user=Depends(get_verified_user)):
    print("generate_title")

    model_id = form_data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    if app.state.MODELS[model_id]["owned_by"] == "ollama":
        if app.state.config.TASK_MODEL:
            task_model_id = app.state.config.TASK_MODEL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id
    else:
        if app.state.config.TASK_MODEL_EXTERNAL:
            task_model_id = app.state.config.TASK_MODEL_EXTERNAL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id

    print(model_id)
    model = app.state.MODELS[model_id]

    template = app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE

    content = title_generation_template(
        template,
        form_data["prompt"],
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "max_tokens": 50,
        "chat_id": form_data.get("chat_id", None),
        "title": True,
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )

    return await generate_chat_completions(form_data=payload, user=user)


@app.post("/api/task/query/completions")
async def generate_search_query(form_data: dict, user=Depends(get_verified_user)):
    print("generate_search_query")

    if len(form_data["prompt"]) < app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skip search query generation for short prompts (< {app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD} characters)",
        )

    model_id = form_data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    if app.state.MODELS[model_id]["owned_by"] == "ollama":
        if app.state.config.TASK_MODEL:
            task_model_id = app.state.config.TASK_MODEL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id
    else:
        if app.state.config.TASK_MODEL_EXTERNAL:
            task_model_id = app.state.config.TASK_MODEL_EXTERNAL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id

    print(model_id)
    model = app.state.MODELS[model_id]

    template = app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE

    content = search_query_generation_template(
        template, form_data["prompt"], {"name": user.name}
    )

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "max_tokens": 30,
        "task": True,
    }

    print(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )

    return await generate_chat_completions(form_data=payload, user=user)


@app.post("/api/task/emoji/completions")
async def generate_emoji(form_data: dict, user=Depends(get_verified_user)):
    print("generate_emoji")

    model_id = form_data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    if app.state.MODELS[model_id]["owned_by"] == "ollama":
        if app.state.config.TASK_MODEL:
            task_model_id = app.state.config.TASK_MODEL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id
    else:
        if app.state.config.TASK_MODEL_EXTERNAL:
            task_model_id = app.state.config.TASK_MODEL_EXTERNAL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id

    print(model_id)
    model = app.state.MODELS[model_id]

    template = '''
Your task is to reflect the speaker's likely facial expression through a fitting emoji. Interpret emotions from the message and reflect their facial expression using fitting, diverse emojis (e.g., 😊, 😢, 😡, 😱).

Message: """{{prompt}}"""
'''

    content = title_generation_template(
        template,
        form_data["prompt"],
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "max_tokens": 4,
        "chat_id": form_data.get("chat_id", None),
        "task": True,
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )

    return await generate_chat_completions(form_data=payload, user=user)


@app.post("/api/task/tools/completions")
async def get_tools_function_calling(form_data: dict, user=Depends(get_verified_user)):
    print("get_tools_function_calling")

    model_id = form_data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    if app.state.MODELS[model_id]["owned_by"] == "ollama":
        if app.state.config.TASK_MODEL:
            task_model_id = app.state.config.TASK_MODEL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id
    else:
        if app.state.config.TASK_MODEL_EXTERNAL:
            task_model_id = app.state.config.TASK_MODEL_EXTERNAL
            if task_model_id in app.state.MODELS:
                model_id = task_model_id

    print(model_id)
    template = app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

    try:
        context, citation, file_handler = await get_function_call_response(
            form_data["messages"],
            form_data.get("files", []),
            form_data["tool_id"],
            template,
            model_id,
            user,
        )
        return context
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )


##################################
#
# Pipelines Endpoints
#
##################################


# TODO: Refactor pipelines API endpoints below into a separate file


@app.get("/api/pipelines/list")
async def get_pipelines_list(user=Depends(get_admin_user)):
    responses = await get_openai_models(raw=True)

    print(responses)
    urlIdxs = [
        idx
        for idx, response in enumerate(responses)
        if response != None and "pipelines" in response
    ]

    return {
        "data": [
            {
                "url": openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx],
                "idx": urlIdx,
            }
            for urlIdx in urlIdxs
        ]
    }


@app.post("/api/pipelines/upload")
async def upload_pipeline(
    urlIdx: int = Form(...), file: UploadFile = File(...), user=Depends(get_admin_user)
):
    print("upload_pipeline", urlIdx, file.filename)
    # Check if the uploaded file is a python file
    if not file.filename.endswith(".py"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Python (.py) files are allowed.",
        )

    upload_folder = f"{CACHE_DIR}/pipelines"
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, file.filename)

    try:
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}

        with open(file_path, "rb") as f:
            files = {"file": f}
            r = requests.post(f"{url}/pipelines/upload", headers=headers, files=files)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )
    finally:
        # Ensure the file is deleted after the upload is completed or on failure
        if os.path.exists(file_path):
            os.remove(file_path)


class AddPipelineForm(BaseModel):
    url: str
    urlIdx: int


@app.post("/api/pipelines/add")
async def add_pipeline(form_data: AddPipelineForm, user=Depends(get_admin_user)):

    r = None
    try:
        urlIdx = form_data.urlIdx

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.post(
            f"{url}/pipelines/add", headers=headers, json={"url": form_data.url}
        )

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


class DeletePipelineForm(BaseModel):
    id: str
    urlIdx: int


@app.delete("/api/pipelines/delete")
async def delete_pipeline(form_data: DeletePipelineForm, user=Depends(get_admin_user)):

    r = None
    try:
        urlIdx = form_data.urlIdx

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.delete(
            f"{url}/pipelines/delete", headers=headers, json={"id": form_data.id}
        )

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.get("/api/pipelines")
async def get_pipelines(urlIdx: Optional[int] = None, user=Depends(get_admin_user)):
    r = None
    try:
        urlIdx

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/pipelines", headers=headers)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.get("/api/pipelines/{pipeline_id}/valves")
async def get_pipeline_valves(
    urlIdx: Optional[int], pipeline_id: str, user=Depends(get_admin_user)
):
    models = await get_all_models()
    r = None
    try:

        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/{pipeline_id}/valves", headers=headers)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"

        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.get("/api/pipelines/{pipeline_id}/valves/spec")
async def get_pipeline_valves_spec(
    urlIdx: Optional[int], pipeline_id: str, user=Depends(get_admin_user)
):
    models = await get_all_models()

    r = None
    try:
        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/{pipeline_id}/valves/spec", headers=headers)

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


@app.post("/api/pipelines/{pipeline_id}/valves/update")
async def update_pipeline_valves(
    urlIdx: Optional[int],
    pipeline_id: str,
    form_data: dict,
    user=Depends(get_admin_user),
):
    models = await get_all_models()

    r = None
    try:
        url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
        key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

        headers = {"Authorization": f"Bearer {key}"}
        r = requests.post(
            f"{url}/{pipeline_id}/valves/update",
            headers=headers,
            json={**form_data},
        )

        r.raise_for_status()
        data = r.json()

        return {**data}
    except Exception as e:
        # Handle connection error here
        print(f"Connection error: {e}")

        detail = "Pipeline not found"

        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=(r.status_code if r is not None else status.HTTP_404_NOT_FOUND),
            detail=detail,
        )


##################################
#
# Config Endpoints
#
##################################


@app.get("/api/config")
async def get_app_config():
    return {
        "status": True,
        "name": WEBUI_NAME,
        "version": VERSION,
        "default_locale": str(DEFAULT_LOCALE),
        "default_models": webui_app.state.config.DEFAULT_MODELS,
        "default_prompt_suggestions": webui_app.state.config.DEFAULT_PROMPT_SUGGESTIONS,
        "features": {
            "auth": WEBUI_AUTH,
            "auth_trusted_header": bool(webui_app.state.AUTH_TRUSTED_EMAIL_HEADER),
            "enable_signup": webui_app.state.config.ENABLE_SIGNUP,
            "enable_web_search": rag_app.state.config.ENABLE_RAG_WEB_SEARCH,
            "enable_image_generation": images_app.state.config.ENABLED,
            "enable_community_sharing": webui_app.state.config.ENABLE_COMMUNITY_SHARING,
            "enable_admin_export": ENABLE_ADMIN_EXPORT,
        },
        "audio": {
            "tts": {
                "engine": audio_app.state.config.TTS_ENGINE,
                "voice": audio_app.state.config.TTS_VOICE,
            },
            "stt": {
                "engine": audio_app.state.config.STT_ENGINE,
            },
        },
        "oauth": {
            "providers": {
                name: config.get("name", name)
                for name, config in OAUTH_PROVIDERS.items()
            }
        },
    }


@app.get("/api/config/model/filter")
async def get_model_filter_config(user=Depends(get_admin_user)):
    return {
        "enabled": app.state.config.ENABLE_MODEL_FILTER,
        "models": app.state.config.MODEL_FILTER_LIST,
    }


class ModelFilterConfigForm(BaseModel):
    enabled: bool
    models: List[str]


@app.post("/api/config/model/filter")
async def update_model_filter_config(
    form_data: ModelFilterConfigForm, user=Depends(get_admin_user)
):
    app.state.config.ENABLE_MODEL_FILTER = form_data.enabled
    app.state.config.MODEL_FILTER_LIST = form_data.models

    return {
        "enabled": app.state.config.ENABLE_MODEL_FILTER,
        "models": app.state.config.MODEL_FILTER_LIST,
    }


# TODO: webhook endpoint should be under config endpoints


@app.get("/api/webhook")
async def get_webhook_url(user=Depends(get_admin_user)):
    return {
        "url": app.state.config.WEBHOOK_URL,
    }


class UrlForm(BaseModel):
    url: str


@app.post("/api/webhook")
async def update_webhook_url(form_data: UrlForm, user=Depends(get_admin_user)):
    app.state.config.WEBHOOK_URL = form_data.url
    webui_app.state.WEBHOOK_URL = app.state.config.WEBHOOK_URL
    return {"url": app.state.config.WEBHOOK_URL}


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
        async with aiohttp.ClientSession(trust_env=True) as session:
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


############################
# OAuth Login & Callback
############################

oauth = OAuth()

for provider_name, provider_config in OAUTH_PROVIDERS.items():
    oauth.register(
        name=provider_name,
        client_id=provider_config["client_id"],
        client_secret=provider_config["client_secret"],
        server_metadata_url=provider_config["server_metadata_url"],
        client_kwargs={
            "scope": provider_config["scope"],
        },
    )

# SessionMiddleware is used by authlib for oauth
if len(OAUTH_PROVIDERS) > 0:
    app.add_middleware(
        SessionMiddleware,
        secret_key=WEBUI_SECRET_KEY,
        session_cookie="oui-session",
        same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
        https_only=WEBUI_SESSION_COOKIE_SECURE,
    )


@app.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(404)
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)


# OAuth login logic is as follows:
# 1. Attempt to find a user with matching subject ID, tied to the provider
# 2. If OAUTH_MERGE_ACCOUNTS_BY_EMAIL is true, find a user with the email address provided via OAuth
#    - This is considered insecure in general, as OAuth providers do not always verify email addresses
# 3. If there is no user, and ENABLE_OAUTH_SIGNUP is true, create a user
#    - Email addresses are considered unique, so we fail registration if the email address is alreayd taken
@app.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, response: Response):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(404)
    client = oauth.create_client(provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        log.warning(f"OAuth callback error: {e}")
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
    user_data: UserInfo = token["userinfo"]

    sub = user_data.get("sub")
    if not sub:
        log.warning(f"OAuth callback failed, sub is missing: {user_data}")
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
    provider_sub = f"{provider}@{sub}"
    email = user_data.get("email", "").lower()
    # We currently mandate that email addresses are provided
    if not email:
        log.warning(f"OAuth callback failed, email is missing: {user_data}")
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

    # Check if the user exists
    user = Users.get_user_by_oauth_sub(provider_sub)

    if not user:
        # If the user does not exist, check if merging is enabled
        if OAUTH_MERGE_ACCOUNTS_BY_EMAIL.value:
            # Check if the user exists by email
            user = Users.get_user_by_email(email)
            if user:
                # Update the user with the new oauth sub
                Users.update_user_oauth_sub_by_id(user.id, provider_sub)

    if not user:
        # If the user does not exist, check if signups are enabled
        if ENABLE_OAUTH_SIGNUP.value:
            # Check if an existing user with the same email already exists
            existing_user = Users.get_user_by_email(user_data.get("email", "").lower())
            if existing_user:
                raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

            picture_url = user_data.get("picture", "")
            if picture_url:
                # Download the profile image into a base64 string
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(picture_url) as resp:
                            picture = await resp.read()
                            base64_encoded_picture = base64.b64encode(picture).decode(
                                "utf-8"
                            )
                            guessed_mime_type = mimetypes.guess_type(picture_url)[0]
                            if guessed_mime_type is None:
                                # assume JPG, browsers are tolerant enough of image formats
                                guessed_mime_type = "image/jpeg"
                            picture_url = f"data:{guessed_mime_type};base64,{base64_encoded_picture}"
                except Exception as e:
                    log.error(f"Error downloading profile image '{picture_url}': {e}")
                    picture_url = ""
            if not picture_url:
                picture_url = "/user.png"
            role = (
                "admin"
                if Users.get_num_users() == 0
                else webui_app.state.config.DEFAULT_USER_ROLE
            )
            user = Auths.insert_new_auth(
                email=email,
                password=get_password_hash(
                    str(uuid.uuid4())
                ),  # Random password, not used
                name=user_data.get("name", "User"),
                profile_image_url=picture_url,
                role=role,
                oauth_sub=provider_sub,
            )

            if webui_app.state.config.WEBHOOK_URL:
                post_webhook(
                    webui_app.state.config.WEBHOOK_URL,
                    WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                    {
                        "action": "signup",
                        "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        "user": user.model_dump_json(exclude_none=True),
                    },
                )
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )

    jwt_token = create_token(
        data={"id": user.id},
        expires_delta=parse_duration(webui_app.state.config.JWT_EXPIRES_IN),
    )

    # Set the cookie token
    response.set_cookie(
        key="token",
        value=jwt_token,
        httponly=True,  # Ensures the cookie is not accessible via JavaScript
    )

    # Redirect back to the frontend with the JWT token
    redirect_url = f"{request.base_url}auth#token={jwt_token}"
    return RedirectResponse(url=redirect_url)


@app.get("/manifest.json")
async def get_manifest_json():
    return {
        "name": WEBUI_NAME,
        "short_name": WEBUI_NAME,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#343541",
        "orientation": "portrait-primary",
        "icons": [{"src": "/static/logo.png", "type": "image/png", "sizes": "500x500"}],
    }


@app.get("/opensearch.xml")
async def get_opensearch_xml():
    xml_content = rf"""
    <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/" xmlns:moz="http://www.mozilla.org/2006/browser/search/">
    <ShortName>{WEBUI_NAME}</ShortName>
    <Description>Search {WEBUI_NAME}</Description>
    <InputEncoding>UTF-8</InputEncoding>
    <Image width="16" height="16" type="image/x-icon">{WEBUI_URL}/favicon.png</Image>
    <Url type="text/html" method="get" template="{WEBUI_URL}/?q={"{searchTerms}"}"/>
    <moz:SearchForm>{WEBUI_URL}</moz:SearchForm>
    </OpenSearchDescription>
    """
    return Response(content=xml_content, media_type="application/xml")


@app.get("/health")
async def healthcheck():
    return {"status": True}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")

if os.path.exists(FRONTEND_BUILD_DIR):
    mimetypes.add_type("text/javascript", ".js")
    app.mount(
        "/",
        SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
        name="spa-static-files",
    )
else:
    log.warning(
        f"Frontend build directory not found at '{FRONTEND_BUILD_DIR}'. Serving API only."
    )

import base64
import uuid
from contextlib import asynccontextmanager

from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
import json
import time
import os
import sys
import logging
import aiohttp
import requests
import mimetypes
import shutil
import inspect

from fastapi import FastAPI, Request, Depends, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import StreamingResponse, Response, RedirectResponse


from apps.socket.main import app as socket_app, get_event_emitter, get_event_call
from apps.ollama.main import (
    app as ollama_app,
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
from apps.webui.internal.db import Session


from pydantic import BaseModel
from typing import List, Optional

from apps.webui.models.auths import Auths
from apps.webui.models.models import Models
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
    prepend_to_first_user_message_content,
    parse_duration,
)

from apps.rag.utils import get_rag_context, rag_template

from config import (
    WEBUI_NAME,
    WEBUI_URL,
    WEBUI_AUTH,
    ENV,
    VERSION,
    CHANGELOG,
    FRONTEND_BUILD_DIR,
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

from constants import ERROR_MESSAGES, WEBHOOK_MESSAGES, TASKS
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


def run_migrations():
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
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


async def get_body_and_model_and_user(request):
    # Read the original request body
    body = await request.body()
    body_str = body.decode("utf-8")
    body = json.loads(body_str) if body_str else {}

    model_id = body["model"]
    if model_id not in app.state.MODELS:
        raise Exception("Model not found")
    model = app.state.MODELS[model_id]

    user = get_current_user(
        request,
        get_http_authorization_cred(request.headers.get("Authorization")),
    )

    return body, model, user


def get_task_model_id(default_model_id):
    # Set the task model
    task_model_id = default_model_id
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

    return task_model_id


def get_filter_function_ids(model):
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

    filter_ids.sort(key=get_priority)
    return filter_ids


async def get_function_call_response(
    messages,
    files,
    tool_id,
    template,
    task_model_id,
    user,
    __event_emitter__=None,
    __event_call__=None,
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
        "task": str(TASKS.FUNCTION_CALLING),
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

        if content is None:
            return None, None, False

        # Parse the function response
        print(f"content: {content}")
        result = json.loads(content)
        print(result)

        citation = None

        if "name" not in result:
            return None, None, False

        # Call the function
        if tool_id in webui_app.state.TOOLS:
            toolkit_module = webui_app.state.TOOLS[tool_id]
        else:
            toolkit_module, _ = load_toolkit_module_by_id(tool_id)
            webui_app.state.TOOLS[tool_id] = toolkit_module

        file_handler = False
        # check if toolkit_module has file_handler self variable
        if hasattr(toolkit_module, "file_handler"):
            file_handler = True
            print("file_handler: ", file_handler)

        if hasattr(toolkit_module, "valves") and hasattr(toolkit_module, "Valves"):
            valves = Tools.get_tool_valves_by_id(tool_id)
            toolkit_module.valves = toolkit_module.Valves(**(valves if valves else {}))

        function = getattr(toolkit_module, result["name"])
        function_result = None
        try:
            # Get the signature of the function
            sig = inspect.signature(function)
            params = result["parameters"]

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": tool_id,
                "__messages__": messages,
                "__files__": files,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

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
                            **Tools.get_user_valves_by_id_and_user_id(tool_id, user.id)
                        )
                except Exception as e:
                    print(e)

                params = {**params, "__user__": __user__}

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


async def chat_completion_functions_handler(
    body, model, user, __event_emitter__, __event_call__
):
    skip_files = None

    filter_ids = get_filter_function_ids(model)
    for filter_id in filter_ids:
        filter = Functions.get_function_by_id(filter_id)
        if not filter:
            continue

        if filter_id in webui_app.state.FUNCTIONS:
            function_module = webui_app.state.FUNCTIONS[filter_id]
        else:
            function_module, _, _ = load_function_module_by_id(filter_id)
            webui_app.state.FUNCTIONS[filter_id] = function_module

        # Check if the function has a file_handler variable
        if hasattr(function_module, "file_handler"):
            skip_files = function_module.file_handler

        if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
            valves = Functions.get_function_valves_by_id(filter_id)
            function_module.valves = function_module.Valves(
                **(valves if valves else {})
            )

        if not hasattr(function_module, "inlet"):
            continue

        try:
            inlet = function_module.inlet

            # Get the signature of the function
            sig = inspect.signature(inlet)
            params = {"body": body}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": filter_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

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

            if inspect.iscoroutinefunction(inlet):
                body = await inlet(**params)
            else:
                body = inlet(**params)

        except Exception as e:
            print(f"Error: {e}")
            raise e

    if skip_files:
        if "files" in body:
            del body["files"]

    return body, {}


async def chat_completion_tools_handler(body, user, __event_emitter__, __event_call__):
    skip_files = None

    contexts = []
    citations = None

    task_model_id = get_task_model_id(body["model"])

    # If tool_ids field is present, call the functions
    if "tool_ids" in body:
        print(body["tool_ids"])
        for tool_id in body["tool_ids"]:
            print(tool_id)
            try:
                response, citation, file_handler = await get_function_call_response(
                    messages=body["messages"],
                    files=body.get("files", []),
                    tool_id=tool_id,
                    template=app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
                    task_model_id=task_model_id,
                    user=user,
                    __event_emitter__=__event_emitter__,
                    __event_call__=__event_call__,
                )

                print(file_handler)
                if isinstance(response, str):
                    contexts.append(response)

                if citation:
                    if citations is None:
                        citations = [citation]
                    else:
                        citations.append(citation)

                if file_handler:
                    skip_files = True

            except Exception as e:
                print(f"Error: {e}")
        del body["tool_ids"]
        print(f"tool_contexts: {contexts}")

    if skip_files:
        if "files" in body:
            del body["files"]

    return body, {
        **({"contexts": contexts} if contexts is not None else {}),
        **({"citations": citations} if citations is not None else {}),
    }


async def chat_completion_files_handler(body):
    contexts = []
    citations = None

    if "files" in body:
        files = body["files"]
        del body["files"]

        contexts, citations = get_rag_context(
            files=files,
            messages=body["messages"],
            embedding_function=rag_app.state.EMBEDDING_FUNCTION,
            k=rag_app.state.config.TOP_K,
            reranking_function=rag_app.state.sentence_transformer_rf,
            r=rag_app.state.config.RELEVANCE_THRESHOLD,
            hybrid_search=rag_app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        )

        log.debug(f"rag_contexts: {contexts}, citations: {citations}")

    return body, {
        **({"contexts": contexts} if contexts is not None else {}),
        **({"citations": citations} if citations is not None else {}),
    }


class ChatCompletionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and any(
            endpoint in request.url.path
            for endpoint in ["/ollama/api/chat", "/chat/completions"]
        ):
            log.debug(f"request.url.path: {request.url.path}")

            try:
                body, model, user = await get_body_and_model_and_user(request)
            except Exception as e:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": str(e)},
                )

            metadata = {
                "chat_id": body.pop("chat_id", None),
                "message_id": body.pop("id", None),
                "session_id": body.pop("session_id", None),
                "valves": body.pop("valves", None),
            }

            __event_emitter__ = get_event_emitter(metadata)
            __event_call__ = get_event_call(metadata)

            # Initialize data_items to store additional data to be sent to the client
            data_items = []

            # Initialize context, and citations
            contexts = []
            citations = []

            try:
                body, flags = await chat_completion_functions_handler(
                    body, model, user, __event_emitter__, __event_call__
                )
            except Exception as e:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": str(e)},
                )

            try:
                body, flags = await chat_completion_tools_handler(
                    body, user, __event_emitter__, __event_call__
                )

                contexts.extend(flags.get("contexts", []))
                citations.extend(flags.get("citations", []))
            except Exception as e:
                print(e)
                pass

            try:
                body, flags = await chat_completion_files_handler(body)

                contexts.extend(flags.get("contexts", []))
                citations.extend(flags.get("citations", []))
            except Exception as e:
                print(e)
                pass

            # If context is not empty, insert it into the messages
            if len(contexts) > 0:
                context_string = "/n".join(contexts).strip()
                prompt = get_last_user_message(body["messages"])

                # Workaround for Ollama 2.0+ system prompt issue
                # TODO: replace with add_or_update_system_message
                if model["owned_by"] == "ollama":
                    body["messages"] = prepend_to_first_user_message_content(
                        rag_template(
                            rag_app.state.config.RAG_TEMPLATE, context_string, prompt
                        ),
                        body["messages"],
                    )
                else:
                    body["messages"] = add_or_update_system_message(
                        rag_template(
                            rag_app.state.config.RAG_TEMPLATE, context_string, prompt
                        ),
                        body["messages"],
                    )

            # If there are citations, add them to the data_items
            if len(citations) > 0:
                data_items.append({"citations": citations})

            body["metadata"] = metadata
            modified_body_bytes = json.dumps(body).encode("utf-8")
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


def get_sorted_filters(model_id):
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
    return sorted_filters


def filter_pipeline(payload, user):
    user = {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    model_id = payload["model"]
    sorted_filters = get_sorted_filters(model_id)

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
                res = r.json()
                if "detail" in res:
                    raise Exception(r.status_code, res["detail"])

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
async def commit_session_after_request(request: Request, call_next):
    response = await call_next(request)
    log.debug("Commit session after request")
    Session.commit()
    return response


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
    # TODO: Optimize this function
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

    global_action_ids = [
        function.id for function in Functions.get_global_action_functions()
    ]
    enabled_action_ids = [
        function.id
        for function in Functions.get_functions_by_type("action", active_only=True)
    ]

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

                    action_ids = []
                    if "info" in model and "meta" in model["info"]:
                        action_ids.extend(model["info"]["meta"].get("actionIds", []))

                    model["action_ids"] = action_ids
        else:
            owned_by = "openai"
            pipe = None
            action_ids = []

            for model in models:
                if (
                    custom_model.base_model_id == model["id"]
                    or custom_model.base_model_id == model["id"].split(":")[0]
                ):
                    owned_by = model["owned_by"]
                    if "pipe" in model:
                        pipe = model["pipe"]

                    if "info" in model and "meta" in model["info"]:
                        action_ids.extend(model["info"]["meta"].get("actionIds", []))
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
                    **({"pipe": pipe} if pipe is not None else {}),
                    "action_ids": action_ids,
                }
            )

    for model in models:
        action_ids = []
        if "action_ids" in model:
            action_ids = model["action_ids"]
            del model["action_ids"]

        action_ids = action_ids + global_action_ids
        action_ids = list(set(action_ids))
        action_ids = [
            action_id for action_id in action_ids if action_id in enabled_action_ids
        ]

        model["actions"] = []
        for action_id in action_ids:
            action = Functions.get_function_by_id(action_id)

            if action_id in webui_app.state.FUNCTIONS:
                function_module = webui_app.state.FUNCTIONS[action_id]
            else:
                function_module, _, _ = load_function_module_by_id(action_id)
                webui_app.state.FUNCTIONS[action_id] = function_module

            if hasattr(function_module, "actions"):
                actions = function_module.actions
                model["actions"].extend(
                    [
                        {
                            "id": f"{action_id}.{_action['id']}",
                            "name": _action.get(
                                "name", f"{action.name} ({_action['id']})"
                            ),
                            "description": action.meta.description,
                            "icon_url": _action.get(
                                "icon_url", action.meta.manifest.get("icon_url", None)
                            ),
                        }
                        for _action in actions
                    ]
                )
            else:
                model["actions"].append(
                    {
                        "id": action_id,
                        "name": action.name,
                        "description": action.meta.description,
                        "icon_url": action.meta.manifest.get("icon_url", None),
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

    # `task` field is used to determine the type of the request, e.g. `title_generation`, `query_generation`, etc.
    task = None
    if "task" in form_data:
        task = form_data["task"]
        del form_data["task"]

    if task:
        if "metadata" in form_data:
            form_data["metadata"]["task"] = task
        else:
            form_data["metadata"] = {"task": task}

    if model.get("pipe"):
        return await generate_function_chat_completion(form_data, user=user)
    if model["owned_by"] == "ollama":
        print("generate_ollama_chat_completion")
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

    sorted_filters = get_sorted_filters(model_id)
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
                except Exception:
                    pass

            else:
                pass

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )

    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )

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
        if not filter:
            continue

        if filter_id in webui_app.state.FUNCTIONS:
            function_module = webui_app.state.FUNCTIONS[filter_id]
        else:
            function_module, _, _ = load_function_module_by_id(filter_id)
            webui_app.state.FUNCTIONS[filter_id] = function_module

        if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
            valves = Functions.get_function_valves_by_id(filter_id)
            function_module.valves = function_module.Valves(
                **(valves if valves else {})
            )

        if not hasattr(function_module, "outlet"):
            continue
        try:
            outlet = function_module.outlet

            # Get the signature of the function
            sig = inspect.signature(outlet)
            params = {"body": data}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": filter_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

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


@app.post("/api/chat/actions/{action_id}")
async def chat_action(action_id: str, form_data: dict, user=Depends(get_verified_user)):
    if "." in action_id:
        action_id, sub_action_id = action_id.split(".")
    else:
        sub_action_id = None

    action = Functions.get_function_by_id(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    data = form_data
    model_id = data["model"]
    if model_id not in app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    model = app.state.MODELS[model_id]

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )
    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )

    if action_id in webui_app.state.FUNCTIONS:
        function_module = webui_app.state.FUNCTIONS[action_id]
    else:
        function_module, _, _ = load_function_module_by_id(action_id)
        webui_app.state.FUNCTIONS[action_id] = function_module

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(action_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))

    if hasattr(function_module, "action"):
        try:
            action = function_module.action

            # Get the signature of the function
            sig = inspect.signature(action)
            params = {"body": data}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": sub_action_id if sub_action_id is not None else action_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

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
                                action_id, user.id
                            )
                        )
                except Exception as e:
                    print(e)

                params = {**params, "__user__": __user__}

            if inspect.iscoroutinefunction(action):
                data = await action(**params)
            else:
                data = action(**params)

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
    model_id = get_task_model_id(model_id)

    print(model_id)

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
        "task": str(TASKS.TITLE_GENERATION),
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )

    if "chat_id" in payload:
        del payload["chat_id"]

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
    model_id = get_task_model_id(model_id)

    print(model_id)

    template = app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE

    content = search_query_generation_template(
        template, form_data["prompt"], {"name": user.name}
    )

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "max_tokens": 30,
        "task": str(TASKS.QUERY_GENERATION),
    }

    print(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )

    if "chat_id" in payload:
        del payload["chat_id"]

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
    model_id = get_task_model_id(model_id)

    print(model_id)

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
        "task": str(TASKS.EMOJI_GENERATION),
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        return JSONResponse(
            status_code=e.args[0],
            content={"detail": e.args[1]},
        )

    if "chat_id" in payload:
        del payload["chat_id"]

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
    model_id = get_task_model_id(model_id)

    print(model_id)
    template = app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

    try:
        context, _, _ = await get_function_call_response(
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

    r = None
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
        status_code = status.HTTP_404_NOT_FOUND
        if r is not None:
            status_code = r.status_code
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except:
                pass

        raise HTTPException(
            status_code=status_code,
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
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
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
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
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
            "enable_login_form": webui_app.state.config.ENABLE_LOGIN_FORM,
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
        redirect_uri=provider_config["redirect_uri"],
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
    # If the provider has a custom redirect URL, use that, otherwise automatically generate one
    redirect_uri = OAUTH_PROVIDERS[provider].get("redirect_uri") or request.url_for(
        "oauth_callback", provider=provider
    )
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

            picture_claim = webui_app.state.config.OAUTH_PICTURE_CLAIM
            picture_url = user_data.get(picture_claim, "")
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
            username_claim = webui_app.state.config.OAUTH_USERNAME_CLAIM
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
                name=user_data.get(username_claim, "User"),
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
    <Image width="16" height="16" type="image/x-icon">{WEBUI_URL}/static/favicon.png</Image>
    <Url type="text/html" method="get" template="{WEBUI_URL}/?q={"{searchTerms}"}"/>
    <moz:SearchForm>{WEBUI_URL}</moz:SearchForm>
    </OpenSearchDescription>
    """
    return Response(content=xml_content, media_type="application/xml")


@app.get("/health")
async def healthcheck():
    return {"status": True}


@app.get("/health/db")
async def healthcheck_with_db():
    Session.execute(text("SELECT 1;")).all()
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

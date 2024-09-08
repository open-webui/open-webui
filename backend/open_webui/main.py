import base64
import inspect
import json
import logging
import mimetypes
import os
import shutil
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import aiohttp
import requests


from open_webui.apps.audio.main import app as audio_app
from open_webui.apps.images.main import app as images_app
from open_webui.apps.ollama.main import app as ollama_app
from open_webui.apps.ollama.main import (
    generate_openai_chat_completion as generate_ollama_chat_completion,
)
from open_webui.apps.ollama.main import get_all_models as get_ollama_models
from open_webui.apps.openai.main import app as openai_app
from open_webui.apps.openai.main import (
    generate_chat_completion as generate_openai_chat_completion,
)
from open_webui.apps.openai.main import get_all_models as get_openai_models
from open_webui.apps.rag.main import app as rag_app
from open_webui.apps.rag.utils import get_rag_context, rag_template
from open_webui.apps.socket.main import app as socket_app
from open_webui.apps.socket.main import get_event_call, get_event_emitter
from open_webui.apps.webui.internal.db import Session
from open_webui.apps.webui.main import app as webui_app
from open_webui.apps.webui.main import (
    generate_function_chat_completion,
    get_pipe_models,
)
from open_webui.apps.webui.models.auths import Auths
from open_webui.apps.webui.models.functions import Functions
from open_webui.apps.webui.models.models import Models
from open_webui.apps.webui.models.users import UserModel, Users
from open_webui.apps.webui.utils import load_function_module_by_id


from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo


from open_webui.config import (
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    DEFAULT_LOCALE,
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
    ENABLE_MODEL_FILTER,
    ENABLE_OAUTH_SIGNUP,
    ENABLE_OLLAMA_API,
    ENABLE_OPENAI_API,
    ENV,
    FRONTEND_BUILD_DIR,
    MODEL_FILTER_LIST,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    OAUTH_PROVIDERS,
    ENABLE_SEARCH_QUERY,
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
    STATIC_DIR,
    TASK_MODEL,
    TASK_MODEL_EXTERNAL,
    TITLE_GENERATION_PROMPT_TEMPLATE,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    WEBHOOK_URL,
    WEBUI_AUTH,
    WEBUI_NAME,
    AppConfig,
    run_migrations,
)
from open_webui.constants import ERROR_MESSAGES, TASKS, WEBHOOK_MESSAGES
from open_webui.env import (
    CHANGELOG,
    GLOBAL_LOG_LEVEL,
    SAFE_MODE,
    SRC_LOG_LEVELS,
    VERSION,
    WEBUI_BUILD_HASH,
    WEBUI_SECRET_KEY,
    WEBUI_SESSION_COOKIE_SAME_SITE,
    WEBUI_SESSION_COOKIE_SECURE,
    WEBUI_URL,
)
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response, StreamingResponse


from open_webui.utils.misc import (
    add_or_update_system_message,
    get_last_user_message,
    parse_duration,
    prepend_to_first_user_message_content,
)
from open_webui.utils.task import (
    moa_response_generation_template,
    search_query_generation_template,
    title_generation_template,
    tools_function_calling_generation_template,
)
from open_webui.utils.tools import get_tools
from open_webui.utils.utils import (
    create_token,
    decode_token,
    get_admin_user,
    get_current_user,
    get_http_authorization_cred,
    get_password_hash,
    get_verified_user,
)
from open_webui.utils.webhook import post_webhook

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
app.state.config.ENABLE_SEARCH_QUERY = ENABLE_SEARCH_QUERY
app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
)

app.state.MODELS = {}


##################################
#
# ChatCompletion Middleware
#
##################################


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
            # TODO: Fix FunctionModel
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


async def chat_completion_filter_functions_handler(body, model, extra_params):
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
            params = {"body": body} | {
                k: v
                for k, v in {
                    **extra_params,
                    "__model__": model,
                    "__id__": filter_id,
                }.items()
                if k in sig.parameters
            }

            if "__user__" in params and hasattr(function_module, "UserValves"):
                try:
                    params["__user__"]["valves"] = function_module.UserValves(
                        **Functions.get_user_valves_by_id_and_user_id(
                            filter_id, params["__user__"]["id"]
                        )
                    )
                except Exception as e:
                    print(e)

            if inspect.iscoroutinefunction(inlet):
                body = await inlet(**params)
            else:
                body = inlet(**params)

        except Exception as e:
            print(f"Error: {e}")
            raise e

    if skip_files and "files" in body.get("metadata", {}):
        del body["metadata"]["files"]

    return body, {}


def get_tools_function_calling_payload(messages, task_model_id, content):
    user_message = get_last_user_message(messages)
    history = "\n".join(
        f"{message['role'].upper()}: \"\"\"{message['content']}\"\"\""
        for message in messages[::-1][:4]
    )

    prompt = f"History:\n{history}\nQuery: {user_message}"

    return {
        "model": task_model_id,
        "messages": [
            {"role": "system", "content": content},
            {"role": "user", "content": f"Query: {prompt}"},
        ],
        "stream": False,
        "metadata": {"task": str(TASKS.FUNCTION_CALLING)},
    }


async def get_content_from_response(response) -> Optional[str]:
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
    return content


async def chat_completion_tools_handler(
    body: dict, user: UserModel, extra_params: dict
) -> tuple[dict, dict]:
    # If tool_ids field is present, call the functions
    metadata = body.get("metadata", {})

    tool_ids = metadata.get("tool_ids", None)
    log.debug(f"{tool_ids=}")
    if not tool_ids:
        return body, {}

    skip_files = False
    contexts = []
    citations = []

    task_model_id = get_task_model_id(body["model"])
    tools = get_tools(
        webui_app,
        tool_ids,
        user,
        {
            **extra_params,
            "__model__": app.state.MODELS[task_model_id],
            "__messages__": body["messages"],
            "__files__": metadata.get("files", []),
        },
    )
    log.info(f"{tools=}")

    specs = [tool["spec"] for tool in tools.values()]
    tools_specs = json.dumps(specs)

    if app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE != "":
        template = app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    else:
        template = """Available Tools: {{TOOLS}}\nReturn an empty string if no tools match the query. If a function tool matches, construct and return a JSON object in the format {\"name\": \"functionName\", \"parameters\": {\"requiredFunctionParamKey\": \"requiredFunctionParamValue\"}} using the appropriate tool and its parameters. Only return the object and limit the response to the JSON object without additional text."""

    tools_function_calling_prompt = tools_function_calling_generation_template(
        template, tools_specs
    )
    log.info(f"{tools_function_calling_prompt=}")
    payload = get_tools_function_calling_payload(
        body["messages"], task_model_id, tools_function_calling_prompt
    )

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        raise e

    try:
        response = await generate_chat_completions(form_data=payload, user=user)
        log.debug(f"{response=}")
        content = await get_content_from_response(response)
        log.debug(f"{content=}")

        if not content:
            return body, {}

        result = json.loads(content)

        tool_function_name = result.get("name", None)
        if tool_function_name not in tools:
            return body, {}

        tool_function_params = result.get("parameters", {})

        try:
            tool_output = await tools[tool_function_name]["callable"](
                **tool_function_params
            )
        except Exception as e:
            tool_output = str(e)

        if tools[tool_function_name]["citation"]:
            citations.append(
                {
                    "source": {
                        "name": f"TOOL:{tools[tool_function_name]['toolkit_id']}/{tool_function_name}"
                    },
                    "document": [tool_output],
                    "metadata": [{"source": tool_function_name}],
                }
            )
        if tools[tool_function_name]["file_handler"]:
            skip_files = True

        if isinstance(tool_output, str):
            contexts.append(tool_output)

    except Exception as e:
        log.exception(f"Error: {e}")
        content = None

    log.debug(f"tool_contexts: {contexts}")

    if skip_files and "files" in body.get("metadata", {}):
        del body["metadata"]["files"]

    return body, {"contexts": contexts, "citations": citations}


async def chat_completion_files_handler(body) -> tuple[dict, dict[str, list]]:
    contexts = []
    citations = []

    if files := body.get("metadata", {}).get("files", None):
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

    return body, {"contexts": contexts, "citations": citations}


def is_chat_completion_request(request):
    return request.method == "POST" and any(
        endpoint in request.url.path
        for endpoint in ["/ollama/api/chat", "/chat/completions"]
    )


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


class ChatCompletionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not is_chat_completion_request(request):
            return await call_next(request)
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
            "tool_ids": body.get("tool_ids", None),
            "files": body.get("files", None),
        }
        body["metadata"] = metadata

        extra_params = {
            "__event_emitter__": get_event_emitter(metadata),
            "__event_call__": get_event_call(metadata),
            "__user__": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
        }

        # Initialize data_items to store additional data to be sent to the client
        # Initalize contexts and citation
        data_items = []
        contexts = []
        citations = []

        try:
            body, flags = await chat_completion_filter_functions_handler(
                body, model, extra_params
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

        metadata = {
            **metadata,
            "tool_ids": body.pop("tool_ids", None),
            "files": body.pop("files", None),
        }
        body["metadata"] = metadata

        try:
            body, flags = await chat_completion_tools_handler(body, user, extra_params)
            contexts.extend(flags.get("contexts", []))
            citations.extend(flags.get("citations", []))
        except Exception as e:
            log.exception(e)

        try:
            body, flags = await chat_completion_files_handler(body)
            contexts.extend(flags.get("contexts", []))
            citations.extend(flags.get("citations", []))
        except Exception as e:
            log.exception(e)

        # If context is not empty, insert it into the messages
        if len(contexts) > 0:
            context_string = "/n".join(contexts).strip()
            prompt = get_last_user_message(body["messages"])
            if prompt is None:
                raise Exception("No user message found")
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

        modified_body_bytes = json.dumps(body).encode("utf-8")
        # Replace the request body with the modified one
        request._body = modified_body_bytes
        # Set custom header to ensure content-length matches new body length
        request.headers.__dict__["_list"] = [
            (b"content-length", str(len(modified_body_bytes)).encode("utf-8")),
            *[(k, v) for k, v in request.headers.raw if k.lower() != b"content-length"],
        ]

        response = await call_next(request)
        if not isinstance(response, StreamingResponse):
            return response

        content_type = response.headers["Content-Type"]
        is_openai = "text/event-stream" in content_type
        is_ollama = "application/x-ndjson" in content_type
        if not is_openai and not is_ollama:
            return response

        def wrap_item(item):
            return f"data: {item}\n\n" if is_openai else f"{item}\n"

        async def stream_wrapper(original_generator, data_items):
            for item in data_items:
                yield wrap_item(json.dumps(item))

            async for data in original_generator:
                yield data

        return StreamingResponse(
            stream_wrapper(response.body_iterator, data_items),
            headers=dict(response.headers),
        )

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}


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

            if key == "":
                continue

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
        if not is_chat_completion_request(request):
            return await call_next(request)

        log.debug(f"request.url.path: {request.url.path}")

        # Read the original request body
        body = await request.body()
        # Decode body to string
        body_str = body.decode("utf-8")
        # Parse string to JSON
        data = json.loads(body_str) if body_str else {}

        user = get_current_user(
            request,
            get_http_authorization_cred(request.headers["Authorization"]),
        )

        try:
            data = filter_pipeline(data, user)
        except Exception as e:
            if len(e.args) > 1:
                return JSONResponse(
                    status_code=e.args[0],
                    content={"detail": e.args[1]},
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": str(e)},
                )

        modified_body_bytes = json.dumps(data).encode("utf-8")
        # Replace the request body with the modified one
        request._body = modified_body_bytes
        # Set custom header to ensure content-length matches new body length
        request.headers.__dict__["_list"] = [
            (b"content-length", str(len(modified_body_bytes)).encode("utf-8")),
            *[(k, v) for k, v in request.headers.raw if k.lower() != b"content-length"],
        ]

        response = await call_next(request)
        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}


app.add_middleware(PipelineMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
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
        if custom_model.base_model_id is None:
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
            if action is None:
                raise Exception(f"Action not found: {action_id}")

            if action_id in webui_app.state.FUNCTIONS:
                function_module = webui_app.state.FUNCTIONS[action_id]
            else:
                function_module, _, _ = load_function_module_by_id(action_id)
                webui_app.state.FUNCTIONS[action_id] = function_module

            __webui__ = False
            if hasattr(function_module, "__webui__"):
                __webui__ = function_module.__webui__

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
                            **({"__webui__": __webui__} if __webui__ else {}),
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
                        **({"__webui__": __webui__} if __webui__ else {}),
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

    if app.state.config.ENABLE_MODEL_FILTER:
        if user.role == "user" and model_id not in app.state.config.MODEL_FILTER_LIST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Model not found",
            )

    model = app.state.MODELS[model_id]
    if model.get("pipe"):
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
            # TODO: Fix FunctionModel to include vavles
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
        "ENABLE_SEARCH_QUERY": app.state.config.ENABLE_SEARCH_QUERY,
        "SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE": app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


class TaskConfigForm(BaseModel):
    TASK_MODEL: Optional[str]
    TASK_MODEL_EXTERNAL: Optional[str]
    TITLE_GENERATION_PROMPT_TEMPLATE: str
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_SEARCH_QUERY: bool
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
    app.state.config.ENABLE_SEARCH_QUERY = form_data.ENABLE_SEARCH_QUERY
    app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
        form_data.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    )

    return {
        "TASK_MODEL": app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": app.state.config.TASK_MODEL_EXTERNAL,
        "TITLE_GENERATION_PROMPT_TEMPLATE": app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE": app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_SEARCH_QUERY": app.state.config.ENABLE_SEARCH_QUERY,
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

    if app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE != "":
        template = app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE
    else:
        template = """Create a concise, 3-5 word title with an emoji as a title for the prompt in the given language. Suitable Emojis for the summary can be used to enhance understanding but avoid quotation marks or special formatting. RESPOND ONLY WITH THE TITLE TEXT.

Examples of titles:
📉 Stock Market Trends
🍪 Perfect Chocolate Chip Recipe
Evolution of Music Streaming
Remote Work Productivity Tips
Artificial Intelligence in Healthcare
🎮 Video Game Development Insights

Prompt: {{prompt:middletruncate:8000}}"""

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
        "metadata": {"task": str(TASKS.TITLE_GENERATION)},
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        if len(e.args) > 1:
            return JSONResponse(
                status_code=e.args[0],
                content={"detail": e.args[1]},
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

    if "chat_id" in payload:
        del payload["chat_id"]

    return await generate_chat_completions(form_data=payload, user=user)


@app.post("/api/task/query/completions")
async def generate_search_query(form_data: dict, user=Depends(get_verified_user)):
    print("generate_search_query")
    if not app.state.config.ENABLE_SEARCH_QUERY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Search query generation is disabled",
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

    if app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE != "":
        template = app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE
    else:
        template = """Given the user's message and interaction history, decide if a web search is necessary. You must be concise and exclusively provide a search query if one is necessary. Refrain from verbose responses or any additional commentary. Prefer suggesting a search if uncertain to provide comprehensive or updated information. If a search isn't needed at all, respond with an empty string. Default to a search query when in doubt. Today's date is {{CURRENT_DATE}}.

User Message:
{{prompt:end:4000}}

Interaction History:
{{MESSAGES:END:6}}

Search Query:"""

    content = search_query_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    print("content", content)

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "max_tokens": 30,
        "metadata": {"task": str(TASKS.QUERY_GENERATION)},
    }

    print(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        if len(e.args) > 1:
            return JSONResponse(
                status_code=e.args[0],
                content={"detail": e.args[1]},
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
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
        "metadata": {"task": str(TASKS.EMOJI_GENERATION)},
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        if len(e.args) > 1:
            return JSONResponse(
                status_code=e.args[0],
                content={"detail": e.args[1]},
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

    if "chat_id" in payload:
        del payload["chat_id"]

    return await generate_chat_completions(form_data=payload, user=user)


@app.post("/api/task/moa/completions")
async def generate_moa_response(form_data: dict, user=Depends(get_verified_user)):
    print("generate_moa_response")

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

    template = """You have been provided with a set of responses from various models to the latest user query: "{{prompt}}"

Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models: {{responses}}"""

    content = moa_response_generation_template(
        template,
        form_data["prompt"],
        form_data["responses"],
    )

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": form_data.get("stream", False),
        "chat_id": form_data.get("chat_id", None),
        "metadata": {"task": str(TASKS.MOA_RESPONSE_GENERATION)},
    }

    log.debug(payload)

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        if len(e.args) > 1:
            return JSONResponse(
                status_code=e.args[0],
                content={"detail": e.args[1]},
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

    if "chat_id" in payload:
        del payload["chat_id"]

    return await generate_chat_completions(form_data=payload, user=user)


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
        if response is not None and "pipelines" in response
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
    if not (file.filename and file.filename.endswith(".py")):
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
            except Exception:
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
            except Exception:
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
            except Exception:
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
            except Exception:
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
            except Exception:
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
            except Exception:
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
            except Exception:
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
async def get_app_config(request: Request):
    user = None
    if "token" in request.cookies:
        token = request.cookies.get("token")
        data = decode_token(token)
        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

    return {
        "status": True,
        "name": WEBUI_NAME,
        "version": VERSION,
        "default_locale": str(DEFAULT_LOCALE),
        "oauth": {
            "providers": {
                name: config.get("name", name)
                for name, config in OAUTH_PROVIDERS.items()
            }
        },
        "features": {
            "auth": WEBUI_AUTH,
            "auth_trusted_header": bool(webui_app.state.AUTH_TRUSTED_EMAIL_HEADER),
            "enable_signup": webui_app.state.config.ENABLE_SIGNUP,
            "enable_login_form": webui_app.state.config.ENABLE_LOGIN_FORM,
            **(
                {
                    "enable_web_search": rag_app.state.config.ENABLE_RAG_WEB_SEARCH,
                    "enable_image_generation": images_app.state.config.ENABLED,
                    "enable_community_sharing": webui_app.state.config.ENABLE_COMMUNITY_SHARING,
                    "enable_message_rating": webui_app.state.config.ENABLE_MESSAGE_RATING,
                    "enable_admin_export": ENABLE_ADMIN_EXPORT,
                    "enable_admin_chat_access": ENABLE_ADMIN_CHAT_ACCESS,
                }
                if user is not None
                else {}
            ),
        },
        **(
            {
                "default_models": webui_app.state.config.DEFAULT_MODELS,
                "default_prompt_suggestions": webui_app.state.config.DEFAULT_PROMPT_SUGGESTIONS,
                "audio": {
                    "tts": {
                        "engine": audio_app.state.config.TTS_ENGINE,
                        "voice": audio_app.state.config.TTS_VOICE,
                        "split_on": audio_app.state.config.TTS_SPLIT_ON,
                    },
                    "stt": {
                        "engine": audio_app.state.config.STT_ENGINE,
                    },
                },
                "file": {
                    "max_size": rag_app.state.config.FILE_MAX_SIZE,
                    "max_count": rag_app.state.config.FILE_MAX_COUNT,
                },
                "permissions": {**webui_app.state.config.USER_PERMISSIONS},
            }
            if user is not None
            else {}
        ),
    }


@app.get("/api/config/model/filter")
async def get_model_filter_config(user=Depends(get_admin_user)):
    return {
        "enabled": app.state.config.ENABLE_MODEL_FILTER,
        "models": app.state.config.MODEL_FILTER_LIST,
    }


class ModelFilterConfigForm(BaseModel):
    enabled: bool
    models: list[str]


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
async def get_app_version():
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
    except aiohttp.ClientError:
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
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(404)
    return await client.authorize_redirect(request, redirect_uri)


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
    email_claim = webui_app.state.config.OAUTH_EMAIL_CLAIM
    email = user_data.get(email_claim, "").lower()
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
        "icons": [
            {
                "src": "/static/logo.png",
                "type": "image/png",
                "sizes": "500x500",
                "purpose": "any",
            },
            {
                "src": "/static/logo.png",
                "type": "image/png",
                "sizes": "500x500",
                "purpose": "maskable",
            },
        ],
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

import asyncio
import inspect
import json
import logging
import mimetypes
import os
import shutil
import sys
import time
import random
from contextlib import asynccontextmanager
from typing import Optional

from aiocache import cached
import aiohttp
import requests
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
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response, StreamingResponse

from open_webui.apps.audio.main import app as audio_app
from open_webui.apps.images.main import app as images_app
from open_webui.apps.ollama.main import (
    app as ollama_app,
    get_all_models as get_ollama_models,
    generate_chat_completion as generate_ollama_chat_completion,
    GenerateChatCompletionForm,
)
from open_webui.apps.openai.main import (
    app as openai_app,
    generate_chat_completion as generate_openai_chat_completion,
    get_all_models as get_openai_models,
    get_all_models_responses as get_openai_models_responses,
)
from open_webui.apps.retrieval.main import app as retrieval_app
from open_webui.apps.retrieval.utils import get_sources_from_files


from open_webui.apps.socket.main import (
    app as socket_app,
    periodic_usage_pool_cleanup,
    get_event_call,
    get_event_emitter,
)
from open_webui.apps.webui.internal.db import Session
from open_webui.apps.webui.main import (
    app as webui_app,
    generate_function_chat_completion,
    get_all_models as get_open_webui_models,
)
from open_webui.apps.webui.models.functions import Functions
from open_webui.apps.webui.models.models import Models
from open_webui.apps.webui.models.users import UserModel, Users
from open_webui.apps.webui.utils import load_function_module_by_id
from open_webui.config import (
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    DEFAULT_LOCALE,
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
    ENABLE_OLLAMA_API,
    ENABLE_OPENAI_API,
    ENABLE_TAGS_GENERATION,
    ENV,
    FRONTEND_BUILD_DIR,
    OAUTH_PROVIDERS,
    STATIC_DIR,
    TASK_MODEL,
    TASK_MODEL_EXTERNAL,
    ENABLE_SEARCH_QUERY_GENERATION,
    ENABLE_RETRIEVAL_QUERY_GENERATION,
    QUERY_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE,
    TITLE_GENERATION_PROMPT_TEMPLATE,
    TAGS_GENERATION_PROMPT_TEMPLATE,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    WEBHOOK_URL,
    WEBUI_AUTH,
    WEBUI_NAME,
    AppConfig,
    reset_config,
)
from open_webui.constants import TASKS
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
    RESET_CONFIG_ON_START,
    OFFLINE_MODE,
)
from open_webui.utils.misc import (
    add_or_update_system_message,
    get_last_user_message,
    prepend_to_first_user_message_content,
)
from open_webui.utils.oauth import oauth_manager
from open_webui.utils.payload import convert_payload_openai_to_ollama
from open_webui.utils.response import (
    convert_response_ollama_to_openai,
    convert_streaming_response_ollama_to_openai,
)
from open_webui.utils.security_headers import SecurityHeadersMiddleware
from open_webui.utils.task import (
    rag_template,
    title_generation_template,
    query_generation_template,
    tags_generation_template,
    emoji_generation_template,
    moa_response_generation_template,
    tools_function_calling_generation_template,
)
from open_webui.utils.tools import get_tools
from open_webui.utils.utils import (
    decode_token,
    get_admin_user,
    get_current_user,
    get_http_authorization_cred,
    get_verified_user,
)
from open_webui.utils.access_control import has_access

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
    if RESET_CONFIG_ON_START:
        reset_config()

    asyncio.create_task(periodic_usage_pool_cleanup())
    yield


app = FastAPI(
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.config = AppConfig()

app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.ENABLE_OLLAMA_API = ENABLE_OLLAMA_API

app.state.config.WEBHOOK_URL = WEBHOOK_URL

app.state.config.TASK_MODEL = TASK_MODEL
app.state.config.TASK_MODEL_EXTERNAL = TASK_MODEL_EXTERNAL

app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = TITLE_GENERATION_PROMPT_TEMPLATE

app.state.config.ENABLE_TAGS_GENERATION = ENABLE_TAGS_GENERATION
app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = TAGS_GENERATION_PROMPT_TEMPLATE


app.state.config.ENABLE_SEARCH_QUERY_GENERATION = ENABLE_SEARCH_QUERY_GENERATION
app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION = ENABLE_RETRIEVAL_QUERY_GENERATION
app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = QUERY_GENERATION_PROMPT_TEMPLATE

app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
)

##################################
#
# ChatCompletion Middleware
#
##################################


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


def get_task_model_id(
    default_model_id: str, task_model: str, task_model_external: str, models
) -> str:
    # Set the task model
    task_model_id = default_model_id
    # Check if the user has a custom task model and use that model
    if models[task_model_id]["owned_by"] == "ollama":
        if task_model and task_model in models:
            task_model_id = task_model
    else:
        if task_model_external and task_model_external in models:
            task_model_id = task_model_external

    return task_model_id


async def chat_completion_tools_handler(
    body: dict, user: UserModel, models, extra_params: dict
) -> tuple[dict, dict]:
    # If tool_ids field is present, call the functions
    metadata = body.get("metadata", {})

    tool_ids = metadata.get("tool_ids", None)
    log.debug(f"{tool_ids=}")
    if not tool_ids:
        return body, {}

    skip_files = False
    sources = []

    task_model_id = get_task_model_id(
        body["model"],
        app.state.config.TASK_MODEL,
        app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )
    tools = get_tools(
        webui_app,
        tool_ids,
        user,
        {
            **extra_params,
            "__model__": models[task_model_id],
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
        payload = filter_pipeline(payload, user, models)
    except Exception as e:
        raise e

    try:
        response = await generate_chat_completions(form_data=payload, user=user)
        log.debug(f"{response=}")
        content = await get_content_from_response(response)
        log.debug(f"{content=}")

        if not content:
            return body, {}

        try:
            content = content[content.find("{") : content.rfind("}") + 1]
            if not content:
                raise Exception("No JSON object found in the response")

            result = json.loads(content)

            tool_function_name = result.get("name", None)
            if tool_function_name not in tools:
                return body, {}

            tool_function_params = result.get("parameters", {})

            try:
                required_params = (
                    tools[tool_function_name]
                    .get("spec", {})
                    .get("parameters", {})
                    .get("required", [])
                )
                tool_function = tools[tool_function_name]["callable"]
                tool_function_params = {
                    k: v
                    for k, v in tool_function_params.items()
                    if k in required_params
                }
                tool_output = await tool_function(**tool_function_params)

            except Exception as e:
                tool_output = str(e)

            print(tools[tool_function_name]["citation"])

            if isinstance(tool_output, str):
                if tools[tool_function_name]["citation"]:
                    sources.append(
                        {
                            "source": {
                                "name": f"TOOL:{tools[tool_function_name]['toolkit_id']}/{tool_function_name}"
                            },
                            "document": [tool_output],
                            "metadata": [
                                {
                                    "source": f"TOOL:{tools[tool_function_name]['toolkit_id']}/{tool_function_name}"
                                }
                            ],
                        }
                    )
                else:
                    sources.append(
                        {
                            "source": {},
                            "document": [tool_output],
                            "metadata": [
                                {
                                    "source": f"TOOL:{tools[tool_function_name]['toolkit_id']}/{tool_function_name}"
                                }
                            ],
                        }
                    )

                if tools[tool_function_name]["file_handler"]:
                    skip_files = True

        except Exception as e:
            log.exception(f"Error: {e}")
            content = None
    except Exception as e:
        log.exception(f"Error: {e}")
        content = None

    log.debug(f"tool_contexts: {sources}")

    if skip_files and "files" in body.get("metadata", {}):
        del body["metadata"]["files"]

    return body, {"sources": sources}


async def chat_completion_files_handler(
    body: dict, user: UserModel
) -> tuple[dict, dict[str, list]]:
    sources = []

    if files := body.get("metadata", {}).get("files", None):
        try:
            queries_response = await generate_queries(
                {
                    "model": body["model"],
                    "messages": body["messages"],
                    "type": "retrieval",
                },
                user,
            )
            queries_response = queries_response["choices"][0]["message"]["content"]

            try:
                queries_response = json.loads(queries_response)
            except Exception as e:
                queries_response = {"queries": []}

            queries = queries_response.get("queries", [])
        except Exception as e:
            queries = []

        if len(queries) == 0:
            queries = [get_last_user_message(body["messages"])]

        sources = get_sources_from_files(
            files=files,
            queries=queries,
            embedding_function=retrieval_app.state.EMBEDDING_FUNCTION,
            k=retrieval_app.state.config.TOP_K,
            reranking_function=retrieval_app.state.sentence_transformer_rf,
            r=retrieval_app.state.config.RELEVANCE_THRESHOLD,
            hybrid_search=retrieval_app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        )

        log.debug(f"rag_contexts:sources: {sources}")
    return body, {"sources": sources}


def is_chat_completion_request(request):
    return request.method == "POST" and any(
        endpoint in request.url.path
        for endpoint in ["/ollama/api/chat", "/chat/completions"]
    )


async def get_body_and_model_and_user(request, models):
    # Read the original request body
    body = await request.body()
    body_str = body.decode("utf-8")
    body = json.loads(body_str) if body_str else {}

    model_id = body["model"]
    if model_id not in models:
        raise Exception("Model not found")
    model = models[model_id]

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

        model_list = await get_all_models()
        models = {model["id"]: model for model in model_list}

        try:
            body, model, user = await get_body_and_model_and_user(request, models)
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

        model_info = Models.get_model_by_id(model["id"])
        if user.role == "user":
            if model.get("arena"):
                if not has_access(
                    user.id,
                    type="read",
                    access_control=model.get("info", {})
                    .get("meta", {})
                    .get("access_control", {}),
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="Model not found",
                    )
            else:
                if not model_info:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": "Model not found"},
                    )
                elif not (
                    user.id == model_info.user_id
                    or has_access(
                        user.id, type="read", access_control=model_info.access_control
                    )
                ):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "User does not have access to the model"},
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
            "__metadata__": metadata,
        }

        # Initialize data_items to store additional data to be sent to the client
        # Initialize contexts and citation
        data_items = []
        sources = []

        try:
            body, flags = await chat_completion_filter_functions_handler(
                body, model, extra_params
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

        tool_ids = body.pop("tool_ids", None)
        files = body.pop("files", None)

        metadata = {
            **metadata,
            "tool_ids": tool_ids,
            "files": files,
        }
        body["metadata"] = metadata

        try:
            body, flags = await chat_completion_tools_handler(
                body, user, models, extra_params
            )
            sources.extend(flags.get("sources", []))
        except Exception as e:
            log.exception(e)

        try:
            body, flags = await chat_completion_files_handler(body, user)
            sources.extend(flags.get("sources", []))
        except Exception as e:
            log.exception(e)

        # If context is not empty, insert it into the messages
        if len(sources) > 0:
            context_string = ""
            for source_idx, source in enumerate(sources):
                source_id = source.get("source", {}).get("name", "")

                if "document" in source:
                    for doc_idx, doc_context in enumerate(source["document"]):
                        metadata = source.get("metadata")
                        doc_source_id = None

                        if metadata:
                            doc_source_id = metadata[doc_idx].get("source", source_id)

                        if source_id:
                            context_string += f"<source><source_id>{doc_source_id if doc_source_id is not None else source_id}</source_id><source_context>{doc_context}</source_context></source>\n"
                        else:
                            # If there is no source_id, then do not include the source_id tag
                            context_string += f"<source><source_context>{doc_context}</source_context></source>\n"

            context_string = context_string.strip()
            prompt = get_last_user_message(body["messages"])

            if prompt is None:
                raise Exception("No user message found")
            if (
                retrieval_app.state.config.RELEVANCE_THRESHOLD == 0
                and context_string.strip() == ""
            ):
                log.debug(
                    f"With a 0 relevancy threshold for RAG, the context cannot be empty"
                )

            # Workaround for Ollama 2.0+ system prompt issue
            # TODO: replace with add_or_update_system_message
            if model["owned_by"] == "ollama":
                body["messages"] = prepend_to_first_user_message_content(
                    rag_template(
                        retrieval_app.state.config.RAG_TEMPLATE, context_string, prompt
                    ),
                    body["messages"],
                )
            else:
                body["messages"] = add_or_update_system_message(
                    rag_template(
                        retrieval_app.state.config.RAG_TEMPLATE, context_string, prompt
                    ),
                    body["messages"],
                )

        # If there are citations, add them to the data_items
        sources = [
            source for source in sources if source.get("source", {}).get("name", "")
        ]
        if len(sources) > 0:
            data_items.append({"sources": sources})

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


def get_sorted_filters(model_id, models):
    filters = [
        model
        for model in models.values()
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


def filter_pipeline(payload, user, models):
    user = {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    model_id = payload["model"]

    sorted_filters = get_sorted_filters(model_id, models)
    model = models[model_id]

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

        try:
            user = get_current_user(
                request,
                get_http_authorization_cred(request.headers["Authorization"]),
            )
        except KeyError as e:
            if len(e.args) > 1:
                return JSONResponse(
                    status_code=e.args[0],
                    content={"detail": e.args[1]},
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Not authenticated"},
                )
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )

        model_list = await get_all_models()
        models = {model["id"]: model for model in model_list}

        try:
            data = filter_pipeline(data, user, models)
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


from urllib.parse import urlencode, parse_qs, urlparse


class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request is a GET request
        if request.method == "GET":
            path = request.url.path
            query_params = dict(parse_qs(urlparse(str(request.url)).query))

            # Check for the specific watch path and the presence of 'v' parameter
            if path.endswith("/watch") and "v" in query_params:
                video_id = query_params["v"][0]  # Extract the first 'v' parameter
                encoded_video_id = urlencode({"youtube": video_id})
                redirect_url = f"/?{encoded_video_id}"
                return RedirectResponse(url=redirect_url)

        # Proceed with the normal flow of other requests
        response = await call_next(request)
        return response


# Add the middleware to the app
app.add_middleware(RedirectMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def commit_session_after_request(request: Request, call_next):
    response = await call_next(request)
    # log.debug("Commit session after request")
    Session.commit()
    return response


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    request.state.enable_api_key = webui_app.state.config.ENABLE_API_KEY
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def update_embedding_function(request: Request, call_next):
    response = await call_next(request)
    if "/embedding/update" in request.url.path:
        webui_app.state.EMBEDDING_FUNCTION = retrieval_app.state.EMBEDDING_FUNCTION
    return response


@app.middleware("http")
async def inspect_websocket(request: Request, call_next):
    if (
        "/ws/socket.io" in request.url.path
        and request.query_params.get("transport") == "websocket"
    ):
        upgrade = (request.headers.get("Upgrade") or "").lower()
        connection = (request.headers.get("Connection") or "").lower().split(",")
        # Check that there's the correct headers for an upgrade, else reject the connection
        # This is to work around this upstream issue: https://github.com/miguelgrinberg/python-engineio/issues/367
        if upgrade != "websocket" or "upgrade" not in connection:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid WebSocket upgrade request"},
            )
    return await call_next(request)


app.mount("/ws", socket_app)
app.mount("/ollama", ollama_app)
app.mount("/openai", openai_app)

app.mount("/images/api/v1", images_app)
app.mount("/audio/api/v1", audio_app)
app.mount("/retrieval/api/v1", retrieval_app)

app.mount("/api/v1", webui_app)

webui_app.state.EMBEDDING_FUNCTION = retrieval_app.state.EMBEDDING_FUNCTION


async def get_all_base_models():
    open_webui_models = []
    openai_models = []
    ollama_models = []

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

    open_webui_models = await get_open_webui_models()

    models = open_webui_models + openai_models + ollama_models
    return models


@cached(ttl=3)
async def get_all_models():
    models = await get_all_base_models()

    # If there are no models, return an empty list
    if len([model for model in models if not model.get("arena", False)]) == 0:
        return []

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
                    if custom_model.is_active:
                        model["name"] = custom_model.name
                        model["info"] = custom_model.model_dump()

                        action_ids = []
                        if "info" in model and "meta" in model["info"]:
                            action_ids.extend(
                                model["info"]["meta"].get("actionIds", [])
                            )

                        model["action_ids"] = action_ids
                    else:
                        models.remove(model)

        elif custom_model.is_active and (
            custom_model.id not in [model["id"] for model in models]
        ):
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
                    break

            if custom_model.meta:
                meta = custom_model.meta.model_dump()
                if "actionIds" in meta:
                    action_ids.extend(meta["actionIds"])

            models.append(
                {
                    "id": f"{custom_model.id}",
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

    # Process action_ids to get the actions
    def get_action_items_from_module(function, module):
        actions = []
        if hasattr(module, "actions"):
            actions = module.actions
            return [
                {
                    "id": f"{function.id}.{action['id']}",
                    "name": action.get("name", f"{function.name} ({action['id']})"),
                    "description": function.meta.description,
                    "icon_url": action.get(
                        "icon_url", function.meta.manifest.get("icon_url", None)
                    ),
                }
                for action in actions
            ]
        else:
            return [
                {
                    "id": function.id,
                    "name": function.name,
                    "description": function.meta.description,
                    "icon_url": function.meta.manifest.get("icon_url", None),
                }
            ]

    def get_function_module_by_id(function_id):
        if function_id in webui_app.state.FUNCTIONS:
            function_module = webui_app.state.FUNCTIONS[function_id]
        else:
            function_module, _, _ = load_function_module_by_id(function_id)
            webui_app.state.FUNCTIONS[function_id] = function_module

    for model in models:
        action_ids = [
            action_id
            for action_id in list(set(model.pop("action_ids", []) + global_action_ids))
            if action_id in enabled_action_ids
        ]

        model["actions"] = []
        for action_id in action_ids:
            action_function = Functions.get_function_by_id(action_id)
            if action_function is None:
                raise Exception(f"Action not found: {action_id}")

            function_module = get_function_module_by_id(action_id)
            model["actions"].extend(
                get_action_items_from_module(action_function, function_module)
            )
    log.debug(f"get_all_models() returned {len(models)} models")

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

    model_order_list = webui_app.state.config.MODEL_ORDER_LIST
    if model_order_list:
        model_order_dict = {model_id: i for i, model_id in enumerate(model_order_list)}
        # Sort models by order list priority, with fallback for those not in the list
        models.sort(
            key=lambda x: (model_order_dict.get(x["id"], float("inf")), x["name"])
        )

    # Filter out models that the user does not have access to
    if user.role == "user":
        filtered_models = []
        for model in models:
            if model.get("arena"):
                if has_access(
                    user.id,
                    type="read",
                    access_control=model.get("info", {})
                    .get("meta", {})
                    .get("access_control", {}),
                ):
                    filtered_models.append(model)
                continue

            model_info = Models.get_model_by_id(model["id"])
            if model_info:
                if user.id == model_info.user_id or has_access(
                    user.id, type="read", access_control=model_info.access_control
                ):
                    filtered_models.append(model)
        models = filtered_models

    log.debug(
        f"/api/models returned filtered models accessible to the user: {json.dumps([model['id'] for model in models])}"
    )

    return {"data": models}


@app.get("/api/models/base")
async def get_base_models(user=Depends(get_admin_user)):
    models = await get_all_base_models()

    # Filter out arena models
    models = [model for model in models if not model.get("arena", False)]
    return {"data": models}


@app.post("/api/chat/completions")
async def generate_chat_completions(
    form_data: dict, user=Depends(get_verified_user), bypass_filter: bool = False
):
    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    model = models[model_id]

    # Check if user has access to the model
    if not bypass_filter and user.role == "user":
        if model.get("arena"):
            if not has_access(
                user.id,
                type="read",
                access_control=model.get("info", {})
                .get("meta", {})
                .get("access_control", {}),
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
        else:
            model_info = Models.get_model_by_id(model_id)
            if not model_info:
                raise HTTPException(
                    status_code=404,
                    detail="Model not found",
                )
            elif not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )

    if model["owned_by"] == "arena":
        model_ids = model.get("info", {}).get("meta", {}).get("model_ids")
        filter_mode = model.get("info", {}).get("meta", {}).get("filter_mode")
        if model_ids and filter_mode == "exclude":
            model_ids = [
                model["id"]
                for model in await get_all_models()
                if model.get("owned_by") != "arena" and model["id"] not in model_ids
            ]

        selected_model_id = None
        if isinstance(model_ids, list) and model_ids:
            selected_model_id = random.choice(model_ids)
        else:
            model_ids = [
                model["id"]
                for model in await get_all_models()
                if model.get("owned_by") != "arena"
            ]
            selected_model_id = random.choice(model_ids)

        form_data["model"] = selected_model_id

        if form_data.get("stream") == True:

            async def stream_wrapper(stream):
                yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
                async for chunk in stream:
                    yield chunk

            response = await generate_chat_completions(
                form_data, user, bypass_filter=True
            )
            return StreamingResponse(
                stream_wrapper(response.body_iterator), media_type="text/event-stream"
            )
        else:
            return {
                **(
                    await generate_chat_completions(form_data, user, bypass_filter=True)
                ),
                "selected_model_id": selected_model_id,
            }

    if model.get("pipe"):
        # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
        return await generate_function_chat_completion(
            form_data, user=user, models=models
        )
    if model["owned_by"] == "ollama":
        # Using /ollama/api/chat endpoint
        form_data = convert_payload_openai_to_ollama(form_data)
        form_data = GenerateChatCompletionForm(**form_data)
        response = await generate_ollama_chat_completion(
            form_data=form_data, user=user, bypass_filter=bypass_filter
        )
        if form_data.stream:
            response.headers["content-type"] = "text/event-stream"
            return StreamingResponse(
                convert_streaming_response_ollama_to_openai(response),
                headers=dict(response.headers),
            )
        else:
            return convert_response_ollama_to_openai(response)
    else:
        return await generate_openai_chat_completion(
            form_data, user=user, bypass_filter=bypass_filter
        )


@app.post("/api/chat/completed")
async def chat_completed(form_data: dict, user=Depends(get_verified_user)):
    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    data = form_data
    model_id = data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    model = models[model_id]
    sorted_filters = get_sorted_filters(model_id, models)
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

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    data = form_data
    model_id = data["model"]

    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    model = models[model_id]

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
        "TAGS_GENERATION_PROMPT_TEMPLATE": app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_TAGS_GENERATION": app.state.config.ENABLE_TAGS_GENERATION,
        "ENABLE_SEARCH_QUERY_GENERATION": app.state.config.ENABLE_SEARCH_QUERY_GENERATION,
        "ENABLE_RETRIEVAL_QUERY_GENERATION": app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION,
        "QUERY_GENERATION_PROMPT_TEMPLATE": app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


class TaskConfigForm(BaseModel):
    TASK_MODEL: Optional[str]
    TASK_MODEL_EXTERNAL: Optional[str]
    TITLE_GENERATION_PROMPT_TEMPLATE: str
    TAGS_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_TAGS_GENERATION: bool
    ENABLE_SEARCH_QUERY_GENERATION: bool
    ENABLE_RETRIEVAL_QUERY_GENERATION: bool
    QUERY_GENERATION_PROMPT_TEMPLATE: str
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: str


@app.post("/api/task/config/update")
async def update_task_config(form_data: TaskConfigForm, user=Depends(get_admin_user)):
    app.state.config.TASK_MODEL = form_data.TASK_MODEL
    app.state.config.TASK_MODEL_EXTERNAL = form_data.TASK_MODEL_EXTERNAL
    app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = (
        form_data.TITLE_GENERATION_PROMPT_TEMPLATE
    )
    app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = (
        form_data.TAGS_GENERATION_PROMPT_TEMPLATE
    )
    app.state.config.ENABLE_TAGS_GENERATION = form_data.ENABLE_TAGS_GENERATION
    app.state.config.ENABLE_SEARCH_QUERY_GENERATION = (
        form_data.ENABLE_SEARCH_QUERY_GENERATION
    )
    app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION = (
        form_data.ENABLE_RETRIEVAL_QUERY_GENERATION
    )

    app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = (
        form_data.QUERY_GENERATION_PROMPT_TEMPLATE
    )
    app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
        form_data.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    )

    return {
        "TASK_MODEL": app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": app.state.config.TASK_MODEL_EXTERNAL,
        "TITLE_GENERATION_PROMPT_TEMPLATE": app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "TAGS_GENERATION_PROMPT_TEMPLATE": app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_TAGS_GENERATION": app.state.config.ENABLE_TAGS_GENERATION,
        "ENABLE_SEARCH_QUERY_GENERATION": app.state.config.ENABLE_SEARCH_QUERY_GENERATION,
        "ENABLE_RETRIEVAL_QUERY_GENERATION": app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION,
        "QUERY_GENERATION_PROMPT_TEMPLATE": app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


@app.post("/api/task/title/completions")
async def generate_title(form_data: dict, user=Depends(get_verified_user)):

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        app.state.config.TASK_MODEL,
        app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(
        f"generating chat title using model {task_model_id} for user {user.email} "
    )

    if app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE != "":
        template = app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE
    else:
        template = """Create a concise, 3-5 word title with an emoji as a title for the chat history, in the given language. Suitable Emojis for the summary can be used to enhance understanding but avoid quotation marks or special formatting. RESPOND ONLY WITH THE TITLE TEXT.

Examples of titles:
📉 Stock Market Trends
🍪 Perfect Chocolate Chip Recipe
Evolution of Music Streaming
Remote Work Productivity Tips
Artificial Intelligence in Healthcare
🎮 Video Game Development Insights

<chat_history>
{{MESSAGES:END:2}}
</chat_history>"""

    content = title_generation_template(
        template,
        form_data["messages"],
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        **(
            {"max_tokens": 50}
            if models[task_model_id]["owned_by"] == "ollama"
            else {
                "max_completion_tokens": 50,
            }
        ),
        "metadata": {
            "task": str(TASKS.TITLE_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Handle pipeline filters
    try:
        payload = filter_pipeline(payload, user, models)
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


@app.post("/api/task/tags/completions")
async def generate_chat_tags(form_data: dict, user=Depends(get_verified_user)):

    if not app.state.config.ENABLE_TAGS_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Tags generation is disabled"},
        )

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        app.state.config.TASK_MODEL,
        app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(
        f"generating chat tags using model {task_model_id} for user {user.email} "
    )

    if app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE != "":
        template = app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE
    else:
        template = """### Task:
Generate 1-3 broad tags categorizing the main themes of the chat history, along with 1-3 more specific subtopic tags.

### Guidelines:
- Start with high-level domains (e.g. Science, Technology, Philosophy, Arts, Politics, Business, Health, Sports, Entertainment, Education)
- Consider including relevant subfields/subdomains if they are strongly represented throughout the conversation
- If content is too short (less than 3 messages) or too diverse, use only ["General"]
- Use the chat's primary language; default to English if multilingual
- Prioritize accuracy over specificity

### Output:
JSON format: { "tags": ["tag1", "tag2", "tag3"] }

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""

    content = tags_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": {
            "task": str(TASKS.TAGS_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Handle pipeline filters
    try:
        payload = filter_pipeline(payload, user, models)
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


@app.post("/api/task/queries/completions")
async def generate_queries(form_data: dict, user=Depends(get_verified_user)):

    type = form_data.get("type")
    if type == "web_search":
        if not app.state.config.ENABLE_SEARCH_QUERY_GENERATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Search query generation is disabled",
            )
    elif type == "retrieval":
        if not app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query generation is disabled",
            )

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        app.state.config.TASK_MODEL,
        app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(
        f"generating {type} queries using model {task_model_id} for user {user.email}"
    )

    if app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE != "":
        template = app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE

    content = query_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": {
            "task": str(TASKS.QUERY_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Handle pipeline filters
    try:
        payload = filter_pipeline(payload, user, models)
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

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        app.state.config.TASK_MODEL,
        app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(f"generating emoji using model {task_model_id} for user {user.email} ")

    template = '''
Your task is to reflect the speaker's likely facial expression through a fitting emoji. Interpret emotions from the message and reflect their facial expression using fitting, diverse emojis (e.g., 😊, 😢, 😡, 😱).

Message: """{{prompt}}"""
'''
    content = emoji_generation_template(
        template,
        form_data["prompt"],
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        **(
            {"max_tokens": 4}
            if models[task_model_id]["owned_by"] == "ollama"
            else {
                "max_completion_tokens": 4,
            }
        ),
        "chat_id": form_data.get("chat_id", None),
        "metadata": {"task": str(TASKS.EMOJI_GENERATION), "task_body": form_data},
    }

    # Handle pipeline filters
    try:
        payload = filter_pipeline(payload, user, models)
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

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        app.state.config.TASK_MODEL,
        app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(f"generating MOA model {task_model_id} for user {user.email} ")

    template = """You have been provided with a set of responses from various models to the latest user query: "{{prompt}}"

Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models: {{responses}}"""

    content = moa_response_generation_template(
        template,
        form_data["prompt"],
        form_data["responses"],
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": form_data.get("stream", False),
        "chat_id": form_data.get("chat_id", None),
        "metadata": {
            "task": str(TASKS.MOA_RESPONSE_GENERATION),
            "task_body": form_data,
        },
    }

    try:
        payload = filter_pipeline(payload, user, models)
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
    responses = await get_openai_models_responses()

    log.debug(f"get_pipelines_list: get_openai_models_responses returned {responses}")
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
        try:
            data = decode_token(token)
        except Exception as e:
            log.debug(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

    onboarding = False
    if user is None:
        user_count = Users.get_num_users()
        onboarding = user_count == 0

    return {
        **({"onboarding": True} if onboarding else {}),
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
            "enable_ldap": webui_app.state.config.ENABLE_LDAP,
            "enable_api_key": webui_app.state.config.ENABLE_API_KEY,
            "enable_signup": webui_app.state.config.ENABLE_SIGNUP,
            "enable_login_form": webui_app.state.config.ENABLE_LOGIN_FORM,
            **(
                {
                    "enable_web_search": retrieval_app.state.config.ENABLE_RAG_WEB_SEARCH,
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
                    "max_size": retrieval_app.state.config.FILE_MAX_SIZE,
                    "max_count": retrieval_app.state.config.FILE_MAX_COUNT,
                },
                "permissions": {**webui_app.state.config.USER_PERMISSIONS},
            }
            if user is not None
            else {}
        ),
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
    if OFFLINE_MODE:
        log.debug(
            f"Offline mode is enabled, returning current version as latest version"
        )
        return {"current": VERSION, "latest": VERSION}
    try:
        timeout = aiohttp.ClientTimeout(total=1)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                "https://api.github.com/repos/open-webui/open-webui/releases/latest"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["tag_name"]

                return {"current": VERSION, "latest": latest_version[1:]}
    except Exception as e:
        log.debug(e)
        return {"current": VERSION, "latest": VERSION}


############################
# OAuth Login & Callback
############################

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
    return await oauth_manager.handle_login(provider, request)


# OAuth login logic is as follows:
# 1. Attempt to find a user with matching subject ID, tied to the provider
# 2. If OAUTH_MERGE_ACCOUNTS_BY_EMAIL is true, find a user with the email address provided via OAuth
#    - This is considered insecure in general, as OAuth providers do not always verify email addresses
# 3. If there is no user, and ENABLE_OAUTH_SIGNUP is true, create a user
#    - Email addresses are considered unique, so we fail registration if the email address is already taken
@app.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, response: Response):
    return await oauth_manager.handle_callback(provider, request, response)


@app.get("/manifest.json")
async def get_manifest_json():
    return {
        "name": WEBUI_NAME,
        "short_name": WEBUI_NAME,
        "description": "Open WebUI is an open, extensible, user-friendly interface for AI that adapts to your workflow.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#343541",
        "orientation": "natural",
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

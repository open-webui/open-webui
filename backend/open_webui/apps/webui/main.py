import inspect
import json
import logging
from typing import AsyncGenerator, Generator, Iterator

from open_webui.apps.socket.main import get_event_call, get_event_emitter
from open_webui.apps.webui.models.functions import Functions
from open_webui.apps.webui.models.models import Models
from open_webui.apps.webui.routers import (
    auths,
    chats,
    configs,
    files,
    functions,
    memories,
    models,
    knowledge,
    prompts,
    tools,
    users,
    utils,
)
from open_webui.apps.webui.utils import load_function_module_by_id
from open_webui.config import (
    ADMIN_EMAIL,
    CORS_ALLOW_ORIGIN,
    DEFAULT_MODELS,
    DEFAULT_PROMPT_SUGGESTIONS,
    DEFAULT_USER_ROLE,
    ENABLE_COMMUNITY_SHARING,
    ENABLE_LOGIN_FORM,
    ENABLE_MESSAGE_RATING,
    ENABLE_SIGNUP,
    JWT_EXPIRES_IN,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    SHOW_ADMIN_DETAILS,
    USER_PERMISSIONS,
    WEBHOOK_URL,
    WEBUI_AUTH,
    WEBUI_BANNERS,
    AppConfig,
)
from open_webui.env import (
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)


from open_webui.utils.tools import get_tools

app = FastAPI()

log = logging.getLogger(__name__)

app.state.config = AppConfig()

app.state.config.ENABLE_SIGNUP = ENABLE_SIGNUP
app.state.config.ENABLE_LOGIN_FORM = ENABLE_LOGIN_FORM
app.state.config.JWT_EXPIRES_IN = JWT_EXPIRES_IN
app.state.AUTH_TRUSTED_EMAIL_HEADER = WEBUI_AUTH_TRUSTED_EMAIL_HEADER
app.state.AUTH_TRUSTED_NAME_HEADER = WEBUI_AUTH_TRUSTED_NAME_HEADER


app.state.config.SHOW_ADMIN_DETAILS = SHOW_ADMIN_DETAILS
app.state.config.ADMIN_EMAIL = ADMIN_EMAIL


app.state.config.DEFAULT_MODELS = DEFAULT_MODELS
app.state.config.DEFAULT_PROMPT_SUGGESTIONS = DEFAULT_PROMPT_SUGGESTIONS
app.state.config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
app.state.config.USER_PERMISSIONS = USER_PERMISSIONS
app.state.config.WEBHOOK_URL = WEBHOOK_URL
app.state.config.BANNERS = WEBUI_BANNERS

app.state.config.ENABLE_COMMUNITY_SHARING = ENABLE_COMMUNITY_SHARING
app.state.config.ENABLE_MESSAGE_RATING = ENABLE_MESSAGE_RATING

app.state.config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
app.state.config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
app.state.config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM

app.state.MODELS = {}
app.state.TOOLS = {}
app.state.FUNCTIONS = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(configs.router, prefix="/configs", tags=["configs"])
app.include_router(auths.router, prefix="/auths", tags=["auths"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(chats.router, prefix="/chats", tags=["chats"])

app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
app.include_router(prompts.router, prefix="/prompts", tags=["prompts"])

app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])
app.include_router(functions.router, prefix="/functions", tags=["functions"])

app.include_router(memories.router, prefix="/memories", tags=["memories"])
app.include_router(utils.router, prefix="/utils", tags=["utils"])


@app.get("/")
async def get_status():
    return {
        "status": True,
        "auth": WEBUI_AUTH,
        "default_models": app.state.config.DEFAULT_MODELS,
        "default_prompt_suggestions": app.state.config.DEFAULT_PROMPT_SUGGESTIONS,
    }


def get_function_module(pipe_id: str):
    # Check if function is already loaded
    if pipe_id not in app.state.FUNCTIONS:
        function_module, _, _ = load_function_module_by_id(pipe_id)
        app.state.FUNCTIONS[pipe_id] = function_module
    else:
        function_module = app.state.FUNCTIONS[pipe_id]

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(pipe_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))
    return function_module


async def get_pipe_models():
    pipes = Functions.get_functions_by_type("pipe", active_only=True)
    pipe_models = []

    for pipe in pipes:
        function_module = get_function_module(pipe.id)

        # Check if function is a manifold
        if hasattr(function_module, "pipes"):
            sub_pipes = []

            # Check if pipes is a function or a list

            try:
                if callable(function_module.pipes):
                    sub_pipes = function_module.pipes()
                else:
                    sub_pipes = function_module.pipes
            except Exception as e:
                log.exception(e)
                sub_pipes = []

            print(sub_pipes)

            for p in sub_pipes:
                sub_pipe_id = f'{pipe.id}.{p["id"]}'
                sub_pipe_name = p["name"]

                if hasattr(function_module, "name"):
                    sub_pipe_name = f"{function_module.name}{sub_pipe_name}"

                pipe_flag = {"type": pipe.type}
                pipe_models.append(
                    {
                        "id": sub_pipe_id,
                        "name": sub_pipe_name,
                        "object": "model",
                        "created": pipe.created_at,
                        "owned_by": "openai",
                        "pipe": pipe_flag,
                    }
                )
        else:
            pipe_flag = {"type": "pipe"}

            pipe_models.append(
                {
                    "id": pipe.id,
                    "name": pipe.name,
                    "object": "model",
                    "created": pipe.created_at,
                    "owned_by": "openai",
                    "pipe": pipe_flag,
                }
            )

    return pipe_models


async def execute_pipe(pipe, params):
    if inspect.iscoroutinefunction(pipe):
        return await pipe(**params)
    else:
        return pipe(**params)


async def get_message_content(res: str | Generator | AsyncGenerator) -> str:
    if isinstance(res, str):
        return res
    if isinstance(res, Generator):
        return "".join(map(str, res))
    if isinstance(res, AsyncGenerator):
        return "".join([str(stream) async for stream in res])


def process_line(form_data: dict, line):
    if isinstance(line, BaseModel):
        line = line.model_dump_json()
        line = f"data: {line}"
    if isinstance(line, dict):
        line = f"data: {json.dumps(line)}"

    try:
        line = line.decode("utf-8")
    except Exception:
        pass

    if line.startswith("data:"):
        return f"{line}\n\n"
    else:
        line = openai_chat_chunk_message_template(form_data["model"], line)
        return f"data: {json.dumps(line)}\n\n"


def get_pipe_id(form_data: dict) -> str:
    pipe_id = form_data["model"]
    if "." in pipe_id:
        pipe_id, _ = pipe_id.split(".", 1)
    print(pipe_id)
    return pipe_id


def get_function_params(function_module, form_data, user, extra_params=None):
    if extra_params is None:
        extra_params = {}

    pipe_id = get_pipe_id(form_data)

    # Get the signature of the function
    sig = inspect.signature(function_module.pipe)
    params = {"body": form_data} | {
        k: v for k, v in extra_params.items() if k in sig.parameters
    }

    if "__user__" in params and hasattr(function_module, "UserValves"):
        user_valves = Functions.get_user_valves_by_id_and_user_id(pipe_id, user.id)
        try:
            params["__user__"]["valves"] = function_module.UserValves(**user_valves)
        except Exception as e:
            log.exception(e)
            params["__user__"]["valves"] = function_module.UserValves()

    return params


async def generate_function_chat_completion(form_data, user):
    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    metadata = form_data.pop("metadata", {})

    files = metadata.get("files", [])
    tool_ids = metadata.get("tool_ids", [])
    # Check if tool_ids is None
    if tool_ids is None:
        tool_ids = []

    __event_emitter__ = None
    __event_call__ = None
    __task__ = None
    __task_body__ = None

    if metadata:
        if all(k in metadata for k in ("session_id", "chat_id", "message_id")):
            __event_emitter__ = get_event_emitter(metadata)
            __event_call__ = get_event_call(metadata)
        __task__ = metadata.get("task", None)
        __task_body__ = metadata.get("task_body", None)

    extra_params = {
        "__event_emitter__": __event_emitter__,
        "__event_call__": __event_call__,
        "__task__": __task__,
        "__task_body__": __task_body__,
        "__files__": files,
        "__user__": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }
    extra_params["__tools__"] = get_tools(
        app,
        tool_ids,
        user,
        {
            **extra_params,
            "__model__": app.state.MODELS[form_data["model"]],
            "__messages__": form_data["messages"],
            "__files__": files,
        },
    )

    if model_info:
        if model_info.base_model_id:
            form_data["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        form_data = apply_model_params_to_body_openai(params, form_data)
        form_data = apply_model_system_prompt_to_body(params, form_data, user)

    pipe_id = get_pipe_id(form_data)
    function_module = get_function_module(pipe_id)

    pipe = function_module.pipe
    params = get_function_params(function_module, form_data, user, extra_params)

    if form_data.get("stream", False):

        async def stream_content():
            try:
                res = await execute_pipe(pipe, params)

                # Directly return if the response is a StreamingResponse
                if isinstance(res, StreamingResponse):
                    async for data in res.body_iterator:
                        yield data
                    return
                if isinstance(res, dict):
                    yield f"data: {json.dumps(res)}\n\n"
                    return

            except Exception as e:
                print(f"Error: {e}")
                yield f"data: {json.dumps({'error': {'detail':str(e)}})}\n\n"
                return

            if isinstance(res, str):
                message = openai_chat_chunk_message_template(form_data["model"], res)
                yield f"data: {json.dumps(message)}\n\n"

            if isinstance(res, Iterator):
                for line in res:
                    yield process_line(form_data, line)

            if isinstance(res, AsyncGenerator):
                async for line in res:
                    yield process_line(form_data, line)

            if isinstance(res, str) or isinstance(res, Generator):
                finish_message = openai_chat_chunk_message_template(
                    form_data["model"], ""
                )
                finish_message["choices"][0]["finish_reason"] = "stop"
                yield f"data: {json.dumps(finish_message)}\n\n"
                yield "data: [DONE]"

        return StreamingResponse(stream_content(), media_type="text/event-stream")
    else:
        try:
            res = await execute_pipe(pipe, params)

        except Exception as e:
            print(f"Error: {e}")
            return {"error": {"detail": str(e)}}

        if isinstance(res, StreamingResponse) or isinstance(res, dict):
            return res
        if isinstance(res, BaseModel):
            return res.model_dump()

        message = await get_message_content(res)
        return openai_chat_completion_message_template(form_data["model"], message)

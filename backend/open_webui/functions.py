import logging
import sys
import inspect
import json
import asyncio

from pydantic import BaseModel
from typing import AsyncGenerator, Generator, Iterator
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
from starlette.responses import Response, StreamingResponse


from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
)


from open_webui.models.functions import Functions
from open_webui.models.models import Models

from open_webui.utils.plugin import (
    load_function_module_by_id,
    get_function_module_from_cache,
)
from open_webui.utils.tools import get_tools
from open_webui.utils.access_control import has_access

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

from open_webui.utils.misc import (
    add_or_update_system_message,
    get_last_user_message,
    prepend_to_first_user_message_content,
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def get_function_module_by_id(request: Request, pipe_id: str):
    function_module, _, _ = get_function_module_from_cache(request, pipe_id)

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(pipe_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))
    return function_module


async def get_function_models(request):
    pipes = Functions.get_functions_by_type("pipe", active_only=True)
    pipe_models = []

    for pipe in pipes:
        function_module = get_function_module_by_id(request, pipe.id)

        # Check if function is a manifold
        if hasattr(function_module, "pipes"):
            sub_pipes = []

            # Handle pipes being a list, sync function, or async function
            try:
                if callable(function_module.pipes):
                    if asyncio.iscoroutinefunction(function_module.pipes):
                        sub_pipes = await function_module.pipes()
                    else:
                        sub_pipes = function_module.pipes()
                else:
                    sub_pipes = function_module.pipes
            except Exception as e:
                log.exception(e)
                sub_pipes = []

            log.debug(
                f"get_function_models: function '{pipe.id}' is a manifold of {sub_pipes}"
            )

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

            log.debug(
                f"get_function_models: function '{pipe.id}' is a single pipe {{ 'id': {pipe.id}, 'name': {pipe.name} }}"
            )

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


async def generate_function_chat_completion(
    request, form_data, user, models: dict = {}
):
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
        "__chat_id__": metadata.get("chat_id", None),
        "__session_id__": metadata.get("session_id", None),
        "__message_id__": metadata.get("message_id", None),
        "__task__": __task__,
        "__task_body__": __task_body__,
        "__files__": files,
        "__user__": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
        "__metadata__": metadata,
        "__request__": request,
    }
    extra_params["__tools__"] = get_tools(
        request,
        tool_ids,
        user,
        {
            **extra_params,
            "__model__": models.get(form_data["model"], None),
            "__messages__": form_data["messages"],
            "__files__": files,
        },
    )

    if model_info:
        if model_info.base_model_id:
            form_data["model"] = model_info.base_model_id

        params = model_info.params.model_dump()

        if params:
            system = params.pop("system", None)
            form_data = apply_model_params_to_body_openai(params, form_data)
            form_data = apply_model_system_prompt_to_body(
                system, form_data, metadata, user
            )

    pipe_id = get_pipe_id(form_data)
    function_module = get_function_module_by_id(request, pipe_id)

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
                log.error(f"Error: {e}")
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
            log.error(f"Error: {e}")
            return {"error": {"detail": str(e)}}

        if isinstance(res, StreamingResponse) or isinstance(res, dict):
            return res
        if isinstance(res, BaseModel):
            return res.model_dump()

        message = await get_message_content(res)
        return openai_chat_completion_message_template(form_data["model"], message)

import time
import logging
import sys

from aiocache import cached
from typing import Any, Optional
import random
import json
import inspect

from fastapi import Request
from starlette.responses import Response, StreamingResponse


from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
)
from open_webui.routers.tasks import generate_queries


from open_webui.models.users import UserModel
from open_webui.models.functions import Functions
from open_webui.models.models import Models

from open_webui.retrieval.utils import get_sources_from_files


from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import (
    get_task_model_id,
    rag_template,
    tools_function_calling_generation_template,
)
from open_webui.utils.misc import (
    add_or_update_system_message,
    get_last_user_message,
    prepend_to_first_user_message_content,
)
from open_webui.utils.tools import get_tools
from open_webui.utils.plugin import load_function_module_by_id


from open_webui.config import DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL, BYPASS_MODEL_ACCESS_CONTROL
from open_webui.constants import TASKS


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def chat_completion_filter_functions_handler(request, body, model, extra_params):
    skip_files = None

    def get_filter_function_ids(model):
        def get_priority(function_id):
            function = Functions.get_function_by_id(function_id)
            if function is not None and hasattr(function, "valves"):
                # TODO: Fix FunctionModel
                return (function.valves if function.valves else {}).get("priority", 0)
            return 0

        filter_ids = [
            function.id for function in Functions.get_global_filter_functions()
        ]
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

    filter_ids = get_filter_function_ids(model)
    for filter_id in filter_ids:
        filter = Functions.get_function_by_id(filter_id)
        if not filter:
            continue

        if filter_id in request.app.state.FUNCTIONS:
            function_module = request.app.state.FUNCTIONS[filter_id]
        else:
            function_module, _, _ = load_function_module_by_id(filter_id)
            request.app.state.FUNCTIONS[filter_id] = function_module

        # Check if the function has a file_handler variable
        if hasattr(function_module, "file_handler"):
            skip_files = function_module.file_handler

        # Apply valves to the function
        if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
            valves = Functions.get_function_valves_by_id(filter_id)
            function_module.valves = function_module.Valves(
                **(valves if valves else {})
            )

        if hasattr(function_module, "inlet"):
            try:
                inlet = function_module.inlet

                # Create a dictionary of parameters to be passed to the function
                params = {"body": body} | {
                    k: v
                    for k, v in {
                        **extra_params,
                        "__model__": model,
                        "__id__": filter_id,
                    }.items()
                    if k in inspect.signature(inlet).parameters
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


async def chat_completion_tools_handler(
    request: Request, body: dict, user: UserModel, models, extra_params: dict
) -> tuple[dict, dict]:
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
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )
    tools = get_tools(
        request,
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

    if request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE != "":
        template = request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

    tools_function_calling_prompt = tools_function_calling_generation_template(
        template, tools_specs
    )
    log.info(f"{tools_function_calling_prompt=}")
    payload = get_tools_function_calling_payload(
        body["messages"], task_model_id, tools_function_calling_prompt
    )

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
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
    request: Request, body: dict, user: UserModel
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
                bracket_start = queries_response.find("{")
                bracket_end = queries_response.rfind("}") + 1

                if bracket_start == -1 or bracket_end == -1:
                    raise Exception("No JSON object found in the response")

                queries_response = queries_response[bracket_start:bracket_end]
                queries_response = json.loads(queries_response)
            except Exception as e:
                queries_response = {"queries": [queries_response]}

            queries = queries_response.get("queries", [])
        except Exception as e:
            queries = []

        if len(queries) == 0:
            queries = [get_last_user_message(body["messages"])]

        sources = get_sources_from_files(
            files=files,
            queries=queries,
            embedding_function=request.app.state.EMBEDDING_FUNCTION,
            k=request.app.state.config.TOP_K,
            reranking_function=request.app.state.rf,
            r=request.app.state.config.RELEVANCE_THRESHOLD,
            hybrid_search=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        )

        log.debug(f"rag_contexts:sources: {sources}")
    return body, {"sources": sources}


async def process_chat_payload(request, form_data, user, model):
    metadata = {
        "chat_id": form_data.pop("chat_id", None),
        "message_id": form_data.pop("id", None),
        "session_id": form_data.pop("session_id", None),
        "tool_ids": form_data.get("tool_ids", None),
        "files": form_data.get("files", None),
    }
    form_data["metadata"] = metadata

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
        "__request__": request,
    }

    # Initialize events to store additional event to be sent to the client
    # Initialize contexts and citation
    models = request.app.state.MODELS
    events = []
    sources = []

    try:
        form_data, flags = await chat_completion_filter_functions_handler(
            request, form_data, model, extra_params
        )
    except Exception as e:
        return Exception(f"Error: {e}")

    tool_ids = form_data.pop("tool_ids", None)
    files = form_data.pop("files", None)

    metadata = {
        **metadata,
        "tool_ids": tool_ids,
        "files": files,
    }
    form_data["metadata"] = metadata

    try:
        form_data, flags = await chat_completion_tools_handler(
            request, form_data, user, models, extra_params
        )
        sources.extend(flags.get("sources", []))
    except Exception as e:
        log.exception(e)

    try:
        form_data, flags = await chat_completion_files_handler(request, form_data, user)
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
        prompt = get_last_user_message(form_data["messages"])

        if prompt is None:
            raise Exception("No user message found")
        if (
            request.app.state.config.RELEVANCE_THRESHOLD == 0
            and context_string.strip() == ""
        ):
            log.debug(
                f"With a 0 relevancy threshold for RAG, the context cannot be empty"
            )

        # Workaround for Ollama 2.0+ system prompt issue
        # TODO: replace with add_or_update_system_message
        if model["owned_by"] == "ollama":
            form_data["messages"] = prepend_to_first_user_message_content(
                rag_template(
                    request.app.state.config.RAG_TEMPLATE, context_string, prompt
                ),
                form_data["messages"],
            )
        else:
            form_data["messages"] = add_or_update_system_message(
                rag_template(
                    request.app.state.config.RAG_TEMPLATE, context_string, prompt
                ),
                form_data["messages"],
            )

    # If there are citations, add them to the data_items
    sources = [source for source in sources if source.get("source", {}).get("name", "")]

    if len(sources) > 0:
        events.append({"sources": sources})

    return form_data, events


async def process_chat_response(response, events):
    if not isinstance(response, StreamingResponse):
        return response

    content_type = response.headers["Content-Type"]
    is_openai = "text/event-stream" in content_type
    is_ollama = "application/x-ndjson" in content_type

    if not is_openai and not is_ollama:
        return response

    async def stream_wrapper(original_generator, events):
        def wrap_item(item):
            return f"data: {item}\n\n" if is_openai else f"{item}\n"

        for event in events:
            yield wrap_item(json.dumps(event))

        async for data in original_generator:
            yield data

    return StreamingResponse(
        stream_wrapper(response.body_iterator, events),
        headers=dict(response.headers),
    )

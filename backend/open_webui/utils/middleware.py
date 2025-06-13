import time
import logging
import sys

import asyncio
from aiocache import cached
from typing import Any, Optional
import random
import json
import inspect
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


from open_webui.models.message_metrics import MessageMetrics
from fastapi import Request
from fastapi import BackgroundTasks

from starlette.responses import Response, StreamingResponse


from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
    get_active_status_by_user_id,
)
from open_webui.routers.tasks import (
    generate_queries,
    generate_title,
    generate_image_prompt,
    generate_chat_tags,
)
from open_webui.routers.retrieval import process_web_search, SearchForm
from open_webui.routers.images import image_generations, GenerateImageForm


from open_webui.utils.webhook import post_webhook


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
    get_message_list,
    add_or_update_system_message,
    get_last_user_message,
    get_last_assistant_message,
    prepend_to_first_user_message_content,
)
from open_webui.utils.tools import get_tools, get_tools_async
from open_webui.utils.plugin import load_function_module_by_id


from open_webui.tasks import create_task

from open_webui.config import DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
from open_webui.env import (
    SRC_LOG_LEVELS,
    GLOBAL_LOG_LEVEL,
    BYPASS_MODEL_ACCESS_CONTROL,
    ENABLE_REALTIME_CHAT_SAVE,
)
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
    tools = await get_tools_async(
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

    # Debug: Log the user query
    user_message = get_last_user_message(body["messages"])
    log.info(f"=== USER QUERY FOR FUNCTION CALLING ===")
    log.info(f"User query: {user_message}")
    log.info(f"======================================")

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
        log.debug(f"{response=}")
        content = await get_content_from_response(response)
        log.info(f"=== FUNCTION CALLING RESPONSE ===")
        log.info(f"Model response for tool calling: {content}")
        log.info(f"==================================")

        if not content:
            return body, {}

        # Check if the response is an empty string (indicating no tools should be used)
        content_stripped = content.strip()
        if (
            content_stripped == '""'
            or content_stripped == ""
            or content_stripped.lower() in ["", '""', "no tools needed", "none"]
        ):
            log.debug("Model indicated no tools should be used")
            return body, {}

        try:
            # Parse multiple JSON objects from the response
            tool_calls = []

            log.info(f"=== PARSING TOOL CALLS ===")
            log.info(f"Raw content to parse: {repr(content)}")
            log.info(f"==========================")

            # First, try to parse as a single JSON array
            try:
                if content.strip().startswith("[") and content.strip().endswith("]"):
                    parsed_array = json.loads(content.strip())
                    log.debug(f"Parsed tool calls as JSON array: {parsed_array}")

                    # Handle case where array elements are JSON strings that need to be parsed again
                    tool_calls = []
                    for item in parsed_array:
                        if isinstance(item, str):
                            # Try to parse the string as JSON
                            try:
                                parsed_item = json.loads(item)
                                tool_calls.append(parsed_item)
                                log.debug(f"Parsed JSON string in array: {parsed_item}")
                            except json.JSONDecodeError:
                                log.warning(
                                    f"Failed to parse array item as JSON: {item}"
                                )
                        elif isinstance(item, dict):
                            # Already a dictionary, use as-is
                            tool_calls.append(item)
                        else:
                            log.warning(
                                f"Unexpected array item type: {type(item)}, value: {item}"
                            )
                else:
                    raise json.JSONDecodeError("Not a JSON array", content, 0)
            except json.JSONDecodeError:
                # If not a JSON array, try to parse multiple JSON objects separated by newlines
                lines = content.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and line.startswith("{") and line.endswith("}"):
                        try:
                            tool_call = json.loads(line)
                            tool_calls.append(tool_call)
                            log.debug(f"Parsed individual tool call: {tool_call}")
                        except json.JSONDecodeError as e:
                            log.warning(
                                f"Failed to parse line as JSON: {line}, error: {e}"
                            )
                            continue

                # If no valid tool calls found, try to find all JSON objects in the content
                if not tool_calls:
                    import re

                    # Find all JSON-like objects in the content
                    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
                    json_matches = re.findall(json_pattern, content)

                    for match in json_matches:
                        try:
                            tool_call = json.loads(match)
                            if "name" in tool_call:  # Ensure it looks like a tool call
                                tool_calls.append(tool_call)
                                log.debug(f"Parsed tool call from regex: {tool_call}")
                        except json.JSONDecodeError:
                            continue

                # If still no valid tool calls found, try the old single JSON approach
                if not tool_calls:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1

                    if json_start == -1 or json_end == 0:
                        log.debug(
                            "No JSON object found in response, treating as no tool usage"
                        )
                        return body, {}

                    json_content = content[json_start:json_end]
                    log.debug(f"Extracted JSON content: {json_content}")

                    try:
                        result = json.loads(json_content)
                        tool_calls = [result]
                    except json.JSONDecodeError as json_error:
                        log.error(f"JSON parsing failed for content: {json_content}")
                        log.error(f"JSON error: {json_error}")
                        log.error(f"Full response content: {repr(content)}")
                        # Try to find a more complete JSON object by looking for balanced braces
                        brace_count = 0
                        json_end_corrected = json_start
                        for i, char in enumerate(content[json_start:], json_start):
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end_corrected = i + 1
                                    break

                        if json_end_corrected > json_start:
                            json_content = content[json_start:json_end_corrected]
                            log.debug(f"Trying corrected JSON content: {json_content}")
                            try:
                                result = json.loads(json_content)
                                tool_calls = [result]
                            except json.JSONDecodeError:
                                log.error(
                                    f"Corrected JSON parsing also failed, treating as no tool usage"
                                )
                                return body, {}
                        else:
                            log.error(
                                f"Could not find balanced JSON, treating as no tool usage"
                            )
                            return body, {}

            log.info(f"=== PARSED TOOL CALLS ===")
            log.info(f"Total tool calls extracted: {len(tool_calls)}")
            for i, call in enumerate(tool_calls):
                log.info(f"Tool call {i}: {call}")
            log.info(f"=========================")

            # Process all tool calls
            for tool_call in tool_calls:
                tool_function_name = tool_call.get("name", None)
                if not tool_function_name or tool_function_name not in tools:
                    log.debug(
                        f"Tool function '{tool_function_name}' not found in available tools"
                    )
                    continue

                tool_function_params = tool_call.get("parameters", {})
                log.info(f"=== TOOL CALL DEBUG ===")
                log.info(f"Tool: {tool_function_name}")
                log.info(f"Raw parameters from model: {tool_function_params}")
                log.info(f"=======================)")

                try:
                    # Get all parameters from the tool spec, not just required ones
                    all_params = (
                        tools[tool_function_name]
                        .get("spec", {})
                        .get("parameters", {})
                        .get("properties", {})
                    )
                    tool_function = tools[tool_function_name]["callable"]

                    # Filter to only include parameters that exist in the tool spec and are not None/null
                    filtered_params = {
                        k: v
                        for k, v in tool_function_params.items()
                        if k in all_params and v is not None and v != "null" and v != ""
                    }
                    log.info(f"Filtered parameters to pass to tool: {filtered_params}")
                    tool_output = await tool_function(**filtered_params)

                except Exception as e:
                    tool_output = str(e)

                if isinstance(tool_output, str):
                    log.info(
                        f"Tool {tool_function_name} output: {tool_output[:200]}..."
                    )  # Log first 200 chars
                    if tools[tool_function_name]["citation"]:
                        source_entry = {
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
                        sources.append(source_entry)
                        log.info(
                            f"Added source entry for {tool_function_name}: {source_entry['source']['name']}"
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


async def chat_web_search_handler(
    request: Request, form_data: dict, extra_params: dict, user
):
    event_emitter = extra_params["__event_emitter__"]
    await event_emitter(
        {
            "type": "status",
            "data": {
                "action": "web_search",
                "description": "Generating search query",
                "done": False,
            },
        }
    )

    messages = form_data["messages"]
    user_message = get_last_user_message(messages)

    queries = []
    try:
        res = await generate_queries(
            request,
            {
                "model": form_data["model"],
                "messages": messages,
                "prompt": user_message,
                "type": "web_search",
            },
            user,
        )

        response = res["choices"][0]["message"]["content"]

        try:
            bracket_start = response.find("{")
            bracket_end = response.rfind("}") + 1

            if bracket_start == -1 or bracket_end == -1:
                raise Exception("No JSON object found in the response")

            response = response[bracket_start:bracket_end]
            queries = json.loads(response)
            queries = queries.get("queries", [])
        except Exception as e:
            queries = [response]

    except Exception as e:
        log.exception(e)
        queries = [user_message]

    if len(queries) == 0:
        await event_emitter(
            {
                "type": "status",
                "data": {
                    "action": "web_search",
                    "description": "No search query generated",
                    "done": True,
                },
            }
        )
        return

    searchQuery = queries[0]

    await event_emitter(
        {
            "type": "status",
            "data": {
                "action": "web_search",
                "description": 'Searching "{{searchQuery}}"',
                "query": searchQuery,
                "done": False,
            },
        }
    )

    try:

        results = await process_web_search(
            request,
            SearchForm(
                **{
                    "query": searchQuery,
                }
            ),
            user=user,
        )

        if results:
            await event_emitter(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search",
                        "description": "Searched {{count}} sites",
                        "query": searchQuery,
                        "urls": results["filenames"],
                        "done": True,
                    },
                }
            )

            files = form_data.get("files", [])
            files.append(
                {
                    "collection_name": results["collection_name"],
                    "name": searchQuery,
                    "type": "web_search_results",
                    "urls": results["filenames"],
                }
            )
            form_data["files"] = files
        else:
            await event_emitter(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search",
                        "description": "No search results found",
                        "query": searchQuery,
                        "done": True,
                        "error": True,
                    },
                }
            )
    except Exception as e:
        log.exception(e)
        await event_emitter(
            {
                "type": "status",
                "data": {
                    "action": "web_search",
                    "description": 'Error searching "{{searchQuery}}"',
                    "query": searchQuery,
                    "done": True,
                    "error": True,
                },
            }
        )

    return form_data


async def chat_image_generation_handler(
    request: Request, form_data: dict, extra_params: dict, user
):
    __event_emitter__ = extra_params["__event_emitter__"]
    await __event_emitter__(
        {
            "type": "status",
            "data": {"description": "Generating an image", "done": False},
        }
    )

    messages = form_data["messages"]
    user_message = get_last_user_message(messages)

    prompt = user_message
    negative_prompt = ""

    if request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION:
        try:
            res = await generate_image_prompt(
                request,
                {
                    "model": form_data["model"],
                    "messages": messages,
                },
                user,
            )

            response = res["choices"][0]["message"]["content"]

            try:
                bracket_start = response.find("{")
                bracket_end = response.rfind("}") + 1

                if bracket_start == -1 or bracket_end == -1:
                    raise Exception("No JSON object found in the response")

                response = response[bracket_start:bracket_end]
                response = json.loads(response)
                prompt = response.get("prompt", [])
            except Exception as e:
                prompt = user_message

        except Exception as e:
            log.exception(e)
            prompt = user_message

    system_message_content = ""

    try:
        images = await image_generations(
            request=request,
            form_data=GenerateImageForm(**{"prompt": prompt}),
            user=user,
        )

        await __event_emitter__(
            {
                "type": "status",
                "data": {"description": "Generated an image", "done": True},
            }
        )

        for image in images:
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {"content": f"![Generated Image]({image['url']})\n"},
                }
            )

        system_message_content = "<context>User is shown the generated image, tell the user that the image has been generated</context>"
    except Exception as e:
        log.exception(e)
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": f"An error occured while generating an image",
                    "done": True,
                },
            }
        )

        system_message_content = "<context>Unable to generate an image, tell the user that an error occured</context>"

    if system_message_content:
        form_data["messages"] = add_or_update_system_message(
            system_message_content, form_data["messages"]
        )

    return form_data


async def chat_completion_files_handler(
    request: Request, body: dict, user: UserModel
) -> tuple[dict, dict[str, list]]:
    sources = []

    if files := body.get("metadata", {}).get("files", None):
        try:
            queries_response = await generate_queries(
                request,
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

        try:
            # Offload get_sources_from_files to a separate thread
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                sources = await loop.run_in_executor(
                    executor,
                    lambda: get_sources_from_files(
                        files=files,
                        queries=queries,
                        embedding_function=request.app.state.EMBEDDING_FUNCTION,
                        k=request.app.state.config.TOP_K,
                        reranking_function=request.app.state.rf,
                        r=request.app.state.config.RELEVANCE_THRESHOLD,
                        hybrid_search=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
                        full_context=request.app.state.config.RAG_FULL_CONTEXT,
                    ),
                )
        except Exception as e:
            log.exception(e)

        log.debug(f"rag_contexts:sources: {sources}")

    return body, {"sources": sources}


def apply_params_to_form_data(form_data, model):
    params = form_data.pop("params", {})
    if model.get("ollama"):
        form_data["options"] = params

        if "format" in params:
            form_data["format"] = params["format"]

        if "keep_alive" in params:
            form_data["keep_alive"] = params["keep_alive"]
    else:
        if "seed" in params:
            form_data["seed"] = params["seed"]

        if "stop" in params:
            form_data["stop"] = params["stop"]

        if "temperature" in params:
            form_data["temperature"] = params["temperature"]

        if "top_p" in params:
            form_data["top_p"] = params["top_p"]

        if "frequency_penalty" in params:
            form_data["frequency_penalty"] = params["frequency_penalty"]

        if "reasoning_effort" in params:
            form_data["reasoning_effort"] = params["reasoning_effort"]

    return form_data


async def process_chat_payload(request, form_data, metadata, user, model):
    form_data = apply_params_to_form_data(form_data, model)
    log.debug(f"form_data: {form_data}")

    event_emitter = get_event_emitter(metadata)
    event_call = get_event_call(metadata)

    extra_params = {
        "__event_emitter__": event_emitter,
        "__event_call__": event_call,
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

    user_message = get_last_user_message(form_data["messages"])
    model_knowledge = model.get("info", {}).get("meta", {}).get("knowledge", False)

    if model_knowledge:
        await event_emitter(
            {
                "type": "status",
                "data": {
                    "action": "knowledge_search",
                    "query": user_message,
                    "done": False,
                },
            }
        )

        knowledge_files = []
        for item in model_knowledge:
            if item.get("collection_name"):
                knowledge_files.append(
                    {
                        "id": item.get("collection_name"),
                        "name": item.get("name"),
                        "legacy": True,
                    }
                )
            elif item.get("collection_names"):
                knowledge_files.append(
                    {
                        "name": item.get("name"),
                        "type": "collection",
                        "collection_names": item.get("collection_names"),
                        "legacy": True,
                    }
                )
            else:
                knowledge_files.append(item)

        files = form_data.get("files", [])
        files.extend(knowledge_files)
        form_data["files"] = files

    features = form_data.pop("features", None)
    if features:
        if "web_search" in features and features["web_search"]:
            form_data = await chat_web_search_handler(
                request, form_data, extra_params, user
            )

        if "image_generation" in features and features["image_generation"]:
            form_data = await chat_image_generation_handler(
                request, form_data, extra_params, user
            )

    try:
        form_data, flags = await chat_completion_filter_functions_handler(
            request, form_data, model, extra_params
        )
    except Exception as e:
        raise Exception(f"Error: {e}")

    tool_ids = form_data.pop("tool_ids", None)
    files = form_data.pop("files", None)
    # Remove files duplicates
    if files:
        files = list({json.dumps(f, sort_keys=True): f for f in files}.values())

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
        log.info(f"Generated context string length: {len(context_string)}")
        log.info(
            f"Context string preview: {context_string[:500]}..."
        )  # Log first 500 chars

        # Debug: Log the complete context structure for tools
        if any(
            "TOOL:" in source.get("source", {}).get("name", "") for source in sources
        ):
            log.info("=== COMPLETE TOOL CONTEXT DEBUG ===")
            log.info(f"Full context string: {context_string}")
            log.info("=== END COMPLETE TOOL CONTEXT DEBUG ===")

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
        rag_content = rag_template(
            request.app.state.config.RAG_TEMPLATE, context_string, prompt
        )
        log.info(f"RAG template content length: {len(rag_content)}")
        log.info(f"RAG template preview: {rag_content[:500]}...")

        if model["owned_by"] == "ollama":
            form_data["messages"] = prepend_to_first_user_message_content(
                rag_content,
                form_data["messages"],
            )
        else:
            form_data["messages"] = add_or_update_system_message(
                rag_content,
                form_data["messages"],
            )

        # Log the final messages to see what gets sent to the model
        log.info(f"Final messages count: {len(form_data['messages'])}")
        for idx, msg in enumerate(form_data["messages"]):
            log.info(
                f"Message {idx} ({msg['role']}): {msg['content'][:300]}..."
            )  # Log first 300 chars

    # If there are citations, add them to the data_items
    sources = [source for source in sources if source.get("source", {}).get("name", "")]

    if len(sources) > 0:
        events.append({"sources": sources})

    if model_knowledge:
        await event_emitter(
            {
                "type": "status",
                "data": {
                    "action": "knowledge_search",
                    "query": user_message,
                    "done": True,
                    "hidden": True,
                },
            }
        )

    return form_data, events


async def process_chat_response(
    request, response, form_data, user, events, metadata, tasks
):
    async def background_tasks_handler():
        message_map = Chats.get_messages_by_chat_id(metadata["chat_id"])
        message = message_map.get(metadata["message_id"]) if message_map else None

        if message:
            messages = get_message_list(message_map, message.get("id"))

            if tasks:
                if TASKS.TITLE_GENERATION in tasks:
                    if tasks[TASKS.TITLE_GENERATION]:
                        res = await generate_title(
                            request,
                            {
                                "model": message["model"],
                                "messages": messages,
                                "chat_id": metadata["chat_id"],
                            },
                            user,
                        )

                        if res and isinstance(res, dict):
                            if len(res.get("choices", [])) == 1:
                                title = (
                                    res.get("choices", [])[0]
                                    .get("message", {})
                                    .get(
                                        "content",
                                        message.get("content", "New Chat"),
                                    )
                                ).strip()
                            else:
                                title = None

                            if not title:
                                title = messages[0].get("content", "New Chat")

                            Chats.update_chat_title_by_id(metadata["chat_id"], title)

                            await event_emitter(
                                {
                                    "type": "chat:title",
                                    "data": title,
                                }
                            )
                    elif len(messages) == 2:
                        title = messages[0].get("content", "New Chat")

                        Chats.update_chat_title_by_id(metadata["chat_id"], title)

                        await event_emitter(
                            {
                                "type": "chat:title",
                                "data": message.get("content", "New Chat"),
                            }
                        )

                if TASKS.TAGS_GENERATION in tasks and tasks[TASKS.TAGS_GENERATION]:
                    res = await generate_chat_tags(
                        request,
                        {
                            "model": message["model"],
                            "messages": messages,
                            "chat_id": metadata["chat_id"],
                        },
                        user,
                    )

                    if res and isinstance(res, dict):
                        if len(res.get("choices", [])) == 1:
                            tags_string = (
                                res.get("choices", [])[0]
                                .get("message", {})
                                .get("content", "")
                            )
                        else:
                            tags_string = ""

                        tags_string = tags_string[
                            tags_string.find("{") : tags_string.rfind("}") + 1
                        ]

                        try:
                            tags = json.loads(tags_string).get("tags", [])
                            Chats.update_chat_tags_by_id(
                                metadata["chat_id"], tags, user
                            )

                            await event_emitter(
                                {
                                    "type": "chat:tags",
                                    "data": tags,
                                }
                            )
                        except Exception as e:
                            pass

    event_emitter = None
    if (
        "session_id" in metadata
        and metadata["session_id"]
        and "chat_id" in metadata
        and metadata["chat_id"]
        and "message_id" in metadata
        and metadata["message_id"]
    ):
        event_emitter = get_event_emitter(metadata)

    if not isinstance(response, StreamingResponse):
        if event_emitter:

            if "selected_model_id" in response:
                Chats.upsert_message_to_chat_by_id_and_message_id(
                    metadata["chat_id"],
                    metadata["message_id"],
                    {
                        "selectedModelId": response["selected_model_id"],
                    },
                )

            if response.get("choices", [])[0].get("message", {}).get("content"):
                content = response["choices"][0]["message"]["content"]

                if content:

                    await event_emitter(
                        {
                            "type": "chat:completion",
                            "data": response,
                        }
                    )

                    title = Chats.get_chat_title_by_id(metadata["chat_id"])

                    await event_emitter(
                        {
                            "type": "chat:completion",
                            "data": {
                                "done": True,
                                "content": content,
                                "title": title,
                            },
                        }
                    )

                    # Save message in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            "content": content,
                        },
                    )

                    # Send a webhook notification if the user is not active
                    if get_active_status_by_user_id(user.id) is None:
                        webhook_url = Users.get_user_webhook_url_by_id(user.id)
                        if webhook_url:
                            post_webhook(
                                webhook_url,
                                f"{title} - {request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}\n\n{content}",
                                {
                                    "action": "chat",
                                    "message": content,
                                    "title": title,
                                    "url": f"{request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}",
                                },
                            )

                    # Send sources events after completion is done
                    for event in events:
                        if "sources" in event:
                            await event_emitter(
                                {
                                    "type": "chat:completion",
                                    "data": event,
                                }
                            )

                            # Save sources in the database
                            Chats.upsert_message_to_chat_by_id_and_message_id(
                                metadata["chat_id"],
                                metadata["message_id"],
                                {
                                    **event,
                                },
                            )

                    await background_tasks_handler()

            return response
        else:
            return response

    if not any(
        content_type in response.headers["Content-Type"]
        for content_type in ["text/event-stream", "application/x-ndjson"]
    ):
        return response

    if event_emitter:

        task_id = str(uuid4())  # Create a unique task ID.

        # Handle as a background task
        async def post_response_handler(response, events):
            message = Chats.get_message_by_id_and_message_id(
                metadata["chat_id"], metadata["message_id"]
            )
            content = message.get("content", "") if message else ""

            try:
                # Separate sources events from other events
                sources_events = []
                other_events = []

                for event in events:
                    if "sources" in event:
                        sources_events.append(event)
                    else:
                        other_events.append(event)

                # Process non-sources events first
                for event in other_events:
                    await event_emitter(
                        {
                            "type": "chat:completion",
                            "data": event,
                        }
                    )

                    # Save message in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            **event,
                        },
                    )

                # We might want to disable this by default
                detect_reasoning = True
                reasoning_tags = ["think", "reason", "reasoning", "thought", "Thought"]
                current_tag = None

                reasoning_start_time = None

                reasoning_content = ""
                ongoing_content = ""

                async for line in response.body_iterator:
                    line = line.decode("utf-8") if isinstance(line, bytes) else line
                    data = line

                    # Skip empty lines
                    if not data.strip():
                        continue

                    # "data:" is the prefix for each event
                    if not data.startswith("data:"):
                        continue

                    # Remove the prefix
                    data = data[len("data:") :].strip()

                    try:
                        data = json.loads(data)

                        if "usage" in data:
                            model_used = (
                                data["model"]
                                or metadata["selected_model_id"]
                                or form_data["model"]
                            )
                            MessageMetrics.insert_new_metrics(
                                user,
                                model_used,
                                data["usage"],
                            )

                        if "selected_model_id" in data:
                            Chats.upsert_message_to_chat_by_id_and_message_id(
                                metadata["chat_id"],
                                metadata["message_id"],
                                {
                                    "selectedModelId": data["selected_model_id"],
                                },
                            )
                        else:
                            value = (
                                data.get("choices", [])[0]
                                .get("delta", {})
                                .get("content")
                            )

                            if value:
                                content = f"{content}{value}"

                                if detect_reasoning:
                                    for tag in reasoning_tags:
                                        start_tag = f"<{tag}>\n"
                                        end_tag = f"</{tag}>\n"

                                        if start_tag in content:
                                            # Remove the start tag
                                            content = content.replace(start_tag, "")
                                            ongoing_content = content

                                            reasoning_start_time = time.time()
                                            reasoning_content = ""

                                            current_tag = tag
                                            break

                                    if reasoning_start_time is not None:
                                        # Remove the last value from the content
                                        content = content[: -len(value)]

                                        reasoning_content += value

                                        end_tag = f"</{current_tag}>\n"
                                        if end_tag in reasoning_content:
                                            reasoning_end_time = time.time()
                                            reasoning_duration = int(
                                                reasoning_end_time
                                                - reasoning_start_time
                                            )
                                            reasoning_content = (
                                                reasoning_content.strip(
                                                    f"<{current_tag}>\n"
                                                )
                                                .strip(end_tag)
                                                .strip()
                                            )

                                            if reasoning_content:
                                                reasoning_display_content = "\n".join(
                                                    (
                                                        f"> {line}"
                                                        if not line.startswith(">")
                                                        else line
                                                    )
                                                    for line in reasoning_content.splitlines()
                                                )

                                                # Format reasoning with <details> tag
                                                content = f'{ongoing_content}<details type="reasoning" done="true" duration="{reasoning_duration}">\n<summary>Thought for {reasoning_duration} seconds</summary>\n{reasoning_display_content}\n</details>\n'
                                            else:
                                                content = ""

                                            reasoning_start_time = None
                                        else:

                                            reasoning_display_content = "\n".join(
                                                (
                                                    f"> {line}"
                                                    if not line.startswith(">")
                                                    else line
                                                )
                                                for line in reasoning_content.splitlines()
                                            )

                                            # Show ongoing thought process
                                            content = f'{ongoing_content}<details type="reasoning" done="false">\n<summary>Thinking…</summary>\n{reasoning_display_content}\n</details>\n'

                                if ENABLE_REALTIME_CHAT_SAVE:
                                    # Save message in the database
                                    Chats.upsert_message_to_chat_by_id_and_message_id(
                                        metadata["chat_id"],
                                        metadata["message_id"],
                                        {
                                            "content": content,
                                        },
                                    )
                                else:
                                    data = {
                                        "content": content,
                                    }

                        await event_emitter(
                            {
                                "type": "chat:completion",
                                "data": data,
                            }
                        )
                    except Exception as e:
                        done = "data: [DONE]" in line
                        if done:
                            pass
                        else:
                            continue

                title = Chats.get_chat_title_by_id(metadata["chat_id"])
                data = {"done": True, "content": content, "title": title}

                if not ENABLE_REALTIME_CHAT_SAVE:
                    # Save message in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            "content": content,
                        },
                    )

                # Send a webhook notification if the user is not active
                if get_active_status_by_user_id(user.id) is None:
                    webhook_url = Users.get_user_webhook_url_by_id(user.id)
                    if webhook_url:
                        post_webhook(
                            webhook_url,
                            f"{title} - {request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}\n\n{content}",
                            {
                                "action": "chat",
                                "message": content,
                                "title": title,
                                "url": f"{request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}",
                            },
                        )

                await event_emitter(
                    {
                        "type": "chat:completion",
                        "data": data,
                    }
                )

                # Send sources events after completion is done
                for event in sources_events:
                    await event_emitter(
                        {
                            "type": "chat:completion",
                            "data": event,
                        }
                    )

                    # Save sources in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            **event,
                        },
                    )

                await background_tasks_handler()
            except asyncio.CancelledError:
                print("Task was cancelled!")
                await event_emitter({"type": "task-cancelled"})

                if not ENABLE_REALTIME_CHAT_SAVE:
                    # Save message in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            "content": content,
                        },
                    )

            if response.background is not None:
                await response.background()

        # background_tasks.add_task(post_response_handler, response, events)
        task_id, _ = create_task(post_response_handler(response, events))
        return {"status": True, "task_id": task_id}

    else:

        # Fallback to the original response
        async def stream_wrapper(original_generator, events):
            def wrap_item(item):
                return f"data: {item}\n\n"

            # Separate sources events from other events
            sources_events = []
            other_events = []

            for event in events:
                if "sources" in event:
                    sources_events.append(event)
                else:
                    other_events.append(event)

            # Send non-sources events first
            for event in other_events:
                yield wrap_item(json.dumps(event))

            # Stream the original response
            async for data in original_generator:
                yield data

            # Send sources events after completion
            for event in sources_events:
                yield wrap_item(json.dumps(event))

        return StreamingResponse(
            stream_wrapper(response.body_iterator, events),
            headers=dict(response.headers),
            background=response.background,
        )

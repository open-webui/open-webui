import time
import logging
import sys
import os
import base64
import textwrap

import asyncio
from aiocache import cached
from typing import Any, Optional
import random
import json
import html
import inspect
import re
import ast

from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from starlette.responses import Response, StreamingResponse, JSONResponse


from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.chats import Chats
from open_webui.models.folders import Folders
from open_webui.models.users import Users
from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
    get_active_status_by_user_id,
)
from open_webui.routers.tasks import (
    generate_queries,
    generate_title,
    generate_follow_ups,
    generate_image_prompt,
    generate_chat_tags,
)
from open_webui.routers.retrieval import (
    process_web_search,
    SearchForm,
)
from open_webui.routers.images import (
    load_b64_image_data,
    image_generations,
    GenerateImageForm,
    upload_image,
)
from open_webui.routers.pipelines import (
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)
from open_webui.models.memories import Memories
from open_webui.memory.mem0 import mem0_search, mem0_search_and_add

from open_webui.utils.webhook import post_webhook
from open_webui.utils.files import (
    get_audio_url_from_base64,
    get_file_url_from_base64,
    get_image_url_from_base64,
)


from open_webui.models.users import UserModel
from open_webui.models.functions import Functions
from open_webui.models.models import Models

from open_webui.retrieval.utils import get_sources_from_items


from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import (
    get_task_model_id,
    rag_template,
    tools_function_calling_generation_template,
)
from open_webui.utils.misc import (
    deep_update,
    extract_urls,
    get_message_list,
    add_or_update_system_message,
    add_or_update_user_message,
    get_last_user_message,
    get_last_user_message_item,
    get_last_assistant_message,
    get_system_message,
    prepend_to_first_user_message_content,
    convert_logit_bias_input_to_json,
    get_content_from_message,
    merge_consecutive_messages,
)
from open_webui.utils.tools import get_tools
from open_webui.utils.plugin import load_function_module_by_id
from open_webui.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)
from open_webui.utils.code_interpreter import execute_code_jupyter
from open_webui.utils.payload import apply_system_prompt_to_body
from open_webui.utils.mcp.client import MCPClient
from open_webui.utils.summary import (
    summarize,
    compute_token_count,
    slice_messages_with_summary,
)


from open_webui.config import (
    CACHE_DIR,
    DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    DEFAULT_CODE_INTERPRETER_PROMPT,
    CODE_INTERPRETER_BLOCKED_MODULES,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    GLOBAL_LOG_LEVEL,
    CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE,
    CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES,
    SUMMARY_TOKEN_THRESHOLD_DEFAULT,
    BYPASS_MODEL_ACCESS_CONTROL,
    ENABLE_REALTIME_CHAT_SAVE,
    ENABLE_QUERIES_CACHE,

    CHAT_DEBUG_FLAG,
)
from open_webui.constants import TASKS


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


DEFAULT_REASONING_TAGS = [
    ("<think>", "</think>"),
    ("<thinking>", "</thinking>"),
    ("<reason>", "</reason>"),
    ("<reasoning>", "</reasoning>"),
    ("<thought>", "</thought>"),
    ("<Thought>", "</Thought>"),
    ("<|begin_of_thought|>", "<|end_of_thought|>"),
    ("◁think▷", "◁/think▷"),
]
DEFAULT_SOLUTION_TAGS = [("<|begin_of_solution|>", "<|end_of_solution|>")]
DEFAULT_CODE_INTERPRETER_TAGS = [("<code_interpreter>", "</code_interpreter>")]


def process_tool_result(
    request,
    tool_function_name,
    tool_result,
    tool_type,
    direct_tool=False,
    metadata=None,
    user=None,
):
    tool_result_embeds = []

    if isinstance(tool_result, HTMLResponse):
        content_disposition = tool_result.headers.get("Content-Disposition", "")
        if "inline" in content_disposition:
            content = tool_result.body.decode("utf-8", "replace")
            tool_result_embeds.append(content)

            if 200 <= tool_result.status_code < 300:
                tool_result = {
                    "status": "success",
                    "code": "ui_component",
                    "message": f"{tool_function_name}: Embedded UI result is active and visible to the user.",
                }
            elif 400 <= tool_result.status_code < 500:
                tool_result = {
                    "status": "error",
                    "code": "ui_component",
                    "message": f"{tool_function_name}: Client error {tool_result.status_code} from embedded UI result.",
                }
            elif 500 <= tool_result.status_code < 600:
                tool_result = {
                    "status": "error",
                    "code": "ui_component",
                    "message": f"{tool_function_name}: Server error {tool_result.status_code} from embedded UI result.",
                }
            else:
                tool_result = {
                    "status": "error",
                    "code": "ui_component",
                    "message": f"{tool_function_name}: Unexpected status code {tool_result.status_code} from embedded UI result.",
                }
        else:
            tool_result = tool_result.body.decode("utf-8", "replace")

    elif (tool_type == "external" and isinstance(tool_result, tuple)) or (
        direct_tool and isinstance(tool_result, list) and len(tool_result) == 2
    ):
        tool_result, tool_response_headers = tool_result

        try:
            if not isinstance(tool_response_headers, dict):
                tool_response_headers = dict(tool_response_headers)
        except Exception as e:
            tool_response_headers = {}
            log.debug(e)

        if tool_response_headers and isinstance(tool_response_headers, dict):
            content_disposition = tool_response_headers.get(
                "Content-Disposition",
                tool_response_headers.get("content-disposition", ""),
            )

            if "inline" in content_disposition:
                content_type = tool_response_headers.get(
                    "Content-Type",
                    tool_response_headers.get("content-type", ""),
                )
                location = tool_response_headers.get(
                    "Location",
                    tool_response_headers.get("location", ""),
                )

                if "text/html" in content_type:
                    # Display as iframe embed
                    tool_result_embeds.append(tool_result)
                    tool_result = {
                        "status": "success",
                        "code": "ui_component",
                        "message": f"{tool_function_name}: Embedded UI result is active and visible to the user.",
                    }
                elif location:
                    tool_result_embeds.append(location)
                    tool_result = {
                        "status": "success",
                        "code": "ui_component",
                        "message": f"{tool_function_name}: Embedded UI result is active and visible to the user.",
                    }

    tool_result_files = []

    if isinstance(tool_result, list):
        if tool_type == "mcp":  # MCP
            tool_response = []
            for item in tool_result:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        if isinstance(text, str):
                            try:
                                text = json.loads(text)
                            except json.JSONDecodeError:
                                pass
                        tool_response.append(text)
                    elif item.get("type") in ["image", "audio"]:
                        file_url = get_file_url_from_base64(
                            request,
                            f"data:{item.get('mimeType')};base64,{item.get('data', item.get('blob', ''))}",
                            {
                                "chat_id": metadata.get("chat_id", None),
                                "message_id": metadata.get("message_id", None),
                                "session_id": metadata.get("session_id", None),
                                "result": item,
                            },
                            user,
                        )

                        tool_result_files.append(
                            {
                                "type": item.get("type", "data"),
                                "url": file_url,
                            }
                        )
            tool_result = tool_response[0] if len(tool_response) == 1 else tool_response
        else:  # OpenAPI
            for item in tool_result:
                if isinstance(item, str) and item.startswith("data:"):
                    tool_result_files.append(
                        {
                            "type": "data",
                            "content": item,
                        }
                    )
                    tool_result.remove(item)

    if isinstance(tool_result, list):
        tool_result = {"results": tool_result}

    if isinstance(tool_result, dict) or isinstance(tool_result, list):
        tool_result = json.dumps(tool_result, indent=2, ensure_ascii=False)

    return tool_result, tool_result_files, tool_result_embeds


async def chat_completion_tools_handler(
    request: Request, body: dict, extra_params: dict, user: UserModel, models, tools
) -> tuple[dict, dict]:
    async def get_content_from_response(response) -> Optional[str]:
        content = None
        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:
                data = json.loads(chunk.decode("utf-8", "replace"))
                content = data["choices"][0]["message"]["content"]

            # Cleanup any remaining background tasks if necessary
            if response.background is not None:
                await response.background()
        else:
            content = response["choices"][0]["message"]["content"]
        return content

    def get_tools_function_calling_payload(messages, task_model_id, content):
        user_message = get_last_user_message(messages)

        recent_messages = messages[-4:] if len(messages) > 4 else messages
        chat_history = "\n".join(
            f"{message['role'].upper()}: \"\"\"{get_content_from_message(message)}\"\"\""
            for message in recent_messages
        )

        prompt = f"History:\n{chat_history}\nQuery: {user_message}"

        return {
            "model": task_model_id,
            "messages": [
                {"role": "system", "content": content},
                {"role": "user", "content": f"Query: {prompt}"},
            ],
            "stream": False,
            "metadata": {"task": str(TASKS.FUNCTION_CALLING)},
        }

    event_caller = extra_params["__event_call__"]
    event_emitter = extra_params["__event_emitter__"]
    metadata = extra_params["__metadata__"]

    task_model_id = get_task_model_id(
        body["model"],
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    skip_files = False
    sources = []

    specs = [tool["spec"] for tool in tools.values()]
    tools_specs = json.dumps(specs)

    if request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE != "":
        template = request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

    tools_function_calling_prompt = tools_function_calling_generation_template(
        template, tools_specs
    )
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

            async def tool_call_handler(tool_call):
                nonlocal skip_files

                log.debug(f"{tool_call=}")

                tool_function_name = tool_call.get("name", None)
                if tool_function_name not in tools:
                    return body, {}

                tool_function_params = tool_call.get("parameters", {})

                tool = None
                tool_type = ""
                direct_tool = False

                try:
                    tool = tools[tool_function_name]
                    tool_type = tool.get("type", "")
                    direct_tool = tool.get("direct", False)

                    spec = tool.get("spec", {})
                    allowed_params = (
                        spec.get("parameters", {}).get("properties", {}).keys()
                    )
                    tool_function_params = {
                        k: v
                        for k, v in tool_function_params.items()
                        if k in allowed_params
                    }

                    if tool.get("direct", False):
                        tool_result = await event_caller(
                            {
                                "type": "execute:tool",
                                "data": {
                                    "id": str(uuid4()),
                                    "name": tool_function_name,
                                    "params": tool_function_params,
                                    "server": tool.get("server", {}),
                                    "session_id": metadata.get("session_id", None),
                                },
                            }
                        )
                    else:
                        tool_function = tool["callable"]
                        tool_result = await tool_function(**tool_function_params)

                except Exception as e:
                    tool_result = str(e)

                tool_result, tool_result_files, tool_result_embeds = (
                    process_tool_result(
                        request,
                        tool_function_name,
                        tool_result,
                        tool_type,
                        direct_tool,
                        metadata,
                        user,
                    )
                )

                if event_emitter:
                    if tool_result_files:
                        await event_emitter(
                            {
                                "type": "files",
                                "data": {
                                    "files": tool_result_files,
                                },
                            }
                        )

                    if tool_result_embeds:
                        await event_emitter(
                            {
                                "type": "embeds",
                                "data": {
                                    "embeds": tool_result_embeds,
                                },
                            }
                        )

                print(
                    f"Tool {tool_function_name} result: {tool_result}",
                    tool_result_files,
                    tool_result_embeds,
                )

                if tool_result:
                    tool = tools[tool_function_name]
                    tool_id = tool.get("tool_id", "")

                    tool_name = (
                        f"{tool_id}/{tool_function_name}"
                        if tool_id
                        else f"{tool_function_name}"
                    )

                    # Citation is enabled for this tool
                    sources.append(
                        {
                            "source": {
                                "name": (f"{tool_name}"),
                            },
                            "document": [str(tool_result)],
                            "metadata": [
                                {
                                    "source": (f"{tool_name}"),
                                    "parameters": tool_function_params,
                                }
                            ],
                            "tool_result": True,
                        }
                    )

                    # Citation is not enabled for this tool
                    body["messages"] = add_or_update_user_message(
                        f"\nTool `{tool_name}` Output: {tool_result}",
                        body["messages"],
                    )

                    if (
                        tools[tool_function_name]
                        .get("metadata", {})
                        .get("file_handler", False)
                    ):
                        skip_files = True

            # check if "tool_calls" in result
            if result.get("tool_calls"):
                for tool_call in result.get("tool_calls"):
                    await tool_call_handler(tool_call)
            else:
                await tool_call_handler(result)

        except Exception as e:
            log.debug(f"Error: {e}")
            content = None
    except Exception as e:
        log.debug(f"Error: {e}")
        content = None

    log.debug(f"tool_contexts: {sources}")

    if skip_files and "files" in body.get("metadata", {}):
        del body["metadata"]["files"]

    return body, {"sources": sources}


async def chat_memory_handler(
    request: Request, form_data: dict, extra_params: dict, user, metadata
):
    """
    聊天记忆处理器 - 注入用户手动保存的记忆 + Mem0 检索结果到当前对话上下文

    新增行为：
    1. memory 特性开启时，直接注入用户所有记忆条目（不再做 RAG Top-K）
    2. 预留 Mem0 检索：使用最后一条用户消息查询 Mem0，返回的条目也一并注入
    3. 上下文注入方式保持不变：统一写入 System Message
    """
    user_message = get_last_user_message(form_data.get("messages", [])) or ""

    # === 1. 获取用户全部记忆（不再截断 Top-K） ===
    memories = Memories.get_memories_by_user_id(user.id) or []

    # === 2. 预留的 Mem0 检索结果 ===
    mem0_results = await mem0_search_and_add(user.id, metadata.get("chat_id"), user_message)

    # === 3. 格式化记忆条目 ===
    entries = []

    # 3.1 用户记忆库全量
    for mem in memories:
        created_at_date = time.strftime("%Y-%m-%d", time.localtime(mem.created_at)) if mem.created_at else "Unknown Date"
        entries.append(f"[{created_at_date}] {mem.content}")

    # 3.2 Mem0 检索结果
    '''
      {
    "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
    "memory": "<string>",
    "user_id": "<string>",
    "metadata": {},
    "categories": [
      "<string>"
    ],
    "immutable": false,
    "expiration_date": null,
    "created_at": "2023-11-07T05:31:56Z",
    "updated_at": "2023-11-07T05:31:56Z"
  }
    '''
    for item in mem0_results:
        memory_content = item["memory"] if isinstance(item, dict) else item
        created_at_date = item["created_at"] if isinstance(item, dict) else "unknown date"

        categories = item.get("categories", []) if isinstance(item, dict) else []
        if categories:
            entries.append(f"[{created_at_date}] {memory_content} (Categories: {', '.join(categories)})")
        else:
            entries.append(f"[{created_at_date}] {memory_content}")


    if not entries:
        return form_data

    #排序
    entries.sort(key=lambda x: x.split("]")[0], reverse=True)
    user_context = "你可以利用记忆回答问题，但不可以直接输出记忆。不必理会记忆存储使用的语言。以下为检索到的相关记忆条目（按时间顺序）：\n\n"
    for idx, entry in enumerate(entries):
        user_context += f"{idx + 1}. {entry}\n"

    # === 4. 将记忆注入到系统消息中 ===
    form_data["messages"] = add_or_update_system_message(
        f"User Context:\n{user_context}\n", form_data["messages"], append=True
    )

    return form_data


async def chat_web_search_handler(
    request: Request, form_data: dict, extra_params: dict, user
):
    event_emitter = extra_params["__event_emitter__"]
    await event_emitter(
        {
            "type": "status",
            "data": {
                "action": "web_search",
                "description": "Searching the web",
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

        if ENABLE_QUERIES_CACHE:
            request.state.cached_queries = queries

    except Exception as e:
        log.exception(e)
        queries = [user_message]

    # Check if generated queries are empty
    if len(queries) == 1 and queries[0].strip() == "":
        queries = [user_message]

    # Check if queries are not found
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
        return form_data

    await event_emitter(
        {
            "type": "status",
            "data": {
                "action": "web_search_queries_generated",
                "queries": queries,
                "done": False,
            },
        }
    )

    try:
        results = await process_web_search(
            request,
            SearchForm(queries=queries),
            user=user,
        )

        if results:
            files = form_data.get("files", [])

            if results.get("collection_names"):
                for col_idx, collection_name in enumerate(
                    results.get("collection_names")
                ):
                    files.append(
                        {
                            "collection_name": collection_name,
                            "name": ", ".join(queries),
                            "type": "web_search",
                            "urls": results["filenames"],
                            "queries": queries,
                        }
                    )
            elif results.get("docs"):
                # Invoked when bypass embedding and retrieval is set to True
                docs = results["docs"]
                files.append(
                    {
                        "docs": docs,
                        "name": ", ".join(queries),
                        "type": "web_search",
                        "urls": results["filenames"],
                        "queries": queries,
                    }
                )

            form_data["files"] = files

            await event_emitter(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search",
                        "description": "Searched {{count}} sites",
                        "urls": results["filenames"],
                        "items": results.get("items", []),
                        "done": True,
                    },
                }
            )
        else:
            await event_emitter(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search",
                        "description": "No search results found",
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
                    "description": "An error occurred while searching the web",
                    "queries": queries,
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
            "data": {"description": "Creating image", "done": False},
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
                "data": {"description": "Image created", "done": True},
            }
        )

        await __event_emitter__(
            {
                "type": "files",
                "data": {
                    "files": [
                        {
                            "type": "image",
                            "url": image["url"],
                        }
                        for image in images
                    ]
                },
            }
        )

        system_message_content = "<context>User is shown the generated image, tell the user that the image has been generated</context>"
    except Exception as e:
        log.exception(e)
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": f"An error occurred while generating an image",
                    "done": True,
                },
            }
        )

        system_message_content = "<context>Unable to generate an image, tell the user that an error occurred</context>"

    if system_message_content:
        form_data["messages"] = add_or_update_system_message(
            system_message_content, form_data["messages"]
        )

    return form_data


async def chat_completion_files_handler(
    request: Request, body: dict, extra_params: dict, user: UserModel
) -> tuple[dict, dict[str, list]]:
    __event_emitter__ = extra_params["__event_emitter__"]
    sources = []

    if files := body.get("metadata", {}).get("files", None):
        # Check if all files are in full context mode
        all_full_context = all(item.get("context") == "full" for item in files)

        queries = []
        if not all_full_context:
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
            except:
                pass

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "queries_generated",
                        "queries": queries,
                        "done": False,
                    },
                }
            )

        if len(queries) == 0:
            queries = [get_last_user_message(body["messages"])]

        try:
            # Offload get_sources_from_items to a separate thread
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                sources = await loop.run_in_executor(
                    executor,
                    lambda: get_sources_from_items(
                        request=request,
                        items=files,
                        queries=queries,
                        embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                            query, prefix=prefix, user=user
                        ),
                        k=request.app.state.config.TOP_K,
                        reranking_function=(
                            (
                                lambda sentences: request.app.state.RERANKING_FUNCTION(
                                    sentences, user=user
                                )
                            )
                            if request.app.state.RERANKING_FUNCTION
                            else None
                        ),
                        k_reranker=request.app.state.config.TOP_K_RERANKER,
                        r=request.app.state.config.RELEVANCE_THRESHOLD,
                        hybrid_bm25_weight=request.app.state.config.HYBRID_BM25_WEIGHT,
                        hybrid_search=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
                        full_context=all_full_context
                        or request.app.state.config.RAG_FULL_CONTEXT,
                        user=user,
                    ),
                )
        except Exception as e:
            log.exception(e)

        log.debug(f"rag_contexts:sources: {sources}")

        unique_ids = set()
        for source in sources or []:
            if not source or len(source.keys()) == 0:
                continue

            documents = source.get("document") or []
            metadatas = source.get("metadata") or []
            src_info = source.get("source") or {}

            for index, _ in enumerate(documents):
                metadata = metadatas[index] if index < len(metadatas) else None
                _id = (
                    (metadata or {}).get("source")
                    or (src_info or {}).get("id")
                    or "N/A"
                )
                unique_ids.add(_id)

        sources_count = len(unique_ids)
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "action": "sources_retrieved",
                    "count": sources_count,
                    "done": True,
                },
            }
        )

    return body, {"sources": sources}


def apply_params_to_form_data(form_data, model):
    params = form_data.pop("params", {})
    custom_params = params.pop("custom_params", {})

    open_webui_params = {
        "stream_response": bool,
        "stream_delta_chunk_size": int,
        "function_calling": str,
        "reasoning_tags": list,
        "system": str,
    }

    for key in list(params.keys()):
        if key in open_webui_params:
            del params[key]

    if custom_params:
        # Attempt to parse custom_params if they are strings
        for key, value in custom_params.items():
            if isinstance(value, str):
                try:
                    # Attempt to parse the string as JSON
                    custom_params[key] = json.loads(value)
                except json.JSONDecodeError:
                    # If it fails, keep the original string
                    pass

        # If custom_params are provided, merge them into params
        params = deep_update(params, custom_params)

    if model.get("owned_by") == "ollama":
        # Ollama specific parameters
        form_data["options"] = params
    else:
        if isinstance(params, dict):
            for key, value in params.items():
                if value is not None:
                    form_data[key] = value

        if "logit_bias" in params and params["logit_bias"] is not None:
            try:
                form_data["logit_bias"] = json.loads(
                    convert_logit_bias_input_to_json(params["logit_bias"])
                )
            except Exception as e:
                log.exception(f"Error parsing logit_bias: {e}")

    return form_data


async def process_chat_payload(request, form_data, user, metadata, model):
    """
    处理聊天请求的 Payload - 执行 Pipeline、Filter、功能增强和工具注入

    这是聊天请求预处理的核心函数，按以下顺序执行：
    0. Billing Check (计费检查) - 检查用户余额是否充足 [激活]
    1. Pipeline Inlet (管道入口) - 自定义 Python 插件预处理 [已屏蔽]
    2. Filter Inlet (过滤器入口) - 函数过滤器预处理 [已屏蔽]
    3. Chat Memory (记忆) - 注入历史对话记忆 [激活]
    4. Chat Web Search (网页搜索) - 执行网络搜索并注入结果 [已屏蔽]
    5. Chat Image Generation (图像生成) - 处理图像生成请求 [已屏蔽]
    6. Chat Code Interpreter (代码解释器) - 注入代码执行提示词 [已屏蔽]
    7. Chat Tools Function Calling (工具调用) - 处理函数/工具调用 [已屏蔽]
    8. Chat Files (文件处理) - 处理上传文件、知识库文件、RAG 检索 [已屏蔽]

    === 功能屏蔽说明 ===
    当前已屏蔽功能（使用 if False 跳过）：
    - Folder "Project" System Prompt 和文件注入
    - Model "Knowledge" 知识库注入
    - Pipeline Inlet 自定义插件处理
    - Filter Inlet 函数过滤器处理
    - 图像生成功能
    - 代码解释器功能
    - MCP (Model Context Protocol) 工具连接
    - 标准工具（Function Tools）获取与调用
    - 文件处理与 RAG 检索（向量数据库检索、上下文注入）

    当前激活功能：
    - 计费检查（Billing Check）
    - 模型参数应用
    - System Prompt 变量替换
    - OAuth Token 获取
    - 记忆功能（Memory）
    - 网页搜索（Web Search）
    - 客户端直连工具服务器（Direct Tool Servers）
    - 文件夹类型文件展开

    Args:
        request: FastAPI Request 对象
        form_data: OpenAI 格式的聊天请求数据
        user: 用户对象
        metadata: 元数据（chat_id, message_id, tool_ids, files 等）
        model: 模型配置对象

    Returns:
        tuple: (form_data, metadata, events)
            - form_data: 处理后的请求数据
            - metadata: 更新后的元数据
            - events: 需要发送给前端的事件列表（如引用来源）
    """
    # === 0. 计费预检查 ===
    # 注意：只做预检查，不扣费。实际计费由openai.py负责
    from fastapi import HTTPException
    try:
        from open_webui.utils.billing import check_user_balance_threshold

        # 检查余额（默认阈值0.01元 = 100毫）
        check_user_balance_threshold(user.id, threshold=100)

    except HTTPException:
        # 重新抛出业务异常（余额不足/账户冻结）
        raise
    except Exception as e:
        # 其他异常仅记录日志，不阻断请求
        log.error(f"计费预检查异常: {e}")

    # === 1. 应用模型参数到请求 ===
    form_data = apply_params_to_form_data(form_data, model)
    log.debug(f"form_data: {form_data}")

    # === 1 基于摘要的上下文裁剪与系统提示 ===
    # - backend/open_webui/utils/middleware.py:process_chat_payload：
    # 每次请求先读取存量摘要，按 last_summary_id 切片"前 20 条 + 之后全部"消息，再用摘要构建唯一的 system prompt 置前；
    chat_id = metadata.get("chat_id", None)
    summary_record = None
    ordered_messages = form_data.get("messages", [])
    cold_start_ids = []

    # 1.1 读取摘要记录并裁剪消息列表
    if chat_id and user and not str(chat_id).startswith("local:"):
        try:
            # 获取当前会话的摘要记录
            summary_record = Chats.get_summary_by_user_id_and_chat_id(
                user.id, chat_id
            )
            # 获取冷启动消息 ID 列表（用于注入关键历史消息）
            chat_item = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
            if chat_item and isinstance(chat_item.meta, dict):
                cold_start_ids = chat_item.meta.get("recent_message_id_for_cold_start", []) or []
            
            if CHAT_DEBUG_FLAG:
                print(
                    f"[summary:payload] chat_id={chat_id} 有摘要={bool(summary_record)} "
                    f"上次摘要的 message_id={summary_record.get('last_message_id') if summary_record else None}"
                )
            # 基于摘要边界裁剪消息：保留边界前 20 条 + 边界后全部
            messages_map = Chats.get_messages_map_by_chat_id(chat_id) or {}
            anchor_id = metadata.get("message_id")
            ordered_messages = slice_messages_with_summary(
                messages_map,
                summary_record.get("last_message_id") if summary_record else None,
                anchor_id,
                pre_boundary=20,
            )

            if CHAT_DEBUG_FLAG:
                print("[summary:payload]: summary前 20 条 + summary 后全部")
                for i in ordered_messages:
                    print(i['role'], "  ", i['content'][:100])
                print(
                    f"[summary:payload] chat_id={chat_id} 切片后消息数={len(ordered_messages)} 当前锚点={anchor_id}"
                )
        except Exception as e:
            print(f"summary preprocessing failed: {e}")

    # 1.2 追加冷启动消息（避免重要上下文丢失）
    if cold_start_ids and chat_id and not str(chat_id).startswith("local:"):
        messages_map = Chats.get_messages_map_by_chat_id(chat_id) or {}
        seen_ids = {m.get("id") for m in ordered_messages if m.get("id")}
        if CHAT_DEBUG_FLAG:
            print("[summary:payload:cold_start]")
        for mid in cold_start_ids:
            msg = messages_map.get(mid)
            if not msg:
                continue
            print(msg['role'], "  ", msg['content'][:100])
            if mid in seen_ids:  # 跳过已存在的消息
                continue
            ordered_messages.append({**msg, "id": mid})
            seen_ids.add(mid)
        
        if CHAT_DEBUG_FLAG:
            print(
                f"[summary:payload:cold_start] chat_id={chat_id} 追加冷启动消息数={len(cold_start_ids)}"
            )

    # 1.3 注入摘要系统提示（替换原有 system 消息）
    if summary_record and summary_record.get("content"):
        summary_system_message = {
            "role": "system",
            "content": f"Conversation History Summary:\n{summary_record.get('content', '')}",
        }
        # 移除旧的 system 消息，插入摘要系统提示到开头
        ordered_messages = [
            m for m in ordered_messages if m.get("role") != "system"
        ]
        ordered_messages = [summary_system_message, *ordered_messages]

    if ordered_messages:
        # 合并连续的同角色消息，避免 LLM API 报错
        ordered_messages = merge_consecutive_messages(ordered_messages)
        form_data["messages"] = ordered_messages

    # === 2. 处理 System Prompt 变量替换 ===
    system_message = get_system_message(form_data.get("messages", []))
    if system_message:  # Chat Controls/User Settings
        try:
            # 替换 system prompt 中的变量（如 {{USER_NAME}}, {{CURRENT_DATE}}）
            form_data = apply_system_prompt_to_body(
                system_message.get("content"), form_data, metadata, user, replace=True
            )
        except:
            pass

    # === 3. 初始化事件发射器和回调 ===
    event_emitter = get_event_emitter(metadata)  # WebSocket 事件发射器
    event_call = get_event_call(metadata)  # 事件调用函数

    # === 4. 获取 OAuth Token ===
    oauth_token = None
    try:
        if request.cookies.get("oauth_session_id", None):
            oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                user.id,
                request.cookies.get("oauth_session_id", None),
            )
    except Exception as e:
        log.error(f"Error getting OAuth token: {e}")

    # === 5. 构建额外参数（供 Pipeline/Filter/Tools 使用）===
    extra_params = {
        "__event_emitter__": event_emitter,  # 用于向前端发送实时事件
        "__event_call__": event_call,  # 用于调用事件回调
        "__user__": user.model_dump() if isinstance(user, UserModel) else {},
        "__metadata__": metadata,
        "__request__": request,
        "__model__": model,
        "__oauth_token__": oauth_token,
    }

    # === 6. 确定模型列表和任务模型 ===
    # Initialize events to store additional event to be sent to the client
    # Initialize contexts and citation
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        # Direct 模式：使用用户直连的模型
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        # 标准模式：使用平台所有模型
        models = request.app.state.MODELS

    # 获取任务模型 ID（用于工具调用、标题生成等后台任务）
    task_model_id = get_task_model_id(
        form_data["model"],
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    # === 7. 初始化事件和引用来源列表 ===
    events = []  # 需要发送给前端的事件（如 sources 引用）
    sources = []  # RAG 检索到的文档来源

    # === 8. Folder "Project" 处理 - 注入文件夹的 System Prompt 和文件 [已屏蔽] ===
    # Check if the request has chat_id and is inside of a folder
    chat_id = metadata.get("chat_id", None)
    if False:
        if chat_id and user:
            chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
            if chat and chat.folder_id:
                folder = Folders.get_folder_by_id_and_user_id(chat.folder_id, user.id)

                if folder and folder.data:
                    # 注入文件夹的 system prompt
                    if "system_prompt" in folder.data:
                        form_data = apply_system_prompt_to_body(
                            folder.data["system_prompt"], form_data, metadata, user
                        )
                    # 注入文件夹关联的文件
                    if "files" in folder.data:
                        form_data["files"] = [
                            *folder.data["files"],
                            *form_data.get("files", []),
                        ]

    # === 9. Model "Knowledge" 处理 - 注入模型绑定的知识库 [已屏蔽] ===
    user_message = get_last_user_message(form_data["messages"])
    model_knowledge = model.get("info", {}).get("meta", {}).get("knowledge", False)

    if False:
        if model_knowledge:
            # 向前端发送知识库搜索状态
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
                # 处理旧格式的 collection_name
                if item.get("collection_name"):
                    knowledge_files.append(
                        {
                            "id": item.get("collection_name"),
                            "name": item.get("name"),
                            "legacy": True,
                        }
                    )
                # 处理新格式的 collection_names（多个集合）
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

            # 合并模型知识库文件和用户上传文件
            files = form_data.get("files", [])
            files.extend(knowledge_files)
            form_data["files"] = files

    # 清理前端元数据参数
    variables = form_data.pop("variables", None)

    # === 10. Pipeline Inlet 处理 - 执行自定义 Python 插件 [已屏蔽] ===
    # Process the form_data through the pipeline
    if False:
        try:
            form_data = await process_pipeline_inlet_filter(
                request, form_data, user, models
            )
        except Exception as e:
            raise e

    # === 11. Filter Inlet 处理 - 执行函数过滤器 [已屏蔽] ===
    if False:
        try:
            filter_functions = [
                Functions.get_function_by_id(filter_id)
                for filter_id in get_sorted_filter_ids(
                    request, model, metadata.get("filter_ids", [])
                )
            ]

            form_data, flags = await process_filter_functions(
                request=request,
                filter_functions=filter_functions,
                filter_type="inlet",
                form_data=form_data,
                extra_params=extra_params,
            )
        except Exception as e:
            raise Exception(f"{e}")

    # === 12. 功能增强处理 (Features) ===
    features = form_data.pop("features", None)
    if features:
        # 12.1 记忆功能 - 注入历史对话记忆
        if "memory" in features and features["memory"]:
            form_data = await chat_memory_handler(
                request, form_data, extra_params, user, metadata
            )

        # 12.2 网页搜索功能 - 执行网络搜索 [已屏蔽]
        if False:
            if "web_search" in features and features["web_search"]:
                form_data = await chat_web_search_handler(
                    request, form_data, extra_params, user
                )

        # 12.3 图像生成功能 - 处理图像生成请求 [已屏蔽]
        if False:
            if "image_generation" in features and features["image_generation"]:
                form_data = await chat_image_generation_handler(
                    request, form_data, extra_params, user
                )

        # 12.4 代码解释器功能 - 注入代码执行提示词 [已屏蔽]
        if False:
            if "code_interpreter" in features and features["code_interpreter"]:
                form_data["messages"] = add_or_update_user_message(
                    (
                        request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE
                        if request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE != ""
                        else DEFAULT_CODE_INTERPRETER_PROMPT
                    ),
                    form_data["messages"],
                )

    # === 13. 提取工具和文件信息 ===
    tool_ids = form_data.pop("tool_ids", None)
    files = form_data.pop("files", None)

    # === 14. 文件夹类型文件展开 ===
    prompt = get_last_user_message(form_data["messages"])

    if files:
        if not files:
            files = []

        for file_item in files:
            # 如果文件类型是 folder，展开其包含的所有文件
            if file_item.get("type", "file") == "folder":
                # Get folder files
                folder_id = file_item.get("id", None)
                if folder_id:
                    folder = Folders.get_folder_by_id_and_user_id(folder_id, user.id)
                    if folder and folder.data and "files" in folder.data:
                        # 移除文件夹项，添加文件夹内的文件
                        files = [f for f in files if f.get("id", None) != folder_id]
                        files = [*files, *folder.data["files"]]

        # 去重文件（基于文件内容）
        files = list({json.dumps(f, sort_keys=True): f for f in files}.values())

    # === 15. 更新元数据 ===
    metadata = {
        **metadata,
        "tool_ids": tool_ids,
        "files": files,
    }
    form_data["metadata"] = metadata

    # === 16. 准备工具字典 [部分屏蔽] ===
    # Server side tools
    tool_ids = metadata.get("tool_ids", None)  # 服务器端工具 ID
    # Client side tools
    direct_tool_servers = metadata.get("tool_servers", None)  # 客户端直连工具服务器

    log.debug(f"{tool_ids=}")
    log.debug(f"{direct_tool_servers=}")

    tools_dict = {}  # 所有工具的字典

    mcp_clients = {}  # MCP (Model Context Protocol) 客户端
    mcp_tools_dict = {}  # MCP 工具字典

    # === 16.1-16.2 处理 MCP 工具和标准工具 [已屏蔽] ===
    if False:
        if tool_ids:
            for tool_id in tool_ids:
                # === 16.1 处理 MCP (Model Context Protocol) 工具 ===
                if tool_id.startswith("server:mcp:"):
                    try:
                        server_id = tool_id[len("server:mcp:") :]

                        # 查找 MCP 服务器连接配置
                        mcp_server_connection = None
                        for (
                            server_connection
                        ) in request.app.state.config.TOOL_SERVER_CONNECTIONS:
                            if (
                                server_connection.get("type", "") == "mcp"
                                and server_connection.get("info", {}).get("id") == server_id
                            ):
                                mcp_server_connection = server_connection
                                break

                        if not mcp_server_connection:
                            log.error(f"MCP server with id {server_id} not found")
                            continue

                        # 处理认证类型
                        auth_type = mcp_server_connection.get("auth_type", "")

                        headers = {}
                        if auth_type == "bearer":
                            headers["Authorization"] = (
                                f"Bearer {mcp_server_connection.get('key', '')}"
                            )
                        elif auth_type == "none":
                            # 无需认证
                            pass
                        elif auth_type == "session":
                            headers["Authorization"] = (
                                f"Bearer {request.state.token.credentials}"
                            )
                        elif auth_type == "system_oauth":
                            oauth_token = extra_params.get("__oauth_token__", None)
                            if oauth_token:
                                headers["Authorization"] = (
                                    f"Bearer {oauth_token.get('access_token', '')}"
                                )
                        elif auth_type == "oauth_2.1":
                            try:
                                splits = server_id.split(":")
                                server_id = splits[-1] if len(splits) > 1 else server_id

                                oauth_token = await request.app.state.oauth_client_manager.get_oauth_token(
                                    user.id, f"mcp:{server_id}"
                                )

                                if oauth_token:
                                    headers["Authorization"] = (
                                        f"Bearer {oauth_token.get('access_token', '')}"
                                    )
                            except Exception as e:
                                log.error(f"Error getting OAuth token: {e}")
                                oauth_token = None

                        # 连接到 MCP 服务器
                        mcp_clients[server_id] = MCPClient()
                        await mcp_clients[server_id].connect(
                            url=mcp_server_connection.get("url", ""),
                            headers=headers if headers else None,
                        )

                        # 获取 MCP 工具列表并注册
                        tool_specs = await mcp_clients[server_id].list_tool_specs()
                        for tool_spec in tool_specs:

                            def make_tool_function(client, function_name):
                                """为每个 MCP 工具创建异步调用函数"""
                                async def tool_function(**kwargs):
                                    return await client.call_tool(
                                        function_name,
                                        function_args=kwargs,
                                    )

                                return tool_function

                            tool_function = make_tool_function(
                                mcp_clients[server_id], tool_spec["name"]
                            )

                            # 注册 MCP 工具到工具字典
                            mcp_tools_dict[f"{server_id}_{tool_spec['name']}"] = {
                                "spec": {
                                    **tool_spec,
                                    "name": f"{server_id}_{tool_spec['name']}",
                                },
                                "callable": tool_function,
                                "type": "mcp",
                                "client": mcp_clients[server_id],
                                "direct": False,
                            }
                    except Exception as e:
                        log.debug(e)
                        continue

            # === 16.2 获取标准工具（Function Tools）===
            tools_dict = await get_tools(
                request,
                tool_ids,
                user,
                {
                    **extra_params,
                    "__model__": models[task_model_id],
                    "__messages__": form_data["messages"],
                    "__files__": metadata.get("files", []),
                },
            )
            # 合并 MCP 工具
            if mcp_tools_dict:
                tools_dict = {**tools_dict, **mcp_tools_dict}

    # === 16.3 处理客户端直连工具服务器 ===
    if direct_tool_servers:
        for tool_server in direct_tool_servers:
            tool_specs = tool_server.pop("specs", [])

            for tool in tool_specs:
                tools_dict[tool["name"]] = {
                    "spec": tool,
                    "direct": True,
                    "server": tool_server,
                }

    # 保存 MCP 客户端到元数据（用于最后清理）
    if mcp_clients:
        metadata["mcp_clients"] = mcp_clients

    # === 17. 工具调用处理 [已屏蔽] ===
    if False:
        if tools_dict:
            if metadata.get("params", {}).get("function_calling") == "native":
                # 原生函数调用模式：直接传递给 LLM
                metadata["tools"] = tools_dict
                form_data["tools"] = [
                    {"type": "function", "function": tool.get("spec", {})}
                    for tool in tools_dict.values()
                ]
            else:
                # 默认模式：通过 Prompt 实现工具调用
                try:
                    form_data, flags = await chat_completion_tools_handler(
                        request, form_data, extra_params, user, models, tools_dict
                    )
                    sources.extend(flags.get("sources", []))
                except Exception as e:
                    log.exception(e)

    # === 18. 文件处理 - RAG 检索 [已屏蔽] ===
    if False:
        try:
            form_data, flags = await chat_completion_files_handler(
                request, form_data, extra_params, user
            )
            sources.extend(flags.get("sources", []))
        except Exception as e:
            log.exception(e)

        # === 19. 构建上下文字符串并注入到消息 [已屏蔽] ===
        # If context is not empty, insert it into the messages

        if len(sources) > 0:
            context_string = ""
            citation_idx_map = {}  # 引用索引映射（文档 ID → 引用编号）

            # 遍历所有来源，构建上下文字符串
            for source in sources:
                if "document" in source:
                    for document_text, document_metadata in zip(
                        source["document"], source["metadata"]
                    ):
                        source_name = source.get("source", {}).get("name", None)
                        source_id = (
                            document_metadata.get("source", None)
                            or source.get("source", {}).get("id", None)
                            or "N/A"
                        )

                        # 为每个来源分配唯一的引用编号
                        if source_id not in citation_idx_map:
                            citation_idx_map[source_id] = len(citation_idx_map) + 1

                        # 构建 XML 格式的来源标签
                        context_string += (
                            f'<source id="{citation_idx_map[source_id]}"'
                            + (f' name="{source_name}"' if source_name else "")
                            + f">{document_text}</source>\n"
                        )

            context_string = context_string.strip()
            if prompt is None:
                raise Exception("No user message found")

            # 使用 RAG 模板将上下文注入到用户消息中
            if context_string != "":
                form_data["messages"] = add_or_update_user_message(
                    rag_template(
                        request.app.state.config.RAG_TEMPLATE,
                        context_string,
                        prompt,
                    ),
                    form_data["messages"],
                    append=False,
                )

    # === 20. 整理引用来源并添加到事件 ===
    # If there are citations, add them to the data_items
    sources = [
        source
        for source in sources
        if source.get("source", {}).get("name", "")
        or source.get("source", {}).get("id", "")
    ]

    if len(sources) > 0:
        events.append({"sources": sources})

    # === 21. 完成知识库搜索状态 ===
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

    # print(form_data["messages"])
    return form_data, metadata, events


async def process_chat_response(
    request, response, form_data, user, metadata, model, events, tasks
):
    """
    处理聊天响应 - 规范化/分发聊天完成响应

    这是聊天响应后处理的核心函数，负责：
    1. 处理流式（SSE/ndjson）和非流式（JSON）响应
    2. 通过 WebSocket 发送事件到前端
    3. 持久化消息/错误/元数据到数据库
    4. 触发后台任务（标题生成、标签生成、Follow-ups）
    5. 流式响应时：消费上游数据块、重建内容、处理工具调用、转发增量

    Args:
        request: FastAPI Request 对象
        response: 上游响应（dict/JSONResponse/StreamingResponse）
        form_data: 原始请求 payload（可能被上游修改）
        user: 已验证的用户对象
        metadata: 早期收集的聊天/会话上下文
        model: 解析后的模型配置
        events: 需要发送的额外事件（如 sources 引用）
        tasks: 可选的后台任务（title/tags/follow-ups）

    Returns:
        - 非流式: dict (OpenAI JSON 格式)
        - 流式: StreamingResponse (SSE/ndjson 格式)
    """

    # 记录上游 usage 供后台任务判断摘要阈值
    usage_holder = {"usage": None}

    # ========================================
    # 内部函数：后台任务处理器
    # ========================================
    async def background_tasks_handler():
        """
        在响应完成后异步执行后台任务，增强用户体验

        执行的任务类型：
        1. Follow-ups 生成 - 使用 LLM 生成 3-5 个后续问题建议，引导用户继续对话
        2. Title 生成 - 基于对话内容自动生成聊天标题（首次对话时）
        3. Tags 生成 - 自动生成聊天分类标签（如"技术"、"工作"等）

        数据流转：
        - 输入：从数据库读取完整的消息历史（message_list）或从 form_data 获取临时消息
        - 处理：调用 LLM 生成任务结果（JSON 格式）
        - 输出：通过 WebSocket 实时推送给前端 + 持久化到数据库

        边界情况：
        - 临时聊天（chat_id 以 "local:" 开头）：不生成标题和标签，仅生成 Follow-ups
        - Follow-ups 可为临时聊天生成，但不持久化到数据库
        - 任务开关通过 tasks 字典控制（TASKS.TITLE_GENERATION 等）
        """
        message = None  # 当前 AI 回复消息（用于获取 model 字段）
        messages = []   # 完整的消息历史列表（用于 LLM 生成任务）

        # ----------------------------------------
        # 第1步：获取消息历史
        # ----------------------------------------
        # 数据流转：从数据库或 form_data 获取消息列表
        if "chat_id" in metadata and not metadata["chat_id"].startswith("local:"):
            # 从数据库获取持久化的聊天历史
            # 数据结构：messages_map = {"message-id": {"role": "user", "content": "...", ...}}
            messages_map = Chats.get_messages_map_by_chat_id(metadata["chat_id"])
            message = messages_map.get(metadata["message_id"]) if messages_map else None

            # 构建有序的消息链表（从 root 到当前 message_id）
            # get_message_list 遍历 parentId 链接，返回完整的对话历史
            message_list = get_message_list(messages_map, metadata["message_id"])

            # ----------------------------------------
            # 第2步：清理消息内容
            # ----------------------------------------
            # 业务逻辑：移除对 LLM 生成任务无用的内容，降低 token 消耗
            # - 移除 <details> 折叠区域（通常是技术细节/日志）
            # - 移除 Markdown 图片引用（![alt](url)）
            # get_message_list 创建新列表，不影响数据库中的原始消息
            messages = []
            for message in message_list:
                content = message.get("content", "")

                # 边界情况：处理多模态内容（OpenAI 格式：[{"type": "text", "text": "..."}, {"type": "image_url", ...}]）
                # 从多模态消息中提取纯文本部分
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            content = item["text"]
                            break

                # 正则清理：移除对生成任务无用的内容
                if isinstance(content, str):
                    content = re.sub(
                        r"<details\b[^>]*>.*?<\/details>|!\[.*?\]\(.*?\)",  # <details>...</details> 或 ![](url)
                        "",
                        content,
                        flags=re.S | re.I,  # re.S 使 . 匹配换行符，re.I 忽略大小写
                    ).strip()

                # 构建清理后的消息对象
                messages.append(
                    {
                        **message,  # 保留原始字段（id, timestamp, parentId 等）
                        "role": message.get("role", "assistant"),  # 边界情况：缺失 role 时安全回退
                        "content": content,  # 使用清理后的内容
                    }
                )
        else:
            # 边界情况：临时聊天（chat_id 以 "local:" 开头）
            # 数据流转：直接从请求 payload (form_data) 获取消息历史，无需查询数据库
            message = get_last_user_message_item(form_data.get("messages", []))
            messages = form_data.get("messages", [])
            if message:
                message["model"] = form_data.get("model")  # 补充 model 字段（用于后续任务）

        # ----------------------------------------
        # 第3步：执行后台任务
        # ----------------------------------------
        # 业务逻辑：仅当 message 有效且包含 model 字段时才执行
        # 边界情况：若 messages 为空或 tasks 未配置，则跳过所有任务
        if message and "model" in message:
            if tasks and messages:
                # ========================================
                # 任务 1: Follow-ups 生成 
                # [已屏蔽]
                # ========================================
                # 业务逻辑：根据对话历史，使用 LLM 生成 3-5 个后续问题建议
                # 目的：引导用户继续深入对话，提升用户体验
                if False:
                    if (
                        TASKS.FOLLOW_UP_GENERATION in tasks
                        and tasks[TASKS.FOLLOW_UP_GENERATION]
                    ):
                        # 调用 LLM 生成 Follow-ups
                        # 数据流转：messages → LLM → JSON 格式的 follow_ups 列表
                        res = await generate_follow_ups(
                            request,
                            {
                                "model": message["model"],  # 使用当前对话的模型
                                "messages": messages,        # 完整的清理后的消息历史
                                "message_id": metadata["message_id"],
                                "chat_id": metadata["chat_id"],
                            },
                            user,
                        )

                        # 边界情况：检查 LLM 响应是否有效
                        if res and isinstance(res, dict):
                            if len(res.get("choices", [])) == 1:
                                response_message = res.get("choices", [])[0].get(
                                    "message", {}
                                )

                                # 提取内容（优先 content，回退到 reasoning_content）
                                follow_ups_string = response_message.get(
                                    "content"
                                ) or response_message.get("reasoning_content", "")
                            else:
                                # 边界情况：LLM 返回多个 choices 或没有 choices
                                follow_ups_string = ""

                            # 数据清理：提取 JSON 对象（从第一个 { 到最后一个 }）
                            # 业务逻辑：LLM 可能在 JSON 前后添加说明文字，需要裁剪
                            follow_ups_string = follow_ups_string[
                                follow_ups_string.find("{") : follow_ups_string.rfind("}")
                                + 1
                            ]

                            try:
                                # 解析 JSON：{"follow_ups": ["问题1", "问题2", "问题3"]}
                                follow_ups = json.loads(follow_ups_string).get(
                                    "follow_ups", []
                                )

                                # 数据流转：通过 WebSocket 实时推送给前端
                                await event_emitter(
                                    {
                                        "type": "chat:message:follow_ups",
                                        "data": {
                                            "follow_ups": follow_ups,
                                        },
                                    }
                                )

                                # 数据流转：持久化到数据库（仅非临时聊天）
                                # 边界情况：临时聊天（local:）不持久化
                                if not metadata.get("chat_id", "").startswith("local:"):
                                    Chats.upsert_message_to_chat_by_id_and_message_id(
                                        metadata["chat_id"],
                                        metadata["message_id"],
                                        {
                                            "followUps": follow_ups,
                                        },
                                    )

                            except Exception as e:
                                # 边界情况：JSON 解析失败（LLM 返回格式错误）
                                # 静默失败，不影响主流程
                                pass

                # ========================================
                # 任务 2 & 3: 标题和标签生成（仅非临时聊天）
                # ========================================
                # 边界情况：临时聊天（local:）不需要标题和标签，跳过这两个任务
                if not metadata.get("chat_id", "").startswith("local:"):
                    # ========================================
                    # 任务 2: 标题生成
                    # ========================================
                    # 业务逻辑：自动生成聊天标题，提升用户体验（避免显示 "New Chat"）
                    # 触发时机：首次对话完成后
                    if (
                        TASKS.TITLE_GENERATION in tasks
                        and tasks[TASKS.TITLE_GENERATION]
                    ):
                        # 获取最后一条用户消息作为回退标题
                        user_message = get_last_user_message(messages)
                        if user_message and len(user_message) > 100:
                            # 边界情况：截断过长的消息（避免标题过长）
                            user_message = user_message[:100] + "..."

                        if tasks[TASKS.TITLE_GENERATION]:

                            # 调用 LLM 生成标题
                            # 数据流转：messages → LLM → JSON 格式的 title 字符串
                            res = await generate_title(
                                request,
                                {
                                    "model": message["model"],
                                    "messages": messages,
                                    "chat_id": metadata["chat_id"],
                                },
                                user,
                            )

                            # 边界情况：检查 LLM 响应是否有效
                            if res and isinstance(res, dict):
                                if len(res.get("choices", [])) == 1:
                                    response_message = res.get("choices", [])[0].get(
                                        "message", {}
                                    )

                                    # 提取内容（多层回退策略）
                                    # 优先级：content > reasoning_content > 当前 AI 回复 > 用户消息
                                    title_string = (
                                        response_message.get("content")
                                        or response_message.get(
                                            "reasoning_content",
                                        )
                                        or message.get("content", user_message)
                                    )
                                else:
                                    # 边界情况：LLM 返回多个 choices 或没有 choices
                                    title_string = ""

                                # 数据清理：提取 JSON 对象
                                title_string = title_string[
                                    title_string.find("{") : title_string.rfind("}") + 1
                                ]

                                try:
                                    # 解析 JSON：{"title": "生成的标题"}
                                    title = json.loads(title_string).get(
                                        "title", user_message
                                    )
                                except Exception as e:
                                    # 边界情况：JSON 解析失败
                                    title = ""

                                # 边界情况：标题为空时，使用首条用户消息作为回退
                                if not title:
                                    title = messages[0].get("content", user_message)

                                # 数据流转：更新数据库
                                Chats.update_chat_title_by_id(
                                    metadata["chat_id"], title
                                )

                                # 数据流转：通过 WebSocket 发送标题给前端
                                await event_emitter(
                                    {
                                        "type": "chat:title",
                                        "data": title,
                                    }
                                )
                        # 边界情况：简单对话（仅 2 条消息：1条 user + 1条 assistant）
                        # 业务逻辑：直接用用户消息作为标题，无需调用 LLM（节省成本）
                        elif len(messages) == 2:
                            title = messages[0].get("content", user_message)

                            Chats.update_chat_title_by_id(metadata["chat_id"], title)

                            await event_emitter(
                                {
                                    "type": "chat:title",
                                    "data": message.get("content", user_message),
                                }
                            )

                    # ========================================
                    # 任务 3: 标签生成
                    # ========================================
                    # 业务逻辑：使用 LLM 生成聊天分类标签（如"技术"、"工作"、"生活"等）
                    # 目的：方便用户对聊天进行分类管理和检索
                    if TASKS.TAGS_GENERATION in tasks and tasks[TASKS.TAGS_GENERATION]:
                        # 调用 LLM 生成标签
                        # 数据流转：messages → LLM → JSON 格式的 tags 数组
                        res = await generate_chat_tags(
                            request,
                            {
                                "model": message["model"],
                                "messages": messages,
                                "chat_id": metadata["chat_id"],
                            },
                            user,
                        )

                        # 边界情况：检查 LLM 响应是否有效
                        if res and isinstance(res, dict):
                            if len(res.get("choices", [])) == 1:
                                response_message = res.get("choices", [])[0].get(
                                    "message", {}
                                )

                                # 提取内容（优先 content，回退到 reasoning_content）
                                tags_string = response_message.get(
                                    "content"
                                ) or response_message.get("reasoning_content", "")
                            else:
                                # 边界情况：LLM 返回多个 choices 或没有 choices
                                tags_string = ""

                            # 数据清理：提取 JSON 对象
                            tags_string = tags_string[
                                tags_string.find("{") : tags_string.rfind("}") + 1
                            ]

                            try:
                                # 解析 JSON：{"tags": ["技术", "工作", "Python"]}
                                tags = json.loads(tags_string).get("tags", [])

                                # 数据流转：更新数据库（保存到 chat.meta.tags）
                                Chats.update_chat_tags_by_id(
                                    metadata["chat_id"], tags, user
                                )

                                # 数据流转：通过 WebSocket 发送标签给前端
                                await event_emitter(
                                    {
                                        "type": "chat:tags",
                                        "data": tags,
                                    }
                                )
                            except Exception as e:
                                # 边界情况：JSON 解析失败
                                # 静默失败，不影响主流程
                                pass

                # ========================================
                # 任务 4: 摘要更新（基于阈值）
                # ========================================
                try:
                    # 获取 chat_id
                    chat_id = metadata.get("chat_id")
                    if chat_id and not str(chat_id).startswith("local:"):
                        # 阈值来自配置或全局开关
                        threshold = getattr(
                            request.app.state.config,
                            "SUMMARY_TOKEN_THRESHOLD",
                            SUMMARY_TOKEN_THRESHOLD_DEFAULT,
                        )

                        # 优先使用上游 usage，再回退自算 token
                        tokens = None
                        if isinstance(usage_holder.get("usage"), dict):
                            usage = usage_holder["usage"]
                            tokens = usage.get("total_tokens") or usage.get(
                                "prompt_tokens"
                            )
                        if tokens is None:
                            tokens = compute_token_count(messages or [])

                        # 若超过阈值
                        if tokens >= threshold:
                            if CHAT_DEBUG_FLAG:
                                print(
                                    f"[summary:update] chat_id={chat_id} token数={tokens} 阈值={threshold}"
                                )

                            # 读取已有的 summary
                            existing_summary = Chats.get_summary_by_user_id_and_chat_id(
                                user.id, chat_id
                            )
                            old_summary = (
                                existing_summary.get("content")
                                if existing_summary
                                else None
                            )

                            # 取摘要边界前 20 条 + 之后所有消息
                            messages_map = Chats.get_messages_map_by_chat_id(chat_id) or {}
                            ordered = slice_messages_with_summary(
                                messages_map,
                                existing_summary.get("last_message_id") if existing_summary else None,
                                metadata.get("message_id"),
                                pre_boundary=20,
                            )

                            summary_messages = [
                                msg
                                for msg in ordered
                                if msg.get("role") in ("user", "assistant")
                            ]
                            if CHAT_DEBUG_FLAG:
                                print(
                                    f"[summary:update] chat_id={chat_id} 切片总数={len(ordered)} 摘要参与消息数={len(summary_messages)} "
                                    f"上次摘要 message_id={existing_summary.get('last_message_id') if existing_summary else None}"
                                )
                            
                            # 获取当前模型ID，确保使用正确的模型进行摘要更新
                            model_id = model.get("id") if model else None
                            summary_text = summarize(summary_messages, old_summary, model=model_id)
                            last_msg_id = (
                                summary_messages[-1].get("id")
                                if summary_messages
                                else metadata.get("message_id")
                            )
                            Chats.set_summary_by_user_id_and_chat_id(
                                user.id,
                                chat_id,
                                summary_text,
                                last_msg_id,
                                int(time.time()),
                                recent_message_ids=[],
                            )
                        else:
                            if CHAT_DEBUG_FLAG:
                                print(
                                    f"[summary:update] chat_id={chat_id} token数={tokens} 低于阈值={threshold}"
                                )
                except Exception as e:
                    log.debug(f"summary update skipped: {e}")

    # ========================================
    # 第一阶段：事件发射器初始化
    # ========================================
    # 业务逻辑：仅在异步模式（有 session_id）时初始化 WebSocket 事件发射器
    # 数据流转：通过 WebSocket 向前端推送实时事件（completion、error、title 等）
    # 边界情况：同步模式（无 session_id）时，event_emitter 和 event_caller 为 None
    event_emitter = None
    event_caller = None
    if (
        "session_id" in metadata
        and metadata["session_id"]
        and "chat_id" in metadata
        and metadata["chat_id"]
        and "message_id" in metadata
        and metadata["message_id"]
    ):
        # 获取 WebSocket 事件发射器（用于向前端推送事件）
        # event_emitter: async def (event: dict) -> None
        event_emitter = get_event_emitter(metadata)
        # 获取事件调用器（用于调用 MCP/工具等）
        # event_caller: async def (event: dict) -> Any
        event_caller = get_event_call(metadata)

    # ========================================
    # 第二阶段：非流式响应处理
    # ========================================
    # 业务逻辑：处理 LLM 返回的完整 JSON 响应（非 SSE 流）
    # 数据流转：response (dict/JSONResponse) → 解析 → WebSocket 推送 + 数据库持久化
    # 触发条件：response 不是 StreamingResponse 实例
    if not isinstance(response, StreamingResponse):
        # 边界情况：仅在异步模式（有 event_emitter）时才执行 WebSocket 推送和数据库写入
        if event_emitter:
            try:
                # ----------------------------------------
                # 步骤 1：响应类型检查和数据解析
                # ----------------------------------------
                # 边界情况：支持 dict 和 JSONResponse 两种响应类型
                if isinstance(response, dict) or isinstance(response, JSONResponse):
                    # 边界情况：处理单项列表（某些 LLM 可能返回 [response]）
                    # 数据流转：[response] → response
                    if isinstance(response, list) and len(response) == 1:
                        response = response[0]

                    # 边界情况：JSONResponse 需要从 body (bytes) 解析 JSON
                    # 数据流转：JSONResponse.body (bytes) → response_data (dict)
                    if isinstance(response, JSONResponse) and isinstance(
                        response.body, bytes
                    ):
                        try:
                            response_data = json.loads(
                                response.body.decode("utf-8", "replace")  # replace 处理无效 UTF-8 字符
                            )
                        except json.JSONDecodeError:
                            # 边界情况：JSON 解析失败，构造错误响应
                            response_data = {
                                "error": {"detail": "Invalid JSON response"}
                            }
                    else:
                        # dict 类型直接使用
                        response_data = response

                    # ----------------------------------------
                    # 步骤 2：错误响应处理
                    # ----------------------------------------
                    # 业务逻辑：LLM 返回错误（如 API 限流、模型不可用等）
                    # 数据流转：error → 数据库 + WebSocket 推送
                    if "error" in response_data:
                        error = response_data.get("error")

                        # 边界情况：统一错误格式（dict 或 str）
                        if isinstance(error, dict):
                            error = error.get("detail", error)  # 提取 detail 字段或保持原样
                        else:
                            error = str(error)

                        # 数据流转：保存错误到数据库（message.error 字段）
                        Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata["chat_id"],
                            metadata["message_id"],
                            {
                                "error": {"content": error},
                            },
                        )

                        # 数据流转：通过 WebSocket 实时推送错误事件给前端
                        if isinstance(error, str) or isinstance(error, dict):
                            await event_emitter(
                                {
                                    "type": "chat:message:error",
                                    "data": {"error": {"content": error}},
                                }
                            )

                    # ----------------------------------------
                    # 步骤 3：Arena 模式处理（盲测模型选择）
                    # ----------------------------------------
                    # 业务逻辑：Arena 模式下，LLM 随机选择模型，返回 selected_model_id
                    # 数据流转：selected_model_id → 数据库（message.selectedModelId 字段）
                    if "selected_model_id" in response_data:
                        Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata["chat_id"],
                            metadata["message_id"],
                            {
                                "selectedModelId": response_data["selected_model_id"],
                            },
                        )

                    # ----------------------------------------
                    # 步骤 4：成功响应处理
                    # ----------------------------------------
                    # 业务逻辑：LLM 正常返回完整响应
                    # 数据流转：content → WebSocket 推送 + 数据库 + Webhook 通知 + 后台任务
                    choices = response_data.get("choices", [])
                    if choices and choices[0].get("message", {}).get("content"):
                        content = response_data["choices"][0]["message"]["content"]

                        if content:
                            # 数据流转：第1次 WebSocket 推送 - 完整的 LLM 响应数据
                            await event_emitter(
                                {
                                    "type": "chat:completion",
                                    "data": response_data,  # 包含 choices、usage、model 等完整字段
                                }
                            )

                            # 获取聊天标题（用于 Webhook 通知和第2次推送）
                            title = Chats.get_chat_title_by_id(metadata["chat_id"])

                            # 数据流转：第2次 WebSocket 推送 - 标记完成并附带标题
                            # 业务逻辑：前端收到 done=True 后停止加载动画
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

                            # 数据流转：保存 AI 回复到数据库
                            # 字段：role="assistant", content（完整回复内容）
                            Chats.upsert_message_to_chat_by_id_and_message_id(
                                metadata["chat_id"],
                                metadata["message_id"],
                                {
                                    "role": "assistant",
                                    "content": content,
                                },
                            )

                            # ----------------------------------------
                            # 步骤 5：Webhook 通知（用户离线时）
                            # ----------------------------------------
                            # 业务逻辑：用户不在线时，通过 Webhook 发送通知（如 Slack、Discord、企业微信等）
                            # 边界情况：仅当用户配置了 webhook_url 且当前不在线时触发
                            if not get_active_status_by_user_id(user.id):
                                webhook_url = Users.get_user_webhook_url_by_id(user.id)
                                if webhook_url:
                                    await post_webhook(
                                        request.app.state.WEBUI_NAME,  # 应用名称（如 "Open WebUI"）
                                        webhook_url,  # 用户配置的 Webhook URL
                                        # 消息正文：标题 + 链接 + 内容
                                        f"{title} - {request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}\n\n{content}",
                                        # 结构化数据（供 Webhook 接收方解析）
                                        {
                                            "action": "chat",
                                            "message": content,
                                            "title": title,
                                            "url": f"{request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}",
                                        },
                                    )

                            # ----------------------------------------
                            # 步骤 6：执行后台任务
                            # ----------------------------------------
                            # 业务逻辑：异步生成 Follow-ups、标题、标签
                            await background_tasks_handler()

                    # ----------------------------------------
                    # 步骤 7：合并额外事件（如 RAG sources）
                    # ----------------------------------------
                    # 业务逻辑：process_chat_payload 可能注入额外事件（如 RAG 检索的 sources）
                    # 数据流转：events (list) → extra_response (dict) → 合并到 response_data
                    if events and isinstance(events, list):
                        extra_response = {}
                        for event in events:
                            if isinstance(event, dict):
                                # dict 事件：合并到 extra_response
                                extra_response.update(event)
                            else:
                                # 字符串事件：设置为 True（如 "web_search": True）
                                extra_response[event] = True

                        # 合并策略：extra_response 在前（优先级低），response_data 在后（优先级高）
                        response_data = {
                            **extra_response,
                            **response_data,
                        }

                    # ----------------------------------------
                    # 步骤 8：重新封装响应对象
                    # ----------------------------------------
                    # 业务逻辑：保持响应类型一致（dict 或 JSONResponse）
                    if isinstance(response, dict):
                        response = response_data
                    if isinstance(response, JSONResponse):
                        response = JSONResponse(
                            content=response_data,
                            headers=response.headers,
                            status_code=response.status_code,
                        )

            except Exception as e:
                # 边界情况：捕获所有异常，避免整个响应处理流程崩溃
                # 业务逻辑：记录日志但不中断（静默失败）
                log.debug(f"Error occurred while processing request: {e}")
                pass

            return response
        else:
            # ----------------------------------------
            # 同步模式：无 event_emitter（无 session_id）
            # ----------------------------------------
            # 业务逻辑：直接返回响应，不执行 WebSocket 推送和数据库写入
            # 边界情况：仅合并 events 到响应中
            if events and isinstance(events, list) and isinstance(response, dict):
                extra_response = {}
                for event in events:
                    if isinstance(event, dict):
                        extra_response.update(event)
                    else:
                        extra_response[event] = True

                # 合并 events 到响应
                response = {
                    **extra_response,
                    **response,
                }

            return response

    # ========================================
    # 第三阶段：流式响应前置检查
    # ========================================
    # 边界情况：非标准流式响应（既不是 SSE 也不是 ndjson）
    # 业务逻辑：直接返回原始响应，不进行流式处理
    if not any(
        content_type in response.headers["Content-Type"]
        for content_type in ["text/event-stream", "application/x-ndjson"]
    ):
        return response

    # ----------------------------------------
    # 步骤 1：OAuth Token 获取
    # ----------------------------------------
    # 业务逻辑：如果用户通过 OAuth 登录（如 Google、GitHub），获取 OAuth access token
    # 用途：传递给 Filter 函数和工具（可能需要调用外部 API）
    # 边界情况：OAuth 获取失败时，oauth_token 为 None（不影响主流程）
    oauth_token = None
    try:
        if request.cookies.get("oauth_session_id", None):
            oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                user.id,
                request.cookies.get("oauth_session_id", None),
            )
    except Exception as e:
        # 边界情况：OAuth 获取失败（如 session 过期），记录日志但不中断
        log.error(f"Error getting OAuth token: {e}")

    # ----------------------------------------
    # 步骤 2：准备额外参数（传递给 Filter 函数和工具）
    # ----------------------------------------
    # 业务逻辑：构造通用参数对象，供后续 Filter 函数和工具使用
    # 数据流转：extra_params → Filter 函数 → 工具调用
    extra_params = {
        "__event_emitter__": event_emitter,  # WebSocket 事件发射器
        "__event_call__": event_caller,       # 事件调用器（MCP/工具）
        "__user__": user.model_dump() if isinstance(user, UserModel) else {},  # 用户信息
        "__metadata__": metadata,             # 聊天上下文（chat_id、message_id 等）
        "__oauth_token__": oauth_token,       # OAuth access token（可能为 None）
        "__request__": request,               # FastAPI Request 对象
        "__model__": model,                   # 模型配置对象
    }

    # ----------------------------------------
    # 步骤 3：加载 Filter 函数
    # ----------------------------------------
    # 业务逻辑：Filter 函数可以拦截/修改流式响应的每个 delta
    # 数据流转：filter_ids → 从数据库加载 Filter 函数对象 → 按优先级排序
    # 用途：内容审核、敏感词过滤、格式转换等
    filter_functions = [
        Functions.get_function_by_id(filter_id)
        for filter_id in get_sorted_filter_ids(
            request, model, metadata.get("filter_ids", [])
        )
    ]

    # ========================================
    # 第四阶段：流式响应处理
    # ========================================
    # 业务逻辑：消费上游 SSE/ndjson 流，逐段处理并转发给前端
    # 触发条件：异步模式（有 event_emitter 和 event_caller）
    # 数据流转：上游 SSE 流 → 解析 delta → Filter 处理 → 累积 content → WebSocket 推送 → 数据库持久化
    if event_emitter and event_caller:
        # 生成唯一任务 ID（用于任务追踪和取消）
        task_id = str(uuid4())
        model_id = form_data.get("model", "")

        # ========================================
        # 辅助函数 1：split_content_and_whitespace
        # ========================================
        # 业务逻辑：分离内容和尾部空白符（用于流式推送优化）
        # 目的：避免在代码块未闭合时过早推送，造成显示异常
        # 数据流转：content → (content_stripped, original_whitespace)
        def split_content_and_whitespace(content):
            content_stripped = content.rstrip()
            original_whitespace = (
                content[len(content_stripped) :]
                if len(content) > len(content_stripped)
                else ""
            )
            return content_stripped, original_whitespace

        # ========================================
        # 辅助函数 2：is_opening_code_block
        # ========================================
        # 业务逻辑：检测内容是否以未闭合的代码块结尾
        # 原理：计算 ``` 的数量，偶数个 segment 表示最后一个 ``` 是开启新代码块
        # 边界情况：用于判断是否应该延迟推送（等待代码块闭合）
        def is_opening_code_block(content):
            backtick_segments = content.split("```")
            # 偶数个 segment 意味着最后一个 ``` 正在开启新的代码块
            return len(backtick_segments) > 1 and len(backtick_segments) % 2 == 0

        # ========================================
        # 响应处理器（后台任务）
        # ========================================
        # 业务逻辑：在后台异步处理流式响应，避免阻塞主线程
        # 数据流转：response (StreamingResponse) → 消费 SSE 流 → 解析 delta → 累积 content → WebSocket 推送 + 数据库
        async def response_handler(response, events):
            # ========================================
            # 辅助函数 3：serialize_content_blocks
            # ========================================
            # 业务逻辑：将内容块数组序列化为可读字符串（用于前端显示和数据库存储）
            # 数据流转：content_blocks (list) → content (string)
            # 参数：
            #   - content_blocks: 内容块数组 [{"type": "text", "content": "..."}, {"type": "tool_calls", ...}]
            #   - raw: 是否原始格式（True=保留标签，False=转换为 HTML details 折叠区域）
            def serialize_content_blocks(content_blocks, raw=False):
                content = ""

                for block in content_blocks:
                    # ----------------------------------------
                    # 类型 1：普通文本块
                    # ----------------------------------------
                    # 业务逻辑：直接拼接文本内容，每块后添加换行符
                    if block["type"] == "text":
                        block_content = block["content"].strip()
                        if block_content:
                            content = f"{content}{block_content}\n"

                    # ----------------------------------------
                    # 类型 2：工具调用块
                    # ----------------------------------------
                    # 业务逻辑：将工具调用及其结果渲染为 HTML details 折叠区域
                    # 数据流转：tool_calls + results → <details> HTML 标签
                    elif block["type"] == "tool_calls":
                        attributes = block.get("attributes", {})

                        tool_calls = block.get("content", [])  # 工具调用列表 [{"id": "call_1", "function": {"name": "web_search", "arguments": "{}"}}]
                        results = block.get("results", [])      # 工具执行结果列表 [{"tool_call_id": "call_1", "content": "..."}]

                        # 确保前面有换行符（格式美化）
                        if content and not content.endswith("\n"):
                            content += "\n"

                        # ========== 分支 1：工具已执行（有 results）==========
                        if results:

                            tool_calls_display_content = ""
                            # 遍历每个工具调用，匹配其结果
                            for tool_call in tool_calls:

                                tool_call_id = tool_call.get("id", "")
                                tool_name = tool_call.get("function", {}).get(
                                    "name", ""
                                )
                                tool_arguments = tool_call.get("function", {}).get(
                                    "arguments", ""
                                )

                                # 查找对应的工具结果
                                tool_result = None
                                tool_result_files = None
                                for result in results:
                                    if tool_call_id == result.get("tool_call_id", ""):
                                        tool_result = result.get("content", None)
                                        tool_result_files = result.get("files", None)
                                        break

                                # 渲染工具调用结果
                                if tool_result is not None:
                                    # 工具执行成功：done="true"
                                    tool_result_embeds = result.get("embeds", "")
                                    # HTML 转义：防止 XSS 攻击
                                    tool_calls_display_content = f'{tool_calls_display_content}<details type="tool_calls" done="true" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}" result="{html.escape(json.dumps(tool_result, ensure_ascii=False))}" files="{html.escape(json.dumps(tool_result_files)) if tool_result_files else ""}" embeds="{html.escape(json.dumps(tool_result_embeds))}">\n<summary>Tool Executed</summary>\n</details>\n'
                                else:
                                    # 工具执行中或失败：done="false"
                                    tool_calls_display_content = f'{tool_calls_display_content}<details type="tool_calls" done="false" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}">\n<summary>Executing...</summary>\n</details>\n'

                            # raw=False 时才拼接到 content（raw 模式跳过工具调用）
                            if not raw:
                                content = f"{content}{tool_calls_display_content}"

                        # ========== 分支 2：工具未执行（无 results）==========
                        else:
                            tool_calls_display_content = ""

                            # 渲染所有工具调用为"执行中"状态
                            for tool_call in tool_calls:
                                tool_call_id = tool_call.get("id", "")
                                tool_name = tool_call.get("function", {}).get(
                                    "name", ""
                                )
                                tool_arguments = tool_call.get("function", {}).get(
                                    "arguments", ""
                                )

                                tool_calls_display_content = f'{tool_calls_display_content}\n<details type="tool_calls" done="false" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}">\n<summary>Executing...</summary>\n</details>\n'

                            if not raw:
                                content = f"{content}{tool_calls_display_content}"

                    # ----------------------------------------
                    # 类型 3：推理内容块（Reasoning）
                    # ----------------------------------------
                    # 业务逻辑：渲染 LLM 的思考过程（如 o1 模型的 <think> 标签内容）
                    # 数据流转：推理内容 → Markdown 引用格式（> 前缀）→ <details> 折叠区域
                    elif block["type"] == "reasoning":
                        # 格式化推理内容：每行前添加 > 前缀（Markdown 引用格式）
                        reasoning_display_content = "\n".join(
                            (f"> {line}" if not line.startswith(">") else line)
                            for line in block["content"].splitlines()
                        )

                        reasoning_duration = block.get("duration", None)  # 推理耗时（秒）

                        start_tag = block.get("start_tag", "")  # 原始标签（如 <think>）
                        end_tag = block.get("end_tag", "")      # 原始结束标签（如 </think>）

                        # 确保前面有换行符
                        if content and not content.endswith("\n"):
                            content += "\n"

                        # 分支 1：推理完成（有 duration）
                        if reasoning_duration is not None:
                            if raw:
                                # raw 模式：保留原始标签
                                content = (
                                    f'{content}{start_tag}{block["content"]}{end_tag}\n'
                                )
                            else:
                                # 标准模式：渲染为折叠区域，显示推理耗时
                                content = f'{content}<details type="reasoning" done="true" duration="{reasoning_duration}">\n<summary>Thought for {reasoning_duration} seconds</summary>\n{reasoning_display_content}\n</details>\n'

                        # 分支 2：推理进行中（无 duration）
                        else:
                            if raw:
                                # raw 模式：保留原始标签
                                content = (
                                    f'{content}{start_tag}{block["content"]}{end_tag}\n'
                                )
                            else:
                                # 标准模式：渲染为"思考中"状态
                                content = f'{content}<details type="reasoning" done="false">\n<summary>Thinking…</summary>\n{reasoning_display_content}\n</details>\n'

                    # ----------------------------------------
                    # 类型 4：代码解释器块（Code Interpreter）
                    # ----------------------------------------
                    # 业务逻辑：渲染代码执行及其输出结果
                    # 数据流转：代码 + 输出 → Markdown 代码块 + <details> 折叠区域
                    elif block["type"] == "code_interpreter":
                        attributes = block.get("attributes", {})
                        output = block.get("output", None)  # 代码执行输出
                        lang = attributes.get("lang", "")   # 编程语言（如 python）

                        # 检测并处理未闭合的代码块
                        # 业务逻辑：避免在 LLM 正在生成代码块时过早插入代码解释器块
                        content_stripped, original_whitespace = (
                            split_content_and_whitespace(content)
                        )
                        if is_opening_code_block(content_stripped):
                            # 移除尾部的 ``` （正在开启新代码块）
                            # 边界情况：防止出现 ``` 连续符号导致渲染错误
                            content = (
                                content_stripped.rstrip("`").rstrip()
                                + original_whitespace
                            )
                        else:
                            # 保持内容不变（代码块已闭合或无代码块）
                            content = content_stripped + original_whitespace

                        # 确保前面有换行符
                        if content and not content.endswith("\n"):
                            content += "\n"

                        # 分支 1：代码已执行（有 output）
                        if output:
                            # HTML 转义：防止 XSS 攻击
                            output = html.escape(json.dumps(output))

                            if raw:
                                # raw 模式：使用自定义标签
                                content = f'{content}<code_interpreter type="code" lang="{lang}">\n{block["content"]}\n</code_interpreter>\n```output\n{output}\n```\n'
                            else:
                                # 标准模式：渲染为折叠区域，显示代码和输出
                                content = f'{content}<details type="code_interpreter" done="true" output="{output}">\n<summary>Analyzed</summary>\n```{lang}\n{block["content"]}\n```\n</details>\n'

                        # 分支 2：代码执行中（无 output）
                        else:
                            if raw:
                                # raw 模式：使用自定义标签
                                content = f'{content}<code_interpreter type="code" lang="{lang}">\n{block["content"]}\n</code_interpreter>\n'
                            else:
                                # 标准模式：渲染为"分析中"状态
                                content = f'{content}<details type="code_interpreter" done="false">\n<summary>Analyzing...</summary>\n```{lang}\n{block["content"]}\n```\n</details>\n'

                    # ----------------------------------------
                    # 类型 5：未知类型块（回退处理）
                    # ----------------------------------------
                    # 边界情况：处理自定义或未来新增的内容块类型
                    else:
                        block_content = str(block["content"]).strip()
                        if block_content:
                            content = f"{content}{block['type']}: {block_content}\n"

                # 返回序列化后的字符串（移除首尾空白符）
                return content.strip()

            # ========================================
            # 辅助函数 4：convert_content_blocks_to_messages
            # ========================================
            # 业务逻辑：将内容块数组转换为 OpenAI 格式的消息列表
            # 数据流转：content_blocks (list) → messages (list)
            # 用途：工具调用迭代时，需要将历史对话转换为 OpenAI messages 格式
            # 格式示例：
            #   输入：[{"type": "text", "content": "..."}, {"type": "tool_calls", "content": [...], "results": [...]}]
            #   输出：[{"role": "assistant", "content": "..."}, {"role": "tool", "tool_call_id": "...", "content": "..."}]
            def convert_content_blocks_to_messages(content_blocks, raw=False):
                messages = []

                # 临时累积非工具调用块
                temp_blocks = []
                for idx, block in enumerate(content_blocks):
                    # 遇到工具调用块：刷新临时块 + 添加工具调用消息 + 添加工具结果消息
                    if block["type"] == "tool_calls":
                        # 1. 将临时累积的块序列化为 assistant 消息
                        messages.append(
                            {
                                "role": "assistant",
                                "content": serialize_content_blocks(temp_blocks, raw),
                                "tool_calls": block.get("content"),  # 工具调用列表
                            }
                        )

                        # 2. 将每个工具结果转换为 tool 消息
                        results = block.get("results", [])
                        for result in results:
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": result["tool_call_id"],  # 关联到对应的工具调用
                                    "content": result.get("content", "") or "",
                                }
                            )

                        # 重置临时块（开始累积下一段内容）
                        temp_blocks = []
                    else:
                        # 非工具调用块：累积到临时块
                        temp_blocks.append(block)

                # 处理剩余的临时块（最后一段内容）
                if temp_blocks:
                    content = serialize_content_blocks(temp_blocks, raw)
                    if content:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": content,
                            }
                        )

                return messages

            # ========================================
            # 辅助函数 5：tag_content_handler
            # ========================================
            # 业务逻辑：检测并处理流式内容中的特殊标签（如 <think>、<solution>、<code>）
            # 数据流转：content (string) + content_blocks (list) → 检测标签 → 分割/创建新内容块
            # 参数：
            #   - content_type: 标签类型（"reasoning"、"solution"、"code_interpreter"）
            #   - tags: 标签对列表 [[start_tag, end_tag], ...]
            #   - content: 当前累积的内容字符串
            #   - content_blocks: 内容块数组（会被修改）
            # 返回：(content, content_blocks, end_flag)
            #   - end_flag: 是否检测到结束标签（True=该类型内容块已结束）
            def tag_content_handler(content_type, tags, content, content_blocks):
                end_flag = False

                def extract_attributes(tag_content):
                    """从标签中提取属性（如 <tag attr="value">）"""
                    attributes = {}
                    if not tag_content:  # Ensure tag_content is not None
                        return attributes
                    # Match attributes in the format: key="value" (ignores single quotes for simplicity)
                    matches = re.findall(r'(\w+)\s*=\s*"([^"]+)"', tag_content)
                    for key, value in matches:
                        attributes[key] = value
                    return attributes

                if content_blocks[-1]["type"] == "text":
                    for start_tag, end_tag in tags:

                        start_tag_pattern = rf"{re.escape(start_tag)}"
                        if start_tag.startswith("<") and start_tag.endswith(">"):
                            # Match start tag e.g., <tag> or <tag attr="value">
                            # remove both '<' and '>' from start_tag
                            # Match start tag with attributes
                            start_tag_pattern = (
                                rf"<{re.escape(start_tag[1:-1])}(\s.*?)?>"
                            )

                        match = re.search(start_tag_pattern, content)
                        if match:
                            try:
                                attr_content = (
                                    match.group(1) if match.group(1) else ""
                                )  # Ensure it's not None
                            except:
                                attr_content = ""

                            attributes = extract_attributes(
                                attr_content
                            )  # Extract attributes safely

                            # Capture everything before and after the matched tag
                            before_tag = content[
                                : match.start()
                            ]  # Content before opening tag
                            after_tag = content[
                                match.end() :
                            ]  # Content after opening tag

                            # Remove the start tag and after from the currently handling text block
                            content_blocks[-1]["content"] = content_blocks[-1][
                                "content"
                            ].replace(match.group(0) + after_tag, "")

                            if before_tag:
                                content_blocks[-1]["content"] = before_tag

                            if not content_blocks[-1]["content"]:
                                content_blocks.pop()

                            # Append the new block
                            content_blocks.append(
                                {
                                    "type": content_type,
                                    "start_tag": start_tag,
                                    "end_tag": end_tag,
                                    "attributes": attributes,
                                    "content": "",
                                    "started_at": time.time(),
                                }
                            )

                            if after_tag:
                                content_blocks[-1]["content"] = after_tag
                                tag_content_handler(
                                    content_type, tags, after_tag, content_blocks
                                )

                            break
                elif content_blocks[-1]["type"] == content_type:
                    start_tag = content_blocks[-1]["start_tag"]
                    end_tag = content_blocks[-1]["end_tag"]

                    if end_tag.startswith("<") and end_tag.endswith(">"):
                        # Match end tag e.g., </tag>
                        end_tag_pattern = rf"{re.escape(end_tag)}"
                    else:
                        # Handle cases where end_tag is just a tag name
                        end_tag_pattern = rf"{re.escape(end_tag)}"

                    # Check if the content has the end tag
                    if re.search(end_tag_pattern, content):
                        end_flag = True

                        block_content = content_blocks[-1]["content"]
                        # Strip start and end tags from the content
                        start_tag_pattern = rf"<{re.escape(start_tag)}(.*?)>"
                        block_content = re.sub(
                            start_tag_pattern, "", block_content
                        ).strip()

                        end_tag_regex = re.compile(end_tag_pattern, re.DOTALL)
                        split_content = end_tag_regex.split(block_content, maxsplit=1)

                        # Content inside the tag
                        block_content = (
                            split_content[0].strip() if split_content else ""
                        )

                        # Leftover content (everything after `</tag>`)
                        leftover_content = (
                            split_content[1].strip() if len(split_content) > 1 else ""
                        )

                        if block_content:
                            content_blocks[-1]["content"] = block_content
                            content_blocks[-1]["ended_at"] = time.time()
                            content_blocks[-1]["duration"] = int(
                                content_blocks[-1]["ended_at"]
                                - content_blocks[-1]["started_at"]
                            )

                            # Reset the content_blocks by appending a new text block
                            if content_type != "code_interpreter":
                                if leftover_content:

                                    content_blocks.append(
                                        {
                                            "type": "text",
                                            "content": leftover_content,
                                        }
                                    )
                                else:
                                    content_blocks.append(
                                        {
                                            "type": "text",
                                            "content": "",
                                        }
                                    )

                        else:
                            # Remove the block if content is empty
                            content_blocks.pop()

                            if leftover_content:
                                content_blocks.append(
                                    {
                                        "type": "text",
                                        "content": leftover_content,
                                    }
                                )
                            else:
                                content_blocks.append(
                                    {
                                        "type": "text",
                                        "content": "",
                                    }
                                )

                        # Clean processed content
                        start_tag_pattern = rf"{re.escape(start_tag)}"
                        if start_tag.startswith("<") and start_tag.endswith(">"):
                            # Match start tag e.g., <tag> or <tag attr="value">
                            # remove both '<' and '>' from start_tag
                            # Match start tag with attributes
                            start_tag_pattern = (
                                rf"<{re.escape(start_tag[1:-1])}(\s.*?)?>"
                            )

                        content = re.sub(
                            rf"{start_tag_pattern}(.|\n)*?{re.escape(end_tag)}",
                            "",
                            content,
                            flags=re.DOTALL,
                        )

                return content, content_blocks, end_flag

            message = Chats.get_message_by_id_and_message_id(
                metadata["chat_id"], metadata["message_id"]
            )

            tool_calls = []

            last_assistant_message = None
            try:
                if form_data["messages"][-1]["role"] == "assistant":
                    last_assistant_message = get_last_assistant_message(
                        form_data["messages"]
                    )
            except Exception as e:
                pass

            content = (
                message.get("content", "")
                if message
                else last_assistant_message if last_assistant_message else ""
            )

            content_blocks = [
                {
                    "type": "text",
                    "content": content,
                }
            ]

            reasoning_tags_param = metadata.get("params", {}).get("reasoning_tags")
            DETECT_REASONING_TAGS = reasoning_tags_param is not False
            DETECT_CODE_INTERPRETER = metadata.get("features", {}).get(
                "code_interpreter", False
            )

            reasoning_tags = []
            if DETECT_REASONING_TAGS:
                if (
                    isinstance(reasoning_tags_param, list)
                    and len(reasoning_tags_param) == 2
                ):
                    reasoning_tags = [
                        (reasoning_tags_param[0], reasoning_tags_param[1])
                    ]
                else:
                    reasoning_tags = DEFAULT_REASONING_TAGS

            try:
                for event in events:
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

                async def stream_body_handler(response, form_data):
                    """
                    流式响应体处理器 - 消费上游 SSE 流并处理内容块

                    核心功能：
                    1. 解析 SSE (Server-Sent Events) 流
                    2. 处理工具调用（tool_calls）增量更新
                    3. 处理推理内容（reasoning_content）- 如 <think> 标签
                    4. 处理解决方案（solution）和代码解释器（code_interpreter）标签
                    5. 实时保存消息到数据库（可选）
                    6. 控制流式推送频率（delta throttling）避免 WebSocket 过载

                    Args:
                        response: 上游 StreamingResponse 对象
                        form_data: 原始请求数据
                    """
                    nonlocal content  # 累积的完整文本内容
                    nonlocal content_blocks  # 内容块列表（text/reasoning/code_interpreter）

                    response_tool_calls = []  # 累积的工具调用列表

                    # === 1. 初始化流式推送控制 ===
                    delta_count = 0  # 当前累积的 delta 数量
                    delta_chunk_size = max(
                        CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE,  # 全局配置的块大小
                        int(
                            metadata.get("params", {}).get("stream_delta_chunk_size")
                            or 1
                        ),  # 用户配置的块大小
                    )
                    last_delta_data = None  # 待发送的最后一个 delta 数据

                    async def flush_pending_delta_data(threshold: int = 0):
                        """
                        刷新待发送的 delta 数据

                        Args:
                            threshold: 阈值，当 delta_count >= threshold 时才发送
                        """
                        nonlocal delta_count
                        nonlocal last_delta_data

                        if delta_count >= threshold and last_delta_data:
                            # 通过 WebSocket 发送累积的 delta
                            await event_emitter(
                                {
                                    "type": "chat:completion",
                                    "data": last_delta_data,
                                }
                            )
                            delta_count = 0
                            last_delta_data = None

                    # === 2. 消费 SSE 流 ===
                    async for line in response.body_iterator:
                        # 解码字节流为字符串
                        line = (
                            line.decode("utf-8", "replace")
                            if isinstance(line, bytes)
                            else line
                        )
                        data = line

                        # 跳过空行
                        if not data.strip():
                            continue

                        # SSE 格式：每个事件以 "data:" 开头
                        if not data.startswith("data:"):
                            continue

                        # 移除 "data:" 前缀
                        data = data[len("data:") :].strip()

                        try:
                            # 解析 JSON 数据
                            data = json.loads(data)

                            # === 3. 执行 Filter 函数（stream 类型）===
                            data, _ = await process_filter_functions(
                                request=request,
                                filter_functions=filter_functions,
                                filter_type="stream",
                                form_data=data,
                                extra_params={"__body__": form_data, **extra_params},
                            )

                            if data:
                                # 处理自定义事件
                                if "event" in data:
                                    await event_emitter(data.get("event", {}))

                                # === 4. 处理 Arena 模式的模型选择 ===
                                if "selected_model_id" in data:
                                    model_id = data["selected_model_id"]
                                    # 保存选中的模型 ID 到数据库
                                    Chats.upsert_message_to_chat_by_id_and_message_id(
                                        metadata["chat_id"],
                                        metadata["message_id"],
                                        {
                                            "selectedModelId": model_id,
                                        },
                                    )
                                    await event_emitter(
                                        {
                                            "type": "chat:completion",
                                            "data": data,
                                        }
                                    )
                                else:
                                    choices = data.get("choices", [])

                                    # === 5. 处理 usage 和 timings 信息 ===
                                    usage = data.get("usage", {}) or {}
                                    usage.update(data.get("timings", {}))  # llama.cpp timings
                                    if usage:
                                        usage_holder["usage"] = usage
                                        await event_emitter(
                                            {
                                                "type": "chat:completion",
                                                "data": {
                                                    "usage": usage,
                                                },
                                            }
                                        )

                                    # === 6. 处理错误响应 ===
                                    if not choices:
                                        error = data.get("error", {})
                                        if error:
                                            await event_emitter(
                                                {
                                                    "type": "chat:completion",
                                                    "data": {
                                                        "error": error,
                                                    },
                                                }
                                            )
                                        continue

                                    # === 7. 提取 delta（增量内容）===
                                    delta = choices[0].get("delta", {})
                                    delta_tool_calls = delta.get("tool_calls", None)

                                    # === 8. 处理工具调用（Tool Calls）===
                                    if delta_tool_calls:
                                        for delta_tool_call in delta_tool_calls:
                                            tool_call_index = delta_tool_call.get(
                                                "index"
                                            )

                                            if tool_call_index is not None:
                                                # 查找已存在的工具调用
                                                current_response_tool_call = None
                                                for (
                                                    response_tool_call
                                                ) in response_tool_calls:
                                                    if (
                                                        response_tool_call.get("index")
                                                        == tool_call_index
                                                    ):
                                                        current_response_tool_call = (
                                                            response_tool_call
                                                        )
                                                        break

                                                if current_response_tool_call is None:
                                                    # 添加新的工具调用
                                                    delta_tool_call.setdefault(
                                                        "function", {}
                                                    )
                                                    delta_tool_call[
                                                        "function"
                                                    ].setdefault("name", "")
                                                    delta_tool_call[
                                                        "function"
                                                    ].setdefault("arguments", "")
                                                    response_tool_calls.append(
                                                        delta_tool_call
                                                    )
                                                else:
                                                    # 更新已存在的工具调用（累积 name 和 arguments）
                                                    delta_name = delta_tool_call.get(
                                                        "function", {}
                                                    ).get("name")
                                                    delta_arguments = (
                                                        delta_tool_call.get(
                                                            "function", {}
                                                        ).get("arguments")
                                                    )

                                                    if delta_name:
                                                        current_response_tool_call[
                                                            "function"
                                                        ]["name"] += delta_name

                                                    if delta_arguments:
                                                        current_response_tool_call[
                                                            "function"
                                                        ][
                                                            "arguments"
                                                        ] += delta_arguments

                                    # === 9. 处理文本内容 ===
                                    value = delta.get("content")

                                    # === 10. 处理推理内容（Reasoning Content）===
                                    reasoning_content = (
                                        delta.get("reasoning_content")
                                        or delta.get("reasoning")
                                        or delta.get("thinking")
                                    )
                                    if reasoning_content:
                                        # 创建或更新 reasoning 内容块
                                        if (
                                            not content_blocks
                                            or content_blocks[-1]["type"] != "reasoning"
                                        ):
                                            reasoning_block = {
                                                "type": "reasoning",
                                                "start_tag": "<think>",
                                                "end_tag": "</think>",
                                                "attributes": {
                                                    "type": "reasoning_content"
                                                },
                                                "content": "",
                                                "started_at": time.time(),
                                            }
                                            content_blocks.append(reasoning_block)
                                        else:
                                            reasoning_block = content_blocks[-1]

                                        # 累积推理内容
                                        reasoning_block["content"] += reasoning_content

                                        data = {
                                            "content": serialize_content_blocks(
                                                content_blocks
                                            )
                                        }

                                    # === 11. 处理普通文本内容 ===
                                    if value:
                                        # 如果上一个块是 reasoning，标记结束并创建新的文本块
                                        if (
                                            content_blocks
                                            and content_blocks[-1]["type"]
                                            == "reasoning"
                                            and content_blocks[-1]
                                            .get("attributes", {})
                                            .get("type")
                                            == "reasoning_content"
                                        ):
                                            reasoning_block = content_blocks[-1]
                                            reasoning_block["ended_at"] = time.time()
                                            reasoning_block["duration"] = int(
                                                reasoning_block["ended_at"]
                                                - reasoning_block["started_at"]
                                            )

                                            content_blocks.append(
                                                {
                                                    "type": "text",
                                                    "content": "",
                                                }
                                            )

                                        # 累积文本内容
                                        content = f"{content}{value}"
                                        if not content_blocks:
                                            content_blocks.append(
                                                {
                                                    "type": "text",
                                                    "content": "",
                                                }
                                            )

                                        content_blocks[-1]["content"] = (
                                            content_blocks[-1]["content"] + value
                                        )

                                        # === 12. 检测并处理特殊标签 ===
                                        # 12.1 Reasoning 标签检测（如 <think>）
                                        if DETECT_REASONING_TAGS:
                                            content, content_blocks, _ = (
                                                tag_content_handler(
                                                    "reasoning",
                                                    reasoning_tags,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                            # Solution 标签检测
                                            content, content_blocks, _ = (
                                                tag_content_handler(
                                                    "solution",
                                                    DEFAULT_SOLUTION_TAGS,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                        # 12.2 Code Interpreter 标签检测
                                        if DETECT_CODE_INTERPRETER:
                                            content, content_blocks, end = (
                                                tag_content_handler(
                                                    "code_interpreter",
                                                    DEFAULT_CODE_INTERPRETER_TAGS,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                            # 如果检测到结束标签，停止流式处理
                                            if end:
                                                break

                                        # === 13. 实时保存消息（可选）===
                                        if ENABLE_REALTIME_CHAT_SAVE:
                                            # 保存到数据库
                                            Chats.upsert_message_to_chat_by_id_and_message_id(
                                                metadata["chat_id"],
                                                metadata["message_id"],
                                                {
                                                    "content": serialize_content_blocks(
                                                        content_blocks
                                                    ),
                                                },
                                            )
                                        else:
                                            # 准备待发送的数据
                                            data = {
                                                "content": serialize_content_blocks(
                                                    content_blocks
                                                ),
                                            }

                                # === 14. 流式推送控制 ===
                                if delta:
                                    delta_count += 1
                                    last_delta_data = data
                                    # 达到阈值时刷新
                                    if delta_count >= delta_chunk_size:
                                        await flush_pending_delta_data(delta_chunk_size)
                                else:
                                    # 非 delta 数据立即发送
                                    await event_emitter(
                                        {
                                            "type": "chat:completion",
                                            "data": data,
                                        }
                                    )
                        except Exception as e:
                            # 处理流结束标记
                            done = "data: [DONE]" in line
                            if done:
                                pass
                            else:
                                log.debug(f"Error: {e}")
                                continue

                    # === 15. 刷新剩余的 delta 数据 ===
                    await flush_pending_delta_data()

                    # === 16. 清理内容块 ===
                    if content_blocks:
                        # 清理最后一个文本块（移除尾部空白）
                        if content_blocks[-1]["type"] == "text":
                            content_blocks[-1]["content"] = content_blocks[-1][
                                "content"
                            ].strip()

                            # 如果为空则移除
                            if not content_blocks[-1]["content"]:
                                content_blocks.pop()

                                # 确保至少有一个空文本块
                                if not content_blocks:
                                    content_blocks.append(
                                        {
                                            "type": "text",
                                            "content": "",
                                        }
                                    )

                        # 标记最后一个 reasoning 块结束
                        if content_blocks[-1]["type"] == "reasoning":
                            reasoning_block = content_blocks[-1]
                            if reasoning_block.get("ended_at") is None:
                                reasoning_block["ended_at"] = time.time()
                                reasoning_block["duration"] = int(
                                    reasoning_block["ended_at"]
                                    - reasoning_block["started_at"]
                                )

                    # === 17. 保存工具调用 ===
                    if response_tool_calls:
                        tool_calls.append(response_tool_calls)

                    # === 18. 执行响应清理（关闭连接）===
                    if response.background:
                        await response.background()

                await stream_body_handler(response, form_data)

                tool_call_retries = 0

                while (
                    len(tool_calls) > 0
                    and tool_call_retries < CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES
                ):

                    tool_call_retries += 1

                    response_tool_calls = tool_calls.pop(0)

                    content_blocks.append(
                        {
                            "type": "tool_calls",
                            "content": response_tool_calls,
                        }
                    )

                    await event_emitter(
                        {
                            "type": "chat:completion",
                            "data": {
                                "content": serialize_content_blocks(content_blocks),
                            },
                        }
                    )

                    tools = metadata.get("tools", {})

                    results = []

                    for tool_call in response_tool_calls:
                        tool_call_id = tool_call.get("id", "")
                        tool_function_name = tool_call.get("function", {}).get(
                            "name", ""
                        )
                        tool_args = tool_call.get("function", {}).get("arguments", "{}")

                        tool_function_params = {}
                        try:
                            # json.loads cannot be used because some models do not produce valid JSON
                            tool_function_params = ast.literal_eval(tool_args)
                        except Exception as e:
                            log.debug(e)
                            # Fallback to JSON parsing
                            try:
                                tool_function_params = json.loads(tool_args)
                            except Exception as e:
                                log.error(
                                    f"Error parsing tool call arguments: {tool_args}"
                                )

                        # Mutate the original tool call response params as they are passed back to the passed
                        # back to the LLM via the content blocks. If they are in a json block and are invalid json,
                        # this can cause downstream LLM integrations to fail (e.g. bedrock gateway) where response
                        # params are not valid json.
                        # Main case so far is no args = "" = invalid json.
                        log.debug(
                            f"Parsed args from {tool_args} to {tool_function_params}"
                        )
                        tool_call.setdefault("function", {})["arguments"] = json.dumps(
                            tool_function_params
                        )

                        tool_result = None
                        tool = None
                        tool_type = None
                        direct_tool = False

                        if tool_function_name in tools:
                            tool = tools[tool_function_name]
                            spec = tool.get("spec", {})

                            tool_type = tool.get("type", "")
                            direct_tool = tool.get("direct", False)

                            try:
                                allowed_params = (
                                    spec.get("parameters", {})
                                    .get("properties", {})
                                    .keys()
                                )

                                tool_function_params = {
                                    k: v
                                    for k, v in tool_function_params.items()
                                    if k in allowed_params
                                }

                                if direct_tool:
                                    tool_result = await event_caller(
                                        {
                                            "type": "execute:tool",
                                            "data": {
                                                "id": str(uuid4()),
                                                "name": tool_function_name,
                                                "params": tool_function_params,
                                                "server": tool.get("server", {}),
                                                "session_id": metadata.get(
                                                    "session_id", None
                                                ),
                                            },
                                        }
                                    )

                                else:
                                    tool_function = tool["callable"]
                                    tool_result = await tool_function(
                                        **tool_function_params
                                    )

                            except Exception as e:
                                tool_result = str(e)

                        tool_result, tool_result_files, tool_result_embeds = (
                            process_tool_result(
                                request,
                                tool_function_name,
                                tool_result,
                                tool_type,
                                direct_tool,
                                metadata,
                                user,
                            )
                        )

                        results.append(
                            {
                                "tool_call_id": tool_call_id,
                                "content": tool_result or "",
                                **(
                                    {"files": tool_result_files}
                                    if tool_result_files
                                    else {}
                                ),
                                **(
                                    {"embeds": tool_result_embeds}
                                    if tool_result_embeds
                                    else {}
                                ),
                            }
                        )

                    content_blocks[-1]["results"] = results
                    content_blocks.append(
                        {
                            "type": "text",
                            "content": "",
                        }
                    )

                    await event_emitter(
                        {
                            "type": "chat:completion",
                            "data": {
                                "content": serialize_content_blocks(content_blocks),
                            },
                        }
                    )

                    try:
                        new_form_data = {
                            **form_data,
                            "model": model_id,
                            "stream": True,
                            "messages": [
                                *form_data["messages"],
                                *convert_content_blocks_to_messages(
                                    content_blocks, True
                                ),
                            ],
                        }

                        res = await generate_chat_completion(
                            request,
                            new_form_data,
                            user,
                        )

                        if isinstance(res, StreamingResponse):
                            await stream_body_handler(res, new_form_data)
                        else:
                            break
                    except Exception as e:
                        log.debug(e)
                        break

                if DETECT_CODE_INTERPRETER:
                    MAX_RETRIES = 5
                    retries = 0

                    while (
                        content_blocks[-1]["type"] == "code_interpreter"
                        and retries < MAX_RETRIES
                    ):

                        await event_emitter(
                            {
                                "type": "chat:completion",
                                "data": {
                                    "content": serialize_content_blocks(content_blocks),
                                },
                            }
                        )

                        retries += 1
                        log.debug(f"Attempt count: {retries}")

                        output = ""
                        try:
                            if content_blocks[-1]["attributes"].get("type") == "code":
                                code = content_blocks[-1]["content"]
                                if CODE_INTERPRETER_BLOCKED_MODULES:
                                    blocking_code = textwrap.dedent(
                                        f"""
                                        import builtins

                                        BLOCKED_MODULES = {CODE_INTERPRETER_BLOCKED_MODULES}

                                        _real_import = builtins.__import__
                                        def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
                                            if name.split('.')[0] in BLOCKED_MODULES:
                                                importer_name = globals.get('__name__') if globals else None
                                                if importer_name == '__main__':
                                                    raise ImportError(
                                                        f"Direct import of module {{name}} is restricted."
                                                    )
                                            return _real_import(name, globals, locals, fromlist, level)

                                        builtins.__import__ = restricted_import
                                    """
                                    )
                                    code = blocking_code + "\n" + code

                                if (
                                    request.app.state.config.CODE_INTERPRETER_ENGINE
                                    == "pyodide"
                                ):
                                    output = await event_caller(
                                        {
                                            "type": "execute:python",
                                            "data": {
                                                "id": str(uuid4()),
                                                "code": code,
                                                "session_id": metadata.get(
                                                    "session_id", None
                                                ),
                                            },
                                        }
                                    )
                                elif (
                                    request.app.state.config.CODE_INTERPRETER_ENGINE
                                    == "jupyter"
                                ):
                                    output = await execute_code_jupyter(
                                        request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
                                        code,
                                        (
                                            request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
                                            if request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH
                                            == "token"
                                            else None
                                        ),
                                        (
                                            request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
                                            if request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH
                                            == "password"
                                            else None
                                        ),
                                        request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
                                    )
                                else:
                                    output = {
                                        "stdout": "Code interpreter engine not configured."
                                    }

                                log.debug(f"Code interpreter output: {output}")

                                if isinstance(output, dict):
                                    stdout = output.get("stdout", "")

                                    if isinstance(stdout, str):
                                        stdoutLines = stdout.split("\n")
                                        for idx, line in enumerate(stdoutLines):

                                            if "data:image/png;base64" in line:
                                                image_url = get_image_url_from_base64(
                                                    request,
                                                    line,
                                                    metadata,
                                                    user,
                                                )
                                                if image_url:
                                                    stdoutLines[idx] = (
                                                        f"![Output Image]({image_url})"
                                                    )

                                        output["stdout"] = "\n".join(stdoutLines)

                                    result = output.get("result", "")

                                    if isinstance(result, str):
                                        resultLines = result.split("\n")
                                        for idx, line in enumerate(resultLines):
                                            if "data:image/png;base64" in line:
                                                image_url = get_image_url_from_base64(
                                                    request,
                                                    line,
                                                    metadata,
                                                    user,
                                                )
                                                resultLines[idx] = (
                                                    f"![Output Image]({image_url})"
                                                )
                                        output["result"] = "\n".join(resultLines)
                        except Exception as e:
                            output = str(e)

                        content_blocks[-1]["output"] = output

                        content_blocks.append(
                            {
                                "type": "text",
                                "content": "",
                            }
                        )

                        await event_emitter(
                            {
                                "type": "chat:completion",
                                "data": {
                                    "content": serialize_content_blocks(content_blocks),
                                },
                            }
                        )

                        try:
                            new_form_data = {
                                **form_data,
                                "model": model_id,
                                "stream": True,
                                "messages": [
                                    *form_data["messages"],
                                    {
                                        "role": "assistant",
                                        "content": serialize_content_blocks(
                                            content_blocks, raw=True
                                        ),
                                    },
                                ],
                            }

                            res = await generate_chat_completion(
                                request,
                                new_form_data,
                                user,
                            )

                            if isinstance(res, StreamingResponse):
                                await stream_body_handler(res, new_form_data)
                            else:
                                break
                        except Exception as e:
                            log.debug(e)
                            break

                title = Chats.get_chat_title_by_id(metadata["chat_id"])
                data = {
                    "done": True,
                    "content": serialize_content_blocks(content_blocks),
                    "title": title,
                }

                if not ENABLE_REALTIME_CHAT_SAVE:
                    # Save message in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            "content": serialize_content_blocks(content_blocks),
                        },
                    )

                # Send a webhook notification if the user is not active
                if not get_active_status_by_user_id(user.id):
                    webhook_url = Users.get_user_webhook_url_by_id(user.id)
                    if webhook_url:
                        await post_webhook(
                            request.app.state.WEBUI_NAME,
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

                await background_tasks_handler()
            except asyncio.CancelledError:
                log.warning("Task was cancelled!")
                await event_emitter({"type": "chat:tasks:cancel"})

                if not ENABLE_REALTIME_CHAT_SAVE:
                    # Save message in the database
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            "content": serialize_content_blocks(content_blocks),
                        },
                    )

            if response.background is not None:
                await response.background()

        return await response_handler(response, events)

    else:
        # Fallback to the original response
        async def stream_wrapper(original_generator, events):
            def wrap_item(item):
                return f"data: {item}\n\n"

            for event in events:
                event, _ = await process_filter_functions(
                    request=request,
                    filter_functions=filter_functions,
                    filter_type="stream",
                    form_data=event,
                    extra_params=extra_params,
                )

                if event:
                    yield wrap_item(json.dumps(event))

            async for data in original_generator:
                data, _ = await process_filter_functions(
                    request=request,
                    filter_functions=filter_functions,
                    filter_type="stream",
                    form_data=data,
                    extra_params=extra_params,
                )

                if data:
                    yield data

        return StreamingResponse(
            stream_wrapper(response.body_iterator, events),
            headers=dict(response.headers),
            background=response.background,
        )

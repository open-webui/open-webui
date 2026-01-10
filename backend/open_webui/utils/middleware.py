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


from open_webui.utils.misc import is_string_allowed
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.chats import Chats
from open_webui.models.folders import Folders
from open_webui.models.users import Users
from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
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
from open_webui.utils.tools import get_builtin_tools
from open_webui.routers.images import (
    image_generations,
    CreateImageForm,
    image_edits,
    EditImageForm,
)
from open_webui.routers.pipelines import (
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)
from open_webui.routers.memories import query_memory, QueryMemoryForm

from open_webui.utils.webhook import post_webhook
from open_webui.utils.files import (
    convert_markdown_base64_images,
    get_file_url_from_base64,
    get_image_base64_from_url,
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
)
from open_webui.utils.tools import (
    get_tools,
    get_updated_tool_function,
    has_tool_server_access,
)
from open_webui.utils.plugin import load_function_module_by_id
from open_webui.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)
from open_webui.utils.code_interpreter import execute_code_jupyter
from open_webui.utils.payload import apply_system_prompt_to_body
from open_webui.utils.mcp.client import MCPClient


from open_webui.config import (
    CACHE_DIR,
    DEFAULT_VOICE_MODE_PROMPT_TEMPLATE,
    DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    DEFAULT_CODE_INTERPRETER_PROMPT,
    CODE_INTERPRETER_BLOCKED_MODULES,
)
from open_webui.env import (
    GLOBAL_LOG_LEVEL,
    ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION,
    CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE,
    CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES,
    BYPASS_MODEL_ACCESS_CONTROL,
    ENABLE_REALTIME_CHAT_SAVE,
    ENABLE_QUERIES_CACHE,
    RAG_SYSTEM_CONTEXT,
)
from open_webui.constants import TASKS


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


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


def get_citation_source_from_tool_result(
    tool_name: str, tool_params: dict, tool_result: str, tool_id: str = ""
) -> list[dict]:
    """
    Parse a tool's result and convert it to source dicts for citation display.

    Follows the source format conventions from get_sources_from_items:
    - source: file/item info object with id, name, type
    - document: list of document contents
    - metadata: list of metadata objects with source, file_id, name fields

    Returns a list of sources (usually one, but query_knowledge_files may return multiple).
    """
    try:
        if tool_name == "search_web":
            # Parse JSON array: [{"title": "...", "link": "...", "snippet": "..."}]
            results = json.loads(tool_result)
            documents = []
            metadata = []

            for result in results:
                title = result.get("title", "")
                link = result.get("link", "")
                snippet = result.get("snippet", "")

                documents.append(f"{title}\n{snippet}")
                metadata.append(
                    {
                        "source": link,
                        "name": title,
                        "url": link,
                    }
                )

            return [
                {
                    "source": {"name": "search_web", "id": "search_web"},
                    "document": documents,
                    "metadata": metadata,
                }
            ]

        elif tool_name == "view_knowledge_file":
            file_data = json.loads(tool_result)
            filename = file_data.get("filename", "Unknown File")
            file_id = file_data.get("id", "")
            knowledge_name = file_data.get("knowledge_name", "")

            return [
                {
                    "source": {
                        "id": file_id,
                        "name": filename,
                        "type": "file",
                    },
                    "document": [file_data.get("content", "")],
                    "metadata": [
                        {
                            "file_id": file_id,
                            "name": filename,
                            "source": filename,
                            **(
                                {"knowledge_name": knowledge_name}
                                if knowledge_name
                                else {}
                            ),
                        }
                    ],
                }
            ]

        elif tool_name == "query_knowledge_files":
            chunks = json.loads(tool_result)

            # Group chunks by source for better citation display
            # Each unique source becomes a separate source entry
            sources_by_file = {}

            for chunk in chunks:
                source_name = chunk.get("source", "Unknown")
                file_id = chunk.get("file_id", "")
                note_id = chunk.get("note_id", "")
                chunk_type = chunk.get("type", "file")
                content = chunk.get("content", "")

                # Use file_id or note_id as the key
                key = file_id or note_id or source_name

                if key not in sources_by_file:
                    sources_by_file[key] = {
                        "source": {
                            "id": file_id or note_id,
                            "name": source_name,
                            "type": chunk_type,
                        },
                        "document": [],
                        "metadata": [],
                    }

                sources_by_file[key]["document"].append(content)
                sources_by_file[key]["metadata"].append(
                    {
                        "file_id": file_id,
                        "name": source_name,
                        "source": source_name,
                        **({"note_id": note_id} if note_id else {}),
                    }
                )

            # Return all grouped sources as a list
            if sources_by_file:
                return list(sources_by_file.values())

            # Empty result fallback
            return []

        else:
            # Fallback for other tools
            return [
                {
                    "source": {
                        "name": tool_name,
                        "type": "tool",
                        "id": tool_id or tool_name,
                    },
                    "document": [str(tool_result)],
                    "metadata": [{"source": tool_name, "name": tool_name}],
                }
            ]
    except Exception as e:
        log.exception(f"Error parsing tool result for {tool_name}: {e}")
        return [
            {
                "source": {"name": tool_name, "type": "tool"},
                "document": [str(tool_result)],
                "metadata": [{"source": tool_name}],
            }
        ]


def apply_source_context_to_messages(
    request: Request,
    messages: list,
    sources: list,
    user_message: str,
) -> list:
    """
    Build source context from citation sources and apply to messages.
    Uses RAG template to format context for model consumption.
    """
    if not sources or not user_message:
        return messages

    context_string = ""
    citation_idx = {}

    for source in sources:
        for doc, meta in zip(source.get("document", []), source.get("metadata", [])):
            src_id = meta.get("source") or source.get("source", {}).get("id") or "N/A"
            if src_id not in citation_idx:
                citation_idx[src_id] = len(citation_idx) + 1
            src_name = source.get("source", {}).get("name")
            context_string += (
                f'<source id="{citation_idx[src_id]}"'
                + (f' name="{src_name}"' if src_name else "")
                + f">{doc}</source>\n"
            )

    context_string = context_string.strip()
    if not context_string:
        return messages

    if RAG_SYSTEM_CONTEXT:
        return add_or_update_system_message(
            rag_template(
                request.app.state.config.RAG_TEMPLATE, context_string, user_message
            ),
            messages,
            append=True,
        )
    else:
        return add_or_update_user_message(
            rag_template(
                request.app.state.config.RAG_TEMPLATE, context_string, user_message
            ),
            messages,
            append=False,
        )


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

        if user_message and messages and messages[-1]["role"] == "user":
            # Remove the last user message to avoid duplication
            messages = messages[:-1]

        recent_messages = messages[-4:] if len(messages) > 4 else messages
        chat_history = "\n".join(
            f"{message['role'].upper()}: \"\"\"{get_content_from_message(message)}\"\"\""
            for message in recent_messages
        )

        prompt = (
            f"History:\n{chat_history}\nQuery: {user_message}"
            if chat_history
            else f"Query: {user_message}"
        )

        return {
            "model": task_model_id,
            "messages": [
                {"role": "system", "content": content},
                {"role": "user", "content": prompt},
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
    tools_specs = json.dumps(specs, ensure_ascii=False)

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
    request: Request, form_data: dict, extra_params: dict, user
):
    try:
        results = await query_memory(
            request,
            QueryMemoryForm(
                **{
                    "content": get_last_user_message(form_data["messages"]) or "",
                    "k": 3,
                }
            ),
            user,
        )
    except Exception as e:
        log.debug(e)
        results = None

    user_context = ""
    if results and hasattr(results, "documents"):
        if results.documents and len(results.documents) > 0:
            for doc_idx, doc in enumerate(results.documents[0]):
                created_at_date = "Unknown Date"

                if results.metadatas[0][doc_idx].get("created_at"):
                    created_at_timestamp = results.metadatas[0][doc_idx]["created_at"]
                    created_at_date = time.strftime(
                        "%Y-%m-%d", time.localtime(created_at_timestamp)
                    )

                user_context += f"{doc_idx + 1}. [{created_at_date}] {doc}\n"

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


def get_images_from_messages(message_list):
    images = []

    for message in reversed(message_list):

        message_images = []
        for file in message.get("files", []):
            if file.get("type") == "image":
                message_images.append(file.get("url"))
            elif file.get("content_type", "").startswith("image/"):
                message_images.append(file.get("url"))

        if message_images:
            images.append(message_images)

    return images


def get_image_urls(delta_images, request, metadata, user) -> list[str]:
    if not isinstance(delta_images, list):
        return []

    image_urls = []
    for img in delta_images:
        if not isinstance(img, dict) or img.get("type") != "image_url":
            continue

        url = img.get("image_url", {}).get("url")
        if not url:
            continue

        if url.startswith("data:image/png;base64"):
            url = get_image_url_from_base64(request, url, metadata, user)

        image_urls.append(url)

    return image_urls


def add_file_context(messages: list, chat_id: str, user) -> list:
    """
    Add file URLs to messages for native function calling.
    """
    if not chat_id or chat_id.startswith("local:"):
        return messages

    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        return messages

    history = chat.chat.get("history", {})
    stored_messages = get_message_list(
        history.get("messages", {}), history.get("currentId")
    )

    def format_file_tag(file):
        attrs = f'type="{file.get("type", "file")}" url="{file["url"]}"'
        if file.get("content_type"):
            attrs += f' content_type="{file["content_type"]}"'
        if file.get("name"):
            attrs += f' name="{file["name"]}"'
        return f"<file {attrs}/>"

    for message, stored_message in zip(messages, stored_messages):
        files_with_urls = [
            file for file in stored_message.get("files", []) if file.get("url")
        ]
        if not files_with_urls:
            continue

        file_tags = [format_file_tag(file) for file in files_with_urls]
        file_context = (
            "<attached_files>\n" + "\n".join(file_tags) + "\n</attached_files>\n\n"
        )

        content = message.get("content", "")
        if isinstance(content, list):
            message["content"] = [{"type": "text", "text": file_context}] + content
        else:
            message["content"] = file_context + content

    return messages


async def chat_image_generation_handler(
    request: Request, form_data: dict, extra_params: dict, user
):
    metadata = extra_params.get("__metadata__", {})
    chat_id = metadata.get("chat_id", None)
    __event_emitter__ = extra_params.get("__event_emitter__", None)

    if not chat_id or not isinstance(chat_id, str) or not __event_emitter__:
        return form_data

    if chat_id.startswith("local:"):
        message_list = form_data.get("messages", [])
    else:
        chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
        await __event_emitter__(
            {
                "type": "status",
                "data": {"description": "Creating image", "done": False},
            }
        )

        messages_map = chat.chat.get("history", {}).get("messages", {})
        message_id = chat.chat.get("history", {}).get("currentId")
        message_list = get_message_list(messages_map, message_id)

    user_message = get_last_user_message(message_list)

    prompt = user_message
    message_images = get_images_from_messages(message_list)

    # Limit to first 2 sets of images
    # We may want to change this in the future to allow more images
    input_images = []
    for idx, images in enumerate(message_images):
        if idx >= 2:
            break
        for image in images:
            input_images.append(image)

    system_message_content = ""

    if len(input_images) > 0 and request.app.state.config.ENABLE_IMAGE_EDIT:
        # Edit image(s)
        try:
            images = await image_edits(
                request=request,
                form_data=EditImageForm(**{"prompt": prompt, "image": input_images}),
                metadata={
                    "chat_id": metadata.get("chat_id", None),
                    "message_id": metadata.get("message_id", None),
                },
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

            system_message_content = "<context>The requested image has been edited and created and is now being shown to the user. Let them know that it has been generated.</context>"
        except Exception as e:
            log.debug(e)

            error_message = ""
            if isinstance(e, HTTPException):
                if e.detail and isinstance(e.detail, dict):
                    error_message = e.detail.get("message", str(e.detail))
                else:
                    error_message = str(e.detail)

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"An error occurred while generating an image",
                        "done": True,
                    },
                }
            )

            system_message_content = f"<context>Image generation was attempted but failed. The system is currently unable to generate the image. Tell the user that the following error occurred: {error_message}</context>"

    else:
        # Create image(s)
        if request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION:
            try:
                res = await generate_image_prompt(
                    request,
                    {
                        "model": form_data["model"],
                        "messages": form_data["messages"],
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

        try:
            images = await image_generations(
                request=request,
                form_data=CreateImageForm(**{"prompt": prompt}),
                metadata={
                    "chat_id": metadata.get("chat_id", None),
                    "message_id": metadata.get("message_id", None),
                },
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

            system_message_content = "<context>The requested image has been created by the system successfully and is now being shown to the user. Let the user know that the image they requested has been generated and is now shown in the chat.</context>"
        except Exception as e:
            log.debug(e)

            error_message = ""
            if isinstance(e, HTTPException):
                if e.detail and isinstance(e.detail, dict):
                    error_message = e.detail.get("message", str(e.detail))
                else:
                    error_message = str(e.detail)

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"An error occurred while generating an image",
                        "done": True,
                    },
                }
            )

            system_message_content = f"<context>Image generation was attempted but failed because of an error. The system is currently unable to generate the image. Tell the user that the following error occurred: {error_message}</context>"

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
            # Directly await async get_sources_from_items (no thread needed - fully async now)
            sources = await get_sources_from_items(
                request=request,
                items=files,
                queries=queries,
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=request.app.state.config.TOP_K,
                reranking_function=(
                    (
                        lambda query, documents: request.app.state.RERANKING_FUNCTION(
                            query, documents, user=user
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
                logit_bias = convert_logit_bias_input_to_json(params["logit_bias"])

                if logit_bias:
                    form_data["logit_bias"] = json.loads(logit_bias)
            except Exception as e:
                log.exception(f"Error parsing logit_bias: {e}")

    return form_data


async def convert_url_images_to_base64(form_data):
    messages = form_data.get("messages", [])

    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue

        new_content = []

        for item in content:
            if not isinstance(item, dict) or item.get("type") != "image_url":
                new_content.append(item)
                continue

            image_url = item.get("image_url", {}).get("url", "")
            if image_url.startswith("data:image/"):
                new_content.append(item)
                continue

            try:
                base64_data = await asyncio.to_thread(
                    get_image_base64_from_url, image_url
                )
                new_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": base64_data},
                    }
                )
            except Exception as e:
                log.debug(f"Error converting image URL to base64: {e}")
                new_content.append(item)

        message["content"] = new_content

    return form_data


async def process_chat_payload(request, form_data, user, metadata, model):
    # Pipeline Inlet -> Filter Inlet -> Chat Memory -> Chat Web Search -> Chat Image Generation
    # -> Chat Code Interpreter (Form Data Update) -> (Default) Chat Tools Function Calling
    # -> Chat Files

    form_data = apply_params_to_form_data(form_data, model)
    log.debug(f"form_data: {form_data}")

    system_message = get_system_message(form_data.get("messages", []))
    if system_message:  # Chat Controls/User Settings
        try:
            form_data = apply_system_prompt_to_body(
                system_message.get("content"), form_data, metadata, user, replace=True
            )  # Required to handle system prompt variables
        except:
            pass

    form_data = await convert_url_images_to_base64(form_data)

    event_emitter = get_event_emitter(metadata)
    event_caller = get_event_call(metadata)

    oauth_token = None
    try:
        if request.cookies.get("oauth_session_id", None):
            oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                user.id,
                request.cookies.get("oauth_session_id", None),
            )
    except Exception as e:
        log.error(f"Error getting OAuth token: {e}")

    extra_params = {
        "__event_emitter__": event_emitter,
        "__event_call__": event_caller,
        "__user__": user.model_dump() if isinstance(user, UserModel) else {},
        "__metadata__": metadata,
        "__oauth_token__": oauth_token,
        "__request__": request,
        "__model__": model,
        "__chat_id__": metadata.get("chat_id"),
        "__message_id__": metadata.get("message_id"),
    }
    # Initialize events to store additional event to be sent to the client
    # Initialize contexts and citation
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    task_model_id = get_task_model_id(
        form_data["model"],
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    events = []
    sources = []

    # Folder "Project" handling
    # Check if the request has chat_id and is inside of a folder
    chat_id = metadata.get("chat_id", None)
    if chat_id and user:
        chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
        if chat and chat.folder_id:
            folder = Folders.get_folder_by_id_and_user_id(chat.folder_id, user.id)

            if folder and folder.data:
                if "system_prompt" in folder.data:
                    form_data = apply_system_prompt_to_body(
                        folder.data["system_prompt"], form_data, metadata, user
                    )
                if "files" in folder.data:
                    form_data["files"] = [
                        *folder.data["files"],
                        *form_data.get("files", []),
                    ]

    # Model "Knowledge" handling
    user_message = get_last_user_message(form_data["messages"])
    model_knowledge = model.get("info", {}).get("meta", {}).get("knowledge", False)

    if (
        model_knowledge
        and metadata.get("params", {}).get("function_calling") != "native"
    ):
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

    variables = form_data.pop("variables", None)

    # Process the form_data through the pipeline
    try:
        form_data = await process_pipeline_inlet_filter(
            request, form_data, user, models
        )
    except Exception as e:
        raise e

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

    features = form_data.pop("features", None) or {}
    extra_params["__features__"] = features
    if features:
        if "voice" in features and features["voice"]:
            if request.app.state.config.VOICE_MODE_PROMPT_TEMPLATE != None:
                if request.app.state.config.VOICE_MODE_PROMPT_TEMPLATE != "":
                    template = request.app.state.config.VOICE_MODE_PROMPT_TEMPLATE
                else:
                    template = DEFAULT_VOICE_MODE_PROMPT_TEMPLATE

                form_data["messages"] = add_or_update_system_message(
                    template,
                    form_data["messages"],
                )

        if "memory" in features and features["memory"]:
            # Skip forced memory injection when native FC is enabled - model can use memory tools
            if metadata.get("params", {}).get("function_calling") != "native":
                form_data = await chat_memory_handler(
                    request, form_data, extra_params, user
                )

        if "web_search" in features and features["web_search"]:
            # Skip forced RAG web search when native FC is enabled - model can use web_search tool
            if metadata.get("params", {}).get("function_calling") != "native":
                form_data = await chat_web_search_handler(
                    request, form_data, extra_params, user
                )

        if "image_generation" in features and features["image_generation"]:
            # Skip forced image generation when native FC is enabled - model can use generate_image tool
            if metadata.get("params", {}).get("function_calling") != "native":
                form_data = await chat_image_generation_handler(
                    request, form_data, extra_params, user
                )

        if "code_interpreter" in features and features["code_interpreter"]:
            form_data["messages"] = add_or_update_user_message(
                (
                    request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE
                    if request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE != ""
                    else DEFAULT_CODE_INTERPRETER_PROMPT
                ),
                form_data["messages"],
            )

    tool_ids = form_data.pop("tool_ids", None)
    files = form_data.pop("files", None)

    prompt = get_last_user_message(form_data["messages"])
    # TODO: re-enable URL extraction from prompt
    # urls = []
    # if prompt and len(prompt or "") < 500 and (not files or len(files) == 0):
    #     urls = extract_urls(prompt)

    if files:
        if not files:
            files = []

        for file_item in files:
            if file_item.get("type", "file") == "folder":
                # Get folder files
                folder_id = file_item.get("id", None)
                if folder_id:
                    folder = Folders.get_folder_by_id_and_user_id(folder_id, user.id)
                    if folder and folder.data and "files" in folder.data:
                        files = [f for f in files if f.get("id", None) != folder_id]
                        files = [*files, *folder.data["files"]]

        # files = [*files, *[{"type": "url", "url": url, "name": url} for url in urls]]
        # Remove duplicate files based on their content
        files = list({json.dumps(f, sort_keys=True): f for f in files}.values())

    metadata = {
        **metadata,
        "tool_ids": tool_ids,
        "files": files,
    }
    form_data["metadata"] = metadata

    # Server side tools
    tool_ids = metadata.get("tool_ids", None)
    # Client side tools
    direct_tool_servers = metadata.get("tool_servers", None)

    log.debug(f"{tool_ids=}")
    log.debug(f"{direct_tool_servers=}")

    tools_dict = {}

    mcp_clients = {}
    mcp_tools_dict = {}

    if tool_ids:
        for tool_id in tool_ids:
            if tool_id.startswith("server:mcp:"):
                try:
                    server_id = tool_id[len("server:mcp:") :]

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

                    # Check access control for MCP server
                    if not has_tool_server_access(user, mcp_server_connection):
                        log.warning(
                            f"Access denied to MCP server {server_id} for user {user.id}"
                        )
                        continue

                    auth_type = mcp_server_connection.get("auth_type", "")
                    headers = {}
                    if auth_type == "bearer":
                        headers["Authorization"] = (
                            f"Bearer {mcp_server_connection.get('key', '')}"
                        )
                    elif auth_type == "none":
                        # No authentication
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

                    connection_headers = mcp_server_connection.get("headers", None)
                    if connection_headers and isinstance(connection_headers, dict):
                        for key, value in connection_headers.items():
                            headers[key] = value

                    mcp_clients[server_id] = MCPClient()
                    await mcp_clients[server_id].connect(
                        url=mcp_server_connection.get("url", ""),
                        headers=headers if headers else None,
                    )

                    function_name_filter_list = mcp_server_connection.get(
                        "config", {}
                    ).get("function_name_filter_list", "")

                    if isinstance(function_name_filter_list, str):
                        function_name_filter_list = function_name_filter_list.split(",")

                    tool_specs = await mcp_clients[server_id].list_tool_specs()
                    for tool_spec in tool_specs:

                        def make_tool_function(client, function_name):
                            async def tool_function(**kwargs):
                                return await client.call_tool(
                                    function_name,
                                    function_args=kwargs,
                                )

                            return tool_function

                        if function_name_filter_list:
                            if not is_string_allowed(
                                tool_spec["name"], function_name_filter_list
                            ):
                                # Skip this function
                                continue

                        tool_function = make_tool_function(
                            mcp_clients[server_id], tool_spec["name"]
                        )

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
                    if event_emitter:
                        await event_emitter(
                            {
                                "type": "chat:message:error",
                                "data": {
                                    "error": {
                                        "content": f"Failed to connect to MCP server '{server_id}'"
                                    }
                                },
                            }
                        )
                    continue

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

        if mcp_tools_dict:
            tools_dict = {**tools_dict, **mcp_tools_dict}

    if direct_tool_servers:
        for tool_server in direct_tool_servers:
            tool_specs = tool_server.pop("specs", [])

            for tool in tool_specs:
                tools_dict[tool["name"]] = {
                    "spec": tool,
                    "direct": True,
                    "server": tool_server,
                }

    if mcp_clients:
        metadata["mcp_clients"] = mcp_clients

    # Inject builtin tools for native function calling based on enabled features and model capability
    # Check if builtin_tools capability is enabled for this model (defaults to True if not specified)
    builtin_tools_enabled = (
        model.get("info", {})
        .get("meta", {})
        .get("capabilities", {})
        .get("builtin_tools", True)
    )
    if (
        metadata.get("params", {}).get("function_calling") == "native"
        and builtin_tools_enabled
    ):
        # Add file context to user messages
        chat_id = metadata.get("chat_id")
        form_data["messages"] = add_file_context(
            form_data.get("messages", []), chat_id, user
        )
        builtin_tools = get_builtin_tools(
            request,
            {
                **extra_params,
                "__event_emitter__": event_emitter,
            },
            features,
            model,
        )
        for name, tool_dict in builtin_tools.items():
            if name not in tools_dict:
                tools_dict[name] = tool_dict

    if tools_dict:
        if metadata.get("params", {}).get("function_calling") == "native":
            # If the function calling is native, then call the tools function calling handler
            metadata["tools"] = tools_dict
            form_data["tools"] = [
                {"type": "function", "function": tool.get("spec", {})}
                for tool in tools_dict.values()
            ]

        else:
            # If the function calling is not native, then call the tools function calling handler
            try:
                form_data, flags = await chat_completion_tools_handler(
                    request, form_data, extra_params, user, models, tools_dict
                )
                sources.extend(flags.get("sources", []))
            except Exception as e:
                log.exception(e)

    # Check if file context extraction is enabled for this model (default True)
    file_context_enabled = (
        model.get("info", {})
        .get("meta", {})
        .get("capabilities", {})
        .get("file_context", True)
    )

    if file_context_enabled:
        try:
            form_data, flags = await chat_completion_files_handler(
                request, form_data, extra_params, user
            )
            sources.extend(flags.get("sources", []))
        except Exception as e:
            log.exception(e)

    # If context is not empty, insert it into the messages
    if sources and prompt:
        form_data["messages"] = apply_source_context_to_messages(
            request, form_data["messages"], sources, prompt
        )

    # If there are citations, add them to the data_items
    sources = [
        source
        for source in sources
        if source.get("source", {}).get("name", "")
        or source.get("source", {}).get("id", "")
    ]

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

    return form_data, metadata, events


async def process_chat_response(
    request, response, form_data, user, metadata, model, events, tasks
):
    async def background_tasks_handler():
        message = None
        messages = []

        if "chat_id" in metadata and not metadata["chat_id"].startswith("local:"):
            messages_map = Chats.get_messages_map_by_chat_id(metadata["chat_id"])
            message = messages_map.get(metadata["message_id"]) if messages_map else None

            message_list = get_message_list(messages_map, metadata["message_id"])

            # Remove details tags and files from the messages.
            # as get_message_list creates a new list, it does not affect
            # the original messages outside of this handler

            messages = []
            for message in message_list:
                content = message.get("content", "")
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            content = item["text"]
                            break

                if isinstance(content, str):
                    content = re.sub(
                        r"<details\b[^>]*>.*?<\/details>|!\[.*?\]\(.*?\)",
                        "",
                        content,
                        flags=re.S | re.I,
                    ).strip()

                messages.append(
                    {
                        **message,
                        "role": message.get(
                            "role", "assistant"
                        ),  # Safe fallback for missing role
                        "content": content,
                    }
                )
        else:
            # Local temp chat, get the model and message from the form_data
            message = get_last_user_message_item(form_data.get("messages", []))
            messages = form_data.get("messages", [])
            if message:
                message["model"] = form_data.get("model")

        if message and "model" in message:
            if tasks and messages:
                if (
                    TASKS.FOLLOW_UP_GENERATION in tasks
                    and tasks[TASKS.FOLLOW_UP_GENERATION]
                ):
                    res = await generate_follow_ups(
                        request,
                        {
                            "model": message["model"],
                            "messages": messages,
                            "message_id": metadata["message_id"],
                            "chat_id": metadata["chat_id"],
                        },
                        user,
                    )

                    if res and isinstance(res, dict):
                        if len(res.get("choices", [])) == 1:
                            response_message = res.get("choices", [])[0].get(
                                "message", {}
                            )

                            follow_ups_string = response_message.get(
                                "content"
                            ) or response_message.get("reasoning_content", "")
                        else:
                            follow_ups_string = ""

                        follow_ups_string = follow_ups_string[
                            follow_ups_string.find("{") : follow_ups_string.rfind("}")
                            + 1
                        ]

                        try:
                            follow_ups = json.loads(follow_ups_string).get(
                                "follow_ups", []
                            )
                            await event_emitter(
                                {
                                    "type": "chat:message:follow_ups",
                                    "data": {
                                        "follow_ups": follow_ups,
                                    },
                                }
                            )

                            if not metadata.get("chat_id", "").startswith("local:"):
                                Chats.upsert_message_to_chat_by_id_and_message_id(
                                    metadata["chat_id"],
                                    metadata["message_id"],
                                    {
                                        "followUps": follow_ups,
                                    },
                                )

                        except Exception as e:
                            pass

                if not metadata.get("chat_id", "").startswith(
                    "local:"
                ):  # Only update titles and tags for non-temp chats
                    if TASKS.TITLE_GENERATION in tasks:
                        user_message = get_last_user_message(messages)
                        if user_message and len(user_message) > 100:
                            user_message = user_message[:100] + "..."

                        title = None
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
                                    response_message = res.get("choices", [])[0].get(
                                        "message", {}
                                    )

                                    title_string = (
                                        response_message.get("content")
                                        or response_message.get(
                                            "reasoning_content",
                                        )
                                        or message.get("content", user_message)
                                    )
                                else:
                                    title_string = ""

                                title_string = title_string[
                                    title_string.find("{") : title_string.rfind("}") + 1
                                ]

                                try:
                                    title = json.loads(title_string).get(
                                        "title", user_message
                                    )
                                except Exception as e:
                                    title = ""

                                if not title:
                                    title = messages[0].get("content", user_message)

                                Chats.update_chat_title_by_id(
                                    metadata["chat_id"], title
                                )

                                await event_emitter(
                                    {
                                        "type": "chat:title",
                                        "data": title,
                                    }
                                )

                        if title == None and len(messages) == 2:
                            title = messages[0].get("content", user_message)

                            Chats.update_chat_title_by_id(metadata["chat_id"], title)

                            await event_emitter(
                                {
                                    "type": "chat:title",
                                    "data": message.get("content", user_message),
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
                                response_message = res.get("choices", [])[0].get(
                                    "message", {}
                                )

                                tags_string = response_message.get(
                                    "content"
                                ) or response_message.get("reasoning_content", "")
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
    event_caller = None
    if (
        "session_id" in metadata
        and metadata["session_id"]
        and "chat_id" in metadata
        and metadata["chat_id"]
        and "message_id" in metadata
        and metadata["message_id"]
    ):
        event_emitter = get_event_emitter(metadata)
        event_caller = get_event_call(metadata)

    # Non-streaming response
    if not isinstance(response, StreamingResponse):
        if event_emitter:
            try:
                if isinstance(response, dict) or isinstance(response, JSONResponse):
                    if isinstance(response, list) and len(response) == 1:
                        # If the response is a single-item list, unwrap it #17213
                        response = response[0]

                    if isinstance(response, JSONResponse) and isinstance(
                        response.body, bytes
                    ):
                        try:
                            response_data = json.loads(
                                response.body.decode("utf-8", "replace")
                            )
                        except json.JSONDecodeError:
                            response_data = {
                                "error": {"detail": "Invalid JSON response"}
                            }
                    else:
                        response_data = response

                    if "error" in response_data:
                        error = response_data.get("error")

                        if isinstance(error, dict):
                            error = error.get("detail", error)
                        else:
                            error = str(error)

                        Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata["chat_id"],
                            metadata["message_id"],
                            {
                                "error": {"content": error},
                            },
                        )
                        if isinstance(error, str) or isinstance(error, dict):
                            await event_emitter(
                                {
                                    "type": "chat:message:error",
                                    "data": {"error": {"content": error}},
                                }
                            )

                    if "selected_model_id" in response_data:
                        Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata["chat_id"],
                            metadata["message_id"],
                            {
                                "selectedModelId": response_data["selected_model_id"],
                            },
                        )

                    choices = response_data.get("choices", [])
                    if choices and choices[0].get("message", {}).get("content"):
                        content = response_data["choices"][0]["message"]["content"]

                        if content:
                            await event_emitter(
                                {
                                    "type": "chat:completion",
                                    "data": response_data,
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
                                    "role": "assistant",
                                    "content": content,
                                },
                            )

                            # Send a webhook notification if the user is not active
                            if not Users.is_user_active(user.id):
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

                            await background_tasks_handler()

                    if events and isinstance(events, list):
                        extra_response = {}
                        for event in events:
                            if isinstance(event, dict):
                                extra_response.update(event)
                            else:
                                extra_response[event] = True

                        response_data = {
                            **extra_response,
                            **response_data,
                        }

                    if isinstance(response, dict):
                        response = response_data
                    if isinstance(response, JSONResponse):
                        response = JSONResponse(
                            content=response_data,
                            headers=response.headers,
                            status_code=response.status_code,
                        )

            except Exception as e:
                log.debug(f"Error occurred while processing request: {e}")
                pass

            return response
        else:
            if events and isinstance(events, list) and isinstance(response, dict):
                extra_response = {}
                for event in events:
                    if isinstance(event, dict):
                        extra_response.update(event)
                    else:
                        extra_response[event] = True

                response = {
                    **extra_response,
                    **response,
                }

            return response

    # Non standard response
    if not any(
        content_type in response.headers["Content-Type"]
        for content_type in ["text/event-stream", "application/x-ndjson"]
    ):
        return response

    oauth_token = None
    try:
        if request.cookies.get("oauth_session_id", None):
            oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                user.id,
                request.cookies.get("oauth_session_id", None),
            )
    except Exception as e:
        log.error(f"Error getting OAuth token: {e}")

    extra_params = {
        "__event_emitter__": event_emitter,
        "__event_call__": event_caller,
        "__user__": user.model_dump() if isinstance(user, UserModel) else {},
        "__metadata__": metadata,
        "__oauth_token__": oauth_token,
        "__request__": request,
        "__model__": model,
    }
    filter_functions = [
        Functions.get_function_by_id(filter_id)
        for filter_id in get_sorted_filter_ids(
            request, model, metadata.get("filter_ids", [])
        )
    ]

    # Streaming response
    if event_emitter and event_caller:
        task_id = str(uuid4())  # Create a unique task ID.
        model_id = form_data.get("model", "")

        def split_content_and_whitespace(content):
            content_stripped = content.rstrip()
            original_whitespace = (
                content[len(content_stripped) :]
                if len(content) > len(content_stripped)
                else ""
            )
            return content_stripped, original_whitespace

        def is_opening_code_block(content):
            backtick_segments = content.split("```")
            # Even number of segments means the last backticks are opening a new block
            return len(backtick_segments) > 1 and len(backtick_segments) % 2 == 0

        # Handle as a background task
        async def response_handler(response, events):
            def serialize_content_blocks(content_blocks, raw=False):
                content = ""

                for block in content_blocks:
                    if block["type"] == "text":
                        block_content = block["content"].strip()
                        if block_content:
                            content = f"{content}{block_content}\n"
                    elif block["type"] == "tool_calls":
                        attributes = block.get("attributes", {})

                        tool_calls = block.get("content", [])
                        results = block.get("results", [])

                        if content and not content.endswith("\n"):
                            content += "\n"

                        if results:

                            tool_calls_display_content = ""
                            for tool_call in tool_calls:

                                tool_call_id = tool_call.get("id", "")
                                tool_name = tool_call.get("function", {}).get(
                                    "name", ""
                                )
                                tool_arguments = tool_call.get("function", {}).get(
                                    "arguments", ""
                                )

                                tool_result = None
                                tool_result_files = None
                                for result in results:
                                    if tool_call_id == result.get("tool_call_id", ""):
                                        tool_result = result.get("content", None)
                                        tool_result_files = result.get("files", None)
                                        break

                                if tool_result is not None:
                                    tool_result_embeds = result.get("embeds", "")
                                    tool_calls_display_content = f'{tool_calls_display_content}<details type="tool_calls" done="true" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}" result="{html.escape(json.dumps(tool_result, ensure_ascii=False))}" files="{html.escape(json.dumps(tool_result_files)) if tool_result_files else ""}" embeds="{html.escape(json.dumps(tool_result_embeds))}">\n<summary>Tool Executed</summary>\n</details>\n'
                                else:
                                    tool_calls_display_content = f'{tool_calls_display_content}<details type="tool_calls" done="false" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}">\n<summary>Executing...</summary>\n</details>\n'

                            if not raw:
                                content = f"{content}{tool_calls_display_content}"
                        else:
                            tool_calls_display_content = ""

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

                    elif block["type"] == "reasoning":
                        reasoning_display_content = html.escape(
                            "\n".join(
                                (f"> {line}" if not line.startswith(">") else line)
                                for line in block["content"].splitlines()
                            )
                        )

                        reasoning_duration = block.get("duration", None)

                        start_tag = block.get("start_tag", "")
                        end_tag = block.get("end_tag", "")

                        if content and not content.endswith("\n"):
                            content += "\n"

                        if reasoning_duration is not None:
                            if raw:
                                content = (
                                    f'{content}{start_tag}{block["content"]}{end_tag}\n'
                                )
                            else:
                                content = f'{content}<details type="reasoning" done="true" duration="{reasoning_duration}">\n<summary>Thought for {reasoning_duration} seconds</summary>\n{reasoning_display_content}\n</details>\n'
                        else:
                            if raw:
                                content = (
                                    f'{content}{start_tag}{block["content"]}{end_tag}\n'
                                )
                            else:
                                content = f'{content}<details type="reasoning" done="false">\n<summary>Thinking…</summary>\n{reasoning_display_content}\n</details>\n'

                    elif block["type"] == "code_interpreter":
                        attributes = block.get("attributes", {})
                        output = block.get("output", None)
                        lang = attributes.get("lang", "")

                        content_stripped, original_whitespace = (
                            split_content_and_whitespace(content)
                        )
                        if is_opening_code_block(content_stripped):
                            # Remove trailing backticks that would open a new block
                            content = (
                                content_stripped.rstrip("`").rstrip()
                                + original_whitespace
                            )
                        else:
                            # Keep content as is - either closing backticks or no backticks
                            content = content_stripped + original_whitespace

                        if content and not content.endswith("\n"):
                            content += "\n"

                        if output:
                            output = html.escape(json.dumps(output))

                            if raw:
                                content = f'{content}<code_interpreter type="code" lang="{lang}">\n{block["content"]}\n</code_interpreter>\n```output\n{output}\n```\n'
                            else:
                                content = f'{content}<details type="code_interpreter" done="true" output="{output}">\n<summary>Analyzed</summary>\n```{lang}\n{block["content"]}\n```\n</details>\n'
                        else:
                            if raw:
                                content = f'{content}<code_interpreter type="code" lang="{lang}">\n{block["content"]}\n</code_interpreter>\n'
                            else:
                                content = f'{content}<details type="code_interpreter" done="false">\n<summary>Analyzing...</summary>\n```{lang}\n{block["content"]}\n```\n</details>\n'

                    else:
                        block_content = str(block["content"]).strip()
                        if block_content:
                            content = f"{content}{block['type']}: {block_content}\n"

                return content.strip()

            def convert_content_blocks_to_messages(content_blocks, raw=False):
                messages = []

                temp_blocks = []
                for idx, block in enumerate(content_blocks):
                    if block["type"] == "tool_calls":
                        messages.append(
                            {
                                "role": "assistant",
                                "content": serialize_content_blocks(temp_blocks, raw),
                                "tool_calls": block.get("content"),
                            }
                        )

                        results = block.get("results", [])

                        for result in results:
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": result["tool_call_id"],
                                    "content": result.get("content", "") or "",
                                }
                            )
                        temp_blocks = []
                    else:
                        temp_blocks.append(block)

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

            def tag_content_handler(content_type, tags, content, content_blocks):
                end_flag = False

                def extract_attributes(tag_content):
                    """Extract attributes from a tag if they exist."""
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
                    nonlocal content
                    nonlocal content_blocks

                    response_tool_calls = []

                    delta_count = 0
                    delta_chunk_size = max(
                        CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE,
                        int(
                            metadata.get("params", {}).get("stream_delta_chunk_size")
                            or 1
                        ),
                    )
                    last_delta_data = None

                    async def flush_pending_delta_data(threshold: int = 0):
                        nonlocal delta_count
                        nonlocal last_delta_data

                        if delta_count >= threshold and last_delta_data:
                            await event_emitter(
                                {
                                    "type": "chat:completion",
                                    "data": last_delta_data,
                                }
                            )
                            delta_count = 0
                            last_delta_data = None

                    async for line in response.body_iterator:
                        line = (
                            line.decode("utf-8", "replace")
                            if isinstance(line, bytes)
                            else line
                        )
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

                            data, _ = await process_filter_functions(
                                request=request,
                                filter_functions=filter_functions,
                                filter_type="stream",
                                form_data=data,
                                extra_params={"__body__": form_data, **extra_params},
                            )

                            if data:
                                if "event" in data and not getattr(
                                    request.state, "direct", False
                                ):
                                    await event_emitter(data.get("event", {}))

                                if "selected_model_id" in data:
                                    model_id = data["selected_model_id"]
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

                                    # 17421
                                    usage = data.get("usage", {}) or {}
                                    usage.update(data.get("timings", {}))  # llama.cpp
                                    if usage:
                                        await event_emitter(
                                            {
                                                "type": "chat:completion",
                                                "data": {
                                                    "usage": usage,
                                                },
                                            }
                                        )

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

                                    delta = choices[0].get("delta", {})

                                    # Handle delta annotations
                                    annotations = delta.get("annotations")
                                    if annotations:
                                        for annotation in annotations:
                                            if (
                                                annotation.get("type") == "url_citation"
                                                and "url_citation" in annotation
                                            ):
                                                url_citation = annotation[
                                                    "url_citation"
                                                ]

                                                url = url_citation.get("url", "")
                                                title = url_citation.get("title", url)

                                                await event_emitter(
                                                    {
                                                        "type": "source",
                                                        "data": {
                                                            "source": {
                                                                "name": title,
                                                                "url": url,
                                                            },
                                                            "document": [title],
                                                            "metadata": [
                                                                {
                                                                    "source": url,
                                                                    "name": title,
                                                                }
                                                            ],
                                                        },
                                                    }
                                                )

                                    delta_tool_calls = delta.get("tool_calls", None)
                                    if delta_tool_calls:
                                        for delta_tool_call in delta_tool_calls:
                                            tool_call_index = delta_tool_call.get(
                                                "index"
                                            )

                                            if tool_call_index is not None:
                                                # Check if the tool call already exists
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
                                                    # Add the new tool call
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
                                                    # Update the existing tool call
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

                                        # Emit pending tool calls in real-time
                                        if response_tool_calls:
                                            # Flush any pending text first
                                            await flush_pending_delta_data()

                                            pending_content_blocks = content_blocks + [
                                                {
                                                    "type": "tool_calls",
                                                    "content": response_tool_calls,
                                                    "pending": True,
                                                }
                                            ]
                                            await event_emitter(
                                                {
                                                    "type": "chat:completion",
                                                    "data": {
                                                        "content": serialize_content_blocks(
                                                            pending_content_blocks
                                                        ),
                                                    },
                                                }
                                            )

                                    image_urls = get_image_urls(
                                        delta.get("images", []), request, metadata, user
                                    )
                                    if image_urls:
                                        message_files = Chats.add_message_files_by_id_and_message_id(
                                            metadata["chat_id"],
                                            metadata["message_id"],
                                            [
                                                {"type": "image", "url": url}
                                                for url in image_urls
                                            ],
                                        )

                                        await event_emitter(
                                            {
                                                "type": "files",
                                                "data": {"files": message_files},
                                            }
                                        )

                                    value = delta.get("content")

                                    reasoning_content = (
                                        delta.get("reasoning_content")
                                        or delta.get("reasoning")
                                        or delta.get("thinking")
                                    )
                                    if reasoning_content:
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

                                        reasoning_block["content"] += reasoning_content

                                        data = {
                                            "content": serialize_content_blocks(
                                                content_blocks
                                            )
                                        }

                                    if value:
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

                                        if ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION:
                                            value = convert_markdown_base64_images(
                                                request,
                                                value,
                                                {
                                                    "chat_id": metadata.get(
                                                        "chat_id", None
                                                    ),
                                                    "message_id": metadata.get(
                                                        "message_id", None
                                                    ),
                                                },
                                                user,
                                            )

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

                                        if DETECT_REASONING_TAGS:
                                            content, content_blocks, _ = (
                                                tag_content_handler(
                                                    "reasoning",
                                                    reasoning_tags,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                            content, content_blocks, _ = (
                                                tag_content_handler(
                                                    "solution",
                                                    DEFAULT_SOLUTION_TAGS,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                        if DETECT_CODE_INTERPRETER:
                                            content, content_blocks, end = (
                                                tag_content_handler(
                                                    "code_interpreter",
                                                    DEFAULT_CODE_INTERPRETER_TAGS,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                            if end:
                                                break

                                        if ENABLE_REALTIME_CHAT_SAVE:
                                            # Save message in the database
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
                                            data = {
                                                "content": serialize_content_blocks(
                                                    content_blocks
                                                ),
                                            }

                                if delta:
                                    delta_count += 1
                                    last_delta_data = data
                                    if delta_count >= delta_chunk_size:
                                        await flush_pending_delta_data(delta_chunk_size)
                                else:
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
                                log.debug(f"Error: {e}")
                                continue
                    await flush_pending_delta_data()

                    if content_blocks:
                        # Clean up the last text block
                        if content_blocks[-1]["type"] == "text":
                            content_blocks[-1]["content"] = content_blocks[-1][
                                "content"
                            ].strip()

                            if not content_blocks[-1]["content"]:
                                content_blocks.pop()

                                if not content_blocks:
                                    content_blocks.append(
                                        {
                                            "type": "text",
                                            "content": "",
                                        }
                                    )

                        if content_blocks[-1]["type"] == "reasoning":
                            reasoning_block = content_blocks[-1]
                            if reasoning_block.get("ended_at") is None:
                                reasoning_block["ended_at"] = time.time()
                                reasoning_block["duration"] = int(
                                    reasoning_block["ended_at"]
                                    - reasoning_block["started_at"]
                                )

                    if response_tool_calls:
                        tool_calls.append(response_tool_calls)

                    if response.background:
                        await response.background()

                await stream_body_handler(response, form_data)

                tool_call_retries = 0
                tool_call_sources = []  # Track citation sources from tool results

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
                                    tool_function = get_updated_tool_function(
                                        function=tool["callable"],
                                        extra_params={
                                            "__messages__": form_data.get(
                                                "messages", []
                                            ),
                                            "__files__": metadata.get("files", []),
                                        },
                                    )

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

                        # Extract citation sources from tool results
                        if (
                            tool_function_name
                            in [
                                "search_web",
                                "view_knowledge_file",
                                "query_knowledge_files",
                            ]
                            and tool_result
                        ):
                            try:
                                citation_sources = get_citation_source_from_tool_result(
                                    tool_name=tool_function_name,
                                    tool_params=tool_function_params,
                                    tool_result=tool_result,
                                    tool_id=tool.get("tool_id", "") if tool else "",
                                )
                                tool_call_sources.extend(citation_sources)
                            except Exception as e:
                                log.exception(f"Error extracting citation source: {e}")

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

                    # Emit citation sources for UI display
                    for source in tool_call_sources:
                        await event_emitter({"type": "source", "data": source})

                    # Apply source context to messages for model
                    if tool_call_sources:
                        user_msg = get_last_user_message(form_data["messages"])
                        if user_msg:
                            form_data["messages"] = apply_source_context_to_messages(
                                request,
                                form_data["messages"],
                                tool_call_sources,
                                user_msg,
                            )
                        tool_call_sources.clear()

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
                            bypass_system_prompt=True,
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
                                bypass_system_prompt=True,
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
                if not Users.is_user_active(user.id):
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

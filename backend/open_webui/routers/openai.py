import asyncio
import hashlib
import json
import logging
import uuid
import time
from typing import Optional

import aiohttp
from aiocache import cached
import requests

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    JSONResponse,
    PlainTextResponse,
)
from pydantic import BaseModel
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
)
from open_webui.env import (
    MODELS_CACHE_TTL,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES


from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
    stream_chunks_handler,
)
from open_webui.utils.heartbeat import HeartbeatStreamWrapper

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access
from open_webui.utils.headers import include_user_info_headers


log = logging.getLogger(__name__)


##########################################
#
# Utility functions
#
##########################################


async def error_stream_generator(model_id, error_msg):
    """
    Generate an SSE error stream that the frontend can recognize and display with red error styling.
    The frontend checks for 'error' field in SSE data to trigger error rendering.
    """
    # Send error object that frontend can detect
    error_chunk = {
        "error": {
            "message": error_msg,
            "type": "api_error",
            "code": "upstream_error"
        }
    }
    yield f"data: {json.dumps(error_chunk)}\n\n"
    yield "data: [DONE]\n\n"


def convert_tools_to_responses_format(tools):
    if not isinstance(tools, list):
        return tools

    converted = []
    for tool in tools:
        if not isinstance(tool, dict):
            converted.append(tool)
            continue

        tool_type = tool.get("type", "function")
        function_spec = tool.get("function")

        # Already in Responses format; drop nested function if present.
        if "name" in tool:
            converted_tool = {k: v for k, v in tool.items() if k != "function"}
            converted.append(converted_tool)
            continue

        # Convert Chat Completions function tool -> Responses format.
        if tool_type == "function" and isinstance(function_spec, dict):
            converted_tool = {"type": "function"}
            converted_tool.update(function_spec)
            # Preserve any extra tool-level fields except the nested function.
            for key, value in tool.items():
                if key in ("function",):
                    continue
                converted_tool.setdefault(key, value)
            converted.append(converted_tool)
            continue

        # Fallback: keep as-is for non-function tool types.
        converted.append(tool)

    return converted


def convert_tool_choice_to_responses_format(tool_choice):
    if isinstance(tool_choice, dict):
        if tool_choice.get("type") == "function":
            function_spec = tool_choice.get("function", {})
            if isinstance(function_spec, dict) and function_spec.get("name"):
                converted = {"type": "function", "name": function_spec.get("name")}
                for key, value in tool_choice.items():
                    if key not in ("type", "function"):
                        converted.setdefault(key, value)
                return converted
        return tool_choice

    return tool_choice


def _tool_call_id_from_item(item, event=None):
    if not isinstance(item, dict):
        item = {}
    if event is None or not isinstance(event, dict):
        event = {}

    for key in ("id", "call_id", "tool_call_id"):
        value = item.get(key)
        if value:
            return value

    for key in ("call_id", "tool_call_id", "id"):
        value = event.get(key)
        if value:
            return value

    for key in ("item_id", "output_id"):
        value = event.get(key)
        if value:
            return value

    return None


def _tool_call_name_from_item(item):
    if not isinstance(item, dict):
        return ""
    return (
        item.get("name")
        or item.get("name_delta")
        or item.get("function_name")
        or item.get("tool_name")
        or item.get("function", {}).get("name")
        or ""
    )


def _tool_call_args_from_item(item):
    if not isinstance(item, dict):
        return ""
    return (
        item.get("arguments")
        or item.get("arguments_delta")
        or item.get("arguments_text")
        or item.get("arguments_text_delta")
        or item.get("input")
        or item.get("parameters")
        or item.get("args")
        or item.get("function", {}).get("arguments")
        or item.get("function", {}).get("parameters")
        or ""
    )


def _stringify_tool_call_args(arguments):
    if arguments is None:
        return ""
    if isinstance(arguments, str):
        return arguments
    try:
        return json.dumps(arguments, ensure_ascii=False)
    except Exception:
        return str(arguments)


def convert_to_responses_payload(chat_payload: dict) -> dict:
    """
    Convert Chat Completions API format to Responses API format.
    
    Chat Completions:
        {"messages": [...], "model": "...", "stream": true, ...}
    
    Responses API:
        {"input": [...], "model": "...", "stream": true, ...}
    
    Uses EasyInputMessageParam format which supports all roles (user, assistant, system, developer)
    and allows simple string content for easier compatibility.
    """
    responses_payload = {}
    
    # Model is the same
    if "model" in chat_payload:
        responses_payload["model"] = chat_payload["model"]
    
    # Convert messages to input items using EasyInputMessageParam format
    messages = chat_payload.get("messages", [])
    input_items = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # DEBUG: Log each message being processed
        log.info(f"[DEBUG RESPONSES PAYLOAD] Processing message role={role}, has_content={bool(content)}, has_tool_calls={bool(msg.get('tool_calls'))}, tool_call_id={msg.get('tool_call_id')}")
        
        if role == "system":
            # System messages become instructions in Responses API
            responses_payload["instructions"] = content if isinstance(content, str) else str(content)
            continue
        if role in ("tool", "function"):
            tool_call_id = (
                msg.get("tool_call_id")
                or msg.get("id")
                or msg.get("name")
            )
            output = (
                content
                if isinstance(content, str)
                else json.dumps(content, ensure_ascii=False, default=str)
            )
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call_id,
                    "output": output,
                }
            )
            continue
        else:
            # Map role: assistant -> assistant, user -> user, anything else -> user
            mapped_role = role if role in ["user", "assistant"] else "user"
            
            # Build the message item using EasyInputMessageParam format
            # All roles (including assistant) can use simple string content
            if isinstance(content, str):
                # Simple text content - use direct string
                item = {
                    "type": "message",
                    "role": mapped_role,
                    "content": content
                }
            elif isinstance(content, list):
                # Multimodal content - need to build content array
                # For user messages, use input_text and input_image types
                # For assistant messages, we just extract text and use it as string
                if mapped_role == "assistant":
                    # Assistant messages: extract text content as simple string
                    text_parts = []
                    for c in content:
                        if isinstance(c, dict):
                            if c.get("type") == "text":
                                text_parts.append(c.get("text", ""))
                        elif isinstance(c, str):
                            text_parts.append(c)
                    item = {
                        "type": "message",
                        "role": "assistant",
                        "content": "".join(text_parts)
                    }
                else:
                    # User messages with multimodal content
                    content_parts = []
                    for c in content:
                        if isinstance(c, dict):
                            if c.get("type") == "text":
                                content_parts.append({"type": "input_text", "text": c.get("text", "")})
                            elif c.get("type") == "image_url":
                                image_url = c.get("image_url", {}).get("url", "")
                                content_parts.append({"type": "input_image", "image_url": image_url})
                        elif isinstance(c, str):
                            content_parts.append({"type": "input_text", "text": c})
                    
                    if content_parts:
                        item = {
                            "type": "message",
                            "role": "user",
                            "content": content_parts
                        }
                    else:
                        # Fallback to empty string if no content parts
                        item = {
                            "type": "message",
                            "role": "user",
                            "content": ""
                        }
            else:
                # Fallback for other content types
                item = {
                    "type": "message",
                    "role": mapped_role,
                    "content": str(content) if content else ""
                }
            
            # For assistant messages with tool_calls but no content, skip adding empty message
            # Only add function_call items to match Responses API expected format
            has_tool_calls = mapped_role == "assistant" and msg.get("tool_calls")
            has_actual_content = bool(content) if isinstance(content, str) else bool(content)
            
            if has_tool_calls and not has_actual_content:
                # Skip empty message, only add function_call items
                log.info(f"[DEBUG RESPONSES PAYLOAD] Skipping empty assistant message, adding function_calls only")
            else:
                input_items.append(item)

            if has_tool_calls:
                for tool_call in msg.get("tool_calls", []):
                    if not isinstance(tool_call, dict):
                        continue
                    tool_call_id = _tool_call_id_from_item(tool_call)
                    tool_call_name = _tool_call_name_from_item(tool_call)
                    tool_call_args = _stringify_tool_call_args(
                        _tool_call_args_from_item(tool_call)
                    )
                    input_items.append(
                        {
                            "type": "function_call",
                            "call_id": tool_call_id or f"call_{uuid.uuid4().hex}",
                            "name": tool_call_name,
                            "arguments": tool_call_args,
                        }
                    )
    
    responses_payload["input"] = input_items
    
    # Copy other common parameters
    if "stream" in chat_payload:
        responses_payload["stream"] = chat_payload["stream"]
    if "max_tokens" in chat_payload:
        responses_payload["max_output_tokens"] = chat_payload["max_tokens"]
    if "temperature" in chat_payload:
        responses_payload["temperature"] = chat_payload["temperature"]
    if "top_p" in chat_payload:
        responses_payload["top_p"] = chat_payload["top_p"]
    
    # Handle reasoning parameters - convert reasoning_effort to Responses API format
    reasoning_effort = chat_payload.get("reasoning_effort") or chat_payload.get("reasoning", {}).get("effort")
    model_name = chat_payload.get("model", "")
    is_reasoning_model = is_openai_reasoning_model(model_name)

    if reasoning_effort:
        # Responses API format: reasoning.effort and reasoning.summary are inside the same object
        responses_payload["reasoning"] = {
            "effort": reasoning_effort.lower(),
            "summary": "detailed"  # Options: 'concise', 'detailed', 'auto'
        }
    elif is_reasoning_model:
        # For reasoning models without explicit reasoning_effort, still enable summary to show thinking
        responses_payload["reasoning"] = {
            "summary": "detailed"  # Options: 'concise', 'detailed', 'auto'
        }
        log.info(f"[RESPONSES API] Auto-enabled reasoning.summary for reasoning model: {model_name}")
    
    # Convert tools/tool_choice from Chat Completions format to Responses format.
    if "tools" in chat_payload:
        responses_payload["tools"] = convert_tools_to_responses_format(
            chat_payload["tools"]
        )
    if "tool_choice" in chat_payload:
        responses_payload["tool_choice"] = convert_tool_choice_to_responses_format(
            chat_payload["tool_choice"]
        )
    
    # DEBUG: Log the last few input items to see function_call and function_call_output
    if len(input_items) > 5:
        last_items = input_items[-5:]
    else:
        last_items = input_items
    log.info(f"[DEBUG RESPONSES PAYLOAD] Last {len(last_items)} input items: {json.dumps(last_items, ensure_ascii=False, default=str)[:1500]}")
    
    log.info(f"Responses API payload: {json.dumps(responses_payload, ensure_ascii=False, default=str)[:2000]}")
    return responses_payload



async def responses_stream_to_chat_completions_stream(response: aiohttp.ClientResponse, model_id: str):
    """
    Convert Responses API streaming events to Chat Completions format.
    
    Responses API events:
        {"type": "response.output_text.delta", "delta": "..."} 
        {"type": "response.done", ...}
    
    Converts to Chat Completions format:
        {"choices": [{"delta": {"content": "..."}}]}
    """
    stream_id = f"chatcmpl-{uuid.uuid4().hex}"
    timestamp = int(time.time())
    
    # Log response info for debugging
    log.info(f"Responses API stream: status={response.status}, content_type={response.headers.get('Content-Type', 'unknown')}")
    
    buffer = ""
    
    def create_chunk(
        delta_content=None,
        reasoning_content=None,
        tool_calls=None,
        finish_reason=None,
    ):
        """Helper to create a chat completion chunk."""
        delta = {}
        if delta_content is not None:
            delta["content"] = delta_content
        if reasoning_content is not None:
            delta["reasoning_content"] = reasoning_content
        if tool_calls is not None:
            delta["tool_calls"] = tool_calls
        
        return {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": timestamp,
            "model": model_id,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]
        }
    
    tool_call_index_by_id = {}
    tool_call_index_by_fallback = {}
    next_tool_call_index = 0
    seen_tool_call_ids = set()
    tool_call_from_added = {}
    tool_call_has_delta = set()
    content_started = False
    reasoning_source = None

    def get_tool_call_index(tool_call_id, provided_index=None):
        nonlocal next_tool_call_index

        if tool_call_id:
            if tool_call_id not in tool_call_index_by_id:
                tool_call_index_by_id[tool_call_id] = next_tool_call_index
                next_tool_call_index += 1
            return tool_call_index_by_id[tool_call_id]

        if provided_index is not None:
            if provided_index not in tool_call_index_by_fallback:
                tool_call_index_by_fallback[provided_index] = next_tool_call_index
                next_tool_call_index += 1
            return tool_call_index_by_fallback[provided_index]

        tool_call_index = next_tool_call_index
        next_tool_call_index += 1
        return tool_call_index

    def build_tool_call_delta(item, event=None, use_delta=False):
        if event is None:
            event = {}
        if not isinstance(item, dict):
            return None

        tool_type = (
            item.get("type")
            or event.get("item", {}).get("type")
            or event.get("delta", {}).get("type")
            or ""
        )
        if tool_type not in ("tool_call", "function_call"):
            return None

        tool_call_id = _tool_call_id_from_item(item, event)
        provided_index = (
            item.get("index")
            or event.get("output_index")
            or event.get("item_index")
            or event.get("index")
        )
        tool_call_index = get_tool_call_index(tool_call_id, provided_index)

        name = _tool_call_name_from_item(item)
        arguments = _tool_call_args_from_item(item)
        if use_delta and not name and not arguments:
            return None

        name = name or ""
        arguments = _stringify_tool_call_args(arguments)

        if tool_call_id:
            tool_call_id_value = tool_call_id
        else:
            tool_call_id_value = f"call_{stream_id}_{tool_call_index}"

        tool_call = {
            "index": tool_call_index,
            "id": tool_call_id_value,
            "type": "function",
            "function": {
                "name": name,
                "arguments": arguments,
            },
        }
        return tool_call

    try:
        async for chunk in response.content.iter_any():
            if not chunk:
                continue
            
            buffer += chunk.decode("utf-8", errors="replace")
            
            # Process SSE events
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                
                if not line:
                    continue
                
                # Handle SSE data: prefix
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield f"data: [DONE]\n\n"
                        return
                    
                    try:
                        event = json.loads(data)
                        event_type = event.get("type", "")

                        # Debug: log event types
                        log.info(f"Responses API event: type={event_type}")

                        # Handle text delta (main response content)
                        if event_type == "response.output_text.delta":
                            delta_text = event.get("delta", "")
                            if delta_text:
                                content_started = True
                            yield f"data: {json.dumps(create_chunk(delta_content=delta_text))}\n\n"
                        
                        # Handle reasoning/thinking delta - just forward as reasoning_content
                        # middleware.py will handle the <details> tag wrapping
                        elif event_type in ("response.reasoning_summary_text.delta", "response.reasoning.delta"):
                            reasoning_text = event.get("delta", "")
                            if reasoning_text and not content_started:
                                event_source = (
                                    "summary"
                                    if event_type == "response.reasoning_summary_text.delta"
                                    else "reasoning"
                                )
                                if reasoning_source is None:
                                    reasoning_source = event_source
                                if reasoning_source != event_source:
                                    continue
                                yield f"data: {json.dumps(create_chunk(reasoning_content=reasoning_text))}\n\n"

                        elif event_type == "response.output_item.added":
                            item = event.get("item", {}) or {}
                            if not isinstance(item, dict):
                                item = {}
                            # Debug: log the full item to see its structure
                            log.info(f"[TOOL DEBUG] output_item.added - item: {json.dumps(item, default=str)[:500]}")
                            tool_call = build_tool_call_delta(item, event)
                            if tool_call:
                                log.info(f"[TOOL DEBUG] Built tool_call from added: {json.dumps(tool_call, default=str)}")
                                tool_call_from_added[tool_call.get("id")] = tool_call

                        elif event_type == "response.output_item.delta":
                            item = event.get("item", {})
                            delta = event.get("delta", {})

                            tool_item = {}
                            if isinstance(delta, dict):
                                tool_item.update(delta)
                            if isinstance(item, dict) and "type" not in tool_item:
                                tool_item["type"] = item.get("type")

                            tool_call = build_tool_call_delta(
                                tool_item, event, use_delta=True
                            )
                            if tool_call:
                                tool_call_has_delta.add(tool_call.get("id"))
                                yield f"data: {json.dumps(create_chunk(tool_calls=[tool_call]))}\n\n"

                        elif event_type == "response.output_item.done":
                            item = event.get("item", {}) or {}
                            if not isinstance(item, dict):
                                item = {}
                            # Debug: log the full item to see its structure
                            log.info(f"[TOOL DEBUG] output_item.done - item: {json.dumps(item, default=str)[:1000]}")
                            tool_call_id = _tool_call_id_from_item(item, event)
                            if tool_call_id and tool_call_id in tool_call_has_delta:
                                continue
                            tool_call = build_tool_call_delta(item, event)
                            if tool_call:
                                log.info(f"[TOOL DEBUG] Built tool_call from done: {json.dumps(tool_call, default=str)}")
                                tool_call_id_value = tool_call.get("id")
                                if tool_call_id_value in tool_call_has_delta:
                                    continue
                                # FIX: Use the current tool_call directly (has full arguments)
                                # Do NOT use tool_call_from_added which has empty arguments from the initial event
                                seen_tool_call_ids.add(tool_call_id_value)
                                yield f"data: {json.dumps(create_chunk(tool_calls=[tool_call]))}\n\n"
                        
                        # Handle completion (OpenAI uses "response.completed", not "response.done")
                        elif event_type in ("response.completed", "response.done"):
                            # Log full event for debugging
                            log.info(f"Completion event received: {json.dumps(event, default=str)[:1000]}")

                            # Extract usage info from completion event
                            response_data = event.get("response", {}) or {}
                            if not isinstance(response_data, dict):
                                response_data = {}
                            usage = response_data.get("usage", {})

                            # Also try to get usage directly from event (some APIs put it there)
                            if not usage:
                                usage = event.get("usage", {})
                            
                            # Extract usage data
                            usage_data = None
                            if usage:
                                log.info(f"Extracted usage from Responses API: {usage}")
                                usage_data = {
                                    "prompt_tokens": usage.get("input_tokens", 0),
                                    "completion_tokens": usage.get("output_tokens", 0),
                                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                                }

                                # Extract reasoning_tokens and put in completion_tokens_details (frontend expects this structure)
                                output_details = usage.get("output_tokens_details", {})
                                if isinstance(output_details, dict):
                                    reasoning_tokens = output_details.get("reasoning_tokens", 0)
                                    if reasoning_tokens:
                                        usage_data["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}

                                # Extract cached_tokens and put in prompt_tokens_details (frontend expects this structure)
                                input_details = usage.get("input_tokens_details", {})
                                if isinstance(input_details, dict):
                                    cached_tokens = input_details.get("cached_tokens", 0)
                                    if cached_tokens:
                                        usage_data["prompt_tokens_details"] = {"cached_tokens": cached_tokens}
                                
                                log.info(f"Using usage data: {usage_data}")
                            else:
                                log.warning(f"No usage found in response.completed event. response_data keys: {list(response_data.keys())}")
                            
                            # Send finish chunk with usage info (OpenAI spec)
                            finish_chunk = {
                                "id": stream_id,
                                "object": "chat.completion.chunk",
                                "created": timestamp,
                                "model": model_id,
                                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                            }
                            
                            if usage_data:
                                finish_chunk["usage"] = usage_data

                            yield f"data: {json.dumps(finish_chunk)}\n\n"
                            yield f"data: [DONE]\n\n"
                            return
                        
                        # Handle errors
                        elif event_type == "error":
                            error_msg = event.get("error", {}).get("message", "Unknown error")
                            error_chunk = {
                                "error": {
                                    "message": error_msg,
                                    "type": "api_error",
                                    "code": "responses_api_error"
                                }
                            }
                            yield f"data: {json.dumps(error_chunk)}\n\n"
                            yield f"data: [DONE]\n\n"
                            return
                            
                    except json.JSONDecodeError:
                        log.warning(f"Failed to decode Responses API event: {data[:100]}")
                        continue
    

    except aiohttp.ClientPayloadError as e:
        # Handle transfer encoding errors (e.g., stream interrupted)
        # This often means the API returned an error mid-stream
        log.error(f"Stream payload error: {e}")
        
        # Try to extract any error message from the buffer
        error_message = f"Stream interrupted: {str(e)}"
        if buffer:
            log.error(f"Buffer content at error: {buffer[:500]}")
            # Try to parse any JSON error in the buffer
            try:
                # Look for JSON object in buffer
                import re
                json_match = re.search(r'\{[^{}]*"error"[^{}]*\}', buffer)
                if json_match:
                    error_data = json.loads(json_match.group())
                    if "error" in error_data:
                        err = error_data["error"]
                        if isinstance(err, dict):
                            error_message = err.get("message", error_message)
                        else:
                            error_message = str(err)
            except Exception:
                pass
        
        error_chunk = {
            "error": {
                "message": error_message,
                "type": "stream_error",
                "code": "transfer_encoding_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
    except Exception as e:
        log.error(f"Stream processing error: {e}")
        error_chunk = {
            "error": {
                "message": f"Stream error: {str(e)}",
                "type": "stream_error",
                "code": "unknown_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
    
    # Ensure we always send [DONE]
    yield f"data: [DONE]\n\n"


def convert_responses_to_chat_completions(responses_data: dict, model_id: str) -> dict:
    """
    Convert non-streaming Responses API response to Chat Completions format.
    """
    output = responses_data.get("output", [])
    content = ""
    tool_calls = []
    tool_call_index = 0
    
    # DEBUG: Log the output structure
    log.info(f"[DEBUG RESPONSES->CHAT] output count: {len(output)}, text field exists: {bool(responses_data.get('text'))}")
    
    # Extract text from output items
    for item in output:
        item_type = item.get("type", "")
        log.info(f"[DEBUG RESPONSES->CHAT] item type: {item_type}")
        
        if item_type == "message":
            for part in item.get("content", []):
                part_type = part.get("type", "")
                if part_type in ("output_text", "text"):
                    content += part.get("text", "")
        elif item_type in ("tool_call", "function_call"):
            tool_call_id = _tool_call_id_from_item(item)
            tool_call_name = _tool_call_name_from_item(item)
            tool_call_args = _stringify_tool_call_args(
                _tool_call_args_from_item(item)
            )
            tool_calls.append(
                {
                    "index": tool_call_index,
                    "id": tool_call_id or f"call_{uuid.uuid4().hex}",
                    "type": "function",
                    "function": {
                        "name": tool_call_name,
                        "arguments": tool_call_args,
                    },
                }
            )
            tool_call_index += 1
    
    # Also check top-level 'text' field (some Responses API implementations put content here)
    if not content and responses_data.get("text"):
        text_field = responses_data.get("text")
        log.info(f"[DEBUG RESPONSES->CHAT] text field type: {type(text_field).__name__}, value: {str(text_field)[:200]}")
        if isinstance(text_field, str):
            content = text_field
        elif isinstance(text_field, dict):
            content = text_field.get("value", "") or text_field.get("text", "") or text_field.get("content", "")
        elif isinstance(text_field, list):
            # If text is a list of content items, extract text from them
            parts = []
            for item in text_field:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("text", "") or item.get("value", "") or "")
            content = "".join(parts)
    
    log.info(f"[DEBUG RESPONSES->CHAT] extracted content length: {len(content)}, tool_calls: {len(tool_calls)}")
    
    return {
        "id": responses_data.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content,
                **({"tool_calls": tool_calls} if tool_calls else {}),
            },
            "finish_reason": "tool_calls" if tool_calls else "stop"
        }],
        "usage": responses_data.get("usage", {})
    }


def _stringify_message_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                item_type = item.get("type", "")
                if item_type in ("text", "output_text"):
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        parts.append(text)
                        continue
                text = item.get("text") or item.get("content") or item.get("value") or ""
                if text:
                    parts.append(text)
        return "".join(parts)
    if isinstance(content, dict):
        return content.get("text") or content.get("content") or content.get("value") or ""
    return ""


def _normalize_chat_completion_response(response: dict) -> dict:
    if not isinstance(response, dict):
        return response

    choices = response.get("choices")
    if not isinstance(choices, list):
        return response

    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            if isinstance(choice.get("text"), str):
                choice["message"] = {
                    "role": "assistant",
                    "content": choice.get("text"),
                }
            continue

        content = message.get("content")
        normalized = _stringify_message_content(content)
        if normalized:
            message["content"] = normalized
            continue

        for key in ("text", "output_text", "answer", "result"):
            value = message.get(key)
            if isinstance(value, str) and value:
                message["content"] = value
                break

    return response


async def _safe_response_json(response: aiohttp.ClientResponse):
    try:
        body = await response.text()
    except Exception as e:
        log.debug("Failed reading response body from %s: %s", response.url, e)
        return None

    if not body:
        return None

    try:
        return json.loads(body)
    except Exception:
        snippet = body[:500].replace("\n", " ").replace("\r", " ")
        log.debug("Non-JSON response from %s: %s", response.url, snippet)
        return None


async def send_get_request(url, key=None, user: UserModel = None):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                **({"Authorization": f"Bearer {key}"} if key else {}),
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            async with session.get(
                url,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                if response.status != 200:
                    log.error("Model list request failed (%s): HTTP %s", url, response.status)
                    return None
                return await _safe_response_json(response)
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


def is_tool_calling_disabled_error(response) -> bool:
    """
    Detect if the API error indicates that tool calling is disabled.
    This allows automatic fallback to retry without tools.
    
    Common error patterns:
    - Anthropic/Claude proxies: "Tool calling is disabled by configuration"
    - Some proxies: moderation_error with MODERATION_BLOCKED
    - Generic: "tool definitions" or "tool-related content" in message
    
    Args:
        response: Can be dict (JSON error) or str (SSE/text error)
    """
    # Keywords that indicate tool calling is disabled
    tool_disabled_keywords = [
        "tool calling is disabled",
        "tool definitions",
        "tool-related content",
        "tools are not supported",
        "function calling is disabled",
        "functions are not supported",
        "remove 'tools'",
        "remove 'tool_choice'",
    ]
    
    # Handle string response (SSE/text format)
    if isinstance(response, str):
        response_lower = response.lower()
        for keyword in tool_disabled_keywords:
            if keyword in response_lower:
                return True
        return False
    
    # Handle dict response (JSON format)
    if not isinstance(response, dict):
        return False
    
    error = response.get("error", {})
    if isinstance(error, str):
        error_text = error.lower()
    elif isinstance(error, dict):
        error_text = (error.get("message", "") or "").lower()
        error_code = (error.get("code", "") or "").upper()
        error_type = (error.get("type", "") or "").lower()
        
        # Check for moderation block on tools
        if error_type == "moderation_error" and error_code == "MODERATION_BLOCKED":
            if "tool" in error_text:
                return True
    else:
        return False
    
    for keyword in tool_disabled_keywords:
        if keyword in error_text:
            return True
    
    return False


def openai_reasoning_model_handler(payload):
    """
    Handle reasoning model specific parameters
    """
    if "max_tokens" in payload:
        # Convert "max_tokens" to "max_completion_tokens" for all reasoning models
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    # Handle system role conversion based on model type
    if payload["messages"][0]["role"] == "system":
        model_lower = payload["model"].lower()
        # Legacy models use "user" role instead of "system"
        if model_lower.startswith("o1-mini") or model_lower.startswith("o1-preview"):
            payload["messages"][0]["role"] = "user"
        else:
            payload["messages"][0]["role"] = "developer"

    return payload


async def get_headers_and_cookies(
    request: Request,
    url,
    key=None,
    config=None,
    metadata: Optional[dict] = None,
    user: UserModel = None,
):
    cookies = {}
    headers = {
        "Content-Type": "application/json",
        **(
            {
                "HTTP-Referer": "https://openwebui.com/",
                "X-Title": "Open WebUI",
            }
            if "openrouter.ai" in url
            else {}
        ),
    }

    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)
        if metadata and metadata.get("chat_id"):
            headers["X-OpenWebUI-Chat-Id"] = metadata.get("chat_id")

    token = None
    auth_type = config.get("auth_type")

    if auth_type == "bearer" or auth_type is None:
        # Default to bearer if not specified
        token = f"{key}"
    elif auth_type == "none":
        token = None
    elif auth_type == "session":
        cookies = request.cookies
        token = request.state.token.credentials
    elif auth_type == "system_oauth":
        cookies = request.cookies

        oauth_token = None
        try:
            if request.cookies.get("oauth_session_id", None):
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id,
                    request.cookies.get("oauth_session_id", None),
                )
        except Exception as e:
            log.error(f"Error getting OAuth token: {e}")

        if oauth_token:
            token = f"{oauth_token.get('access_token', '')}"

    elif auth_type in ("azure_ad", "microsoft_entra_id"):
        token = get_microsoft_entra_id_access_token()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if config.get("headers") and isinstance(config.get("headers"), dict):
        headers = {**headers, **config.get("headers")}

    return headers, cookies


def get_microsoft_entra_id_access_token():
    """
    Get Microsoft Entra ID access token using DefaultAzureCredential for Azure OpenAI.
    Returns the token string or None if authentication fails.
    """
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        return token_provider()
    except Exception as e:
        log.error(f"Error getting Microsoft Entra ID access token: {e}")
        return None


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.OPENAI_API_KEYS) != len(
        request.app.state.config.OPENAI_API_BASE_URLS
    ):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(
            request.app.state.config.OPENAI_API_BASE_URLS
        ):
            request.app.state.config.OPENAI_API_KEYS = (
                request.app.state.config.OPENAI_API_KEYS[
                    : len(request.app.state.config.OPENAI_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS)
                - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.OPENAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post("/audio/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = request.app.state.config.OPENAI_API_BASE_URLS.index(
            "https://api.openai.com/v1"
        )

        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = CACHE_DIR / "audio" / "speech"
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
        file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
        key = request.app.state.config.OPENAI_API_KEYS[idx]
        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        headers, cookies = await get_headers_and_cookies(
            request, url, key, api_config, user=user
        )

        r = None
        try:
            r = requests.post(
                url=f"{url}/audio/speech",
                data=body,
                headers=headers,
                cookies=cookies,
                stream=True,
            )

            r.raise_for_status()

            # Save the streaming content to a file
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            with open(file_body_path, "w") as f:
                json.dump(json.loads(body.decode("utf-8")), f)

            # Return the saved file
            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error']}"
                except Exception:
                    detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.OPENAI_API_KEYS[:num_urls]
            request.app.state.config.OPENAI_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.OPENAI_API_CONFIGS) and (
            url not in request.app.state.config.OPENAI_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.OPENAI_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "openai",
                                "openai": {"id": model_id},
                                "urlIdx": idx,
                            }
                            for model_id in model_ids
                        ],
                    }

                    request_tasks.append(
                        asyncio.ensure_future(asyncio.sleep(0, model_list))
                    )
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            connection_type = api_config.get("connection_type", "external")
            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            model_list = (
                response if isinstance(response, list) else response.get("data", [])
            )
            if not isinstance(model_list, list):
                # Catch non-list responses
                model_list = []

            for model in model_list:
                # Remove name key if its value is None #16689
                if "name" in model and model["name"] is None:
                    del model["name"]

                if prefix_id:
                    model["id"] = (
                        f"{prefix_id}.{model.get('id', model.get('name', ''))}"
                    )

                if tags:
                    model["tags"] = tags

                if connection_type:
                    model["connection_type"] = connection_type

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user, db=None):
    # Filter models based on user access control
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"], db=db)
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control, db=db
            ):
                filtered_models.append(model)
    return filtered_models



async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def is_supported_openai_models(model_id):
        if any(
            name in model_id
            for name in [
                "babbage",
                "dall-e",
                "davinci",
                "embedding",
                "tts",
                "whisper",
            ]
        ):
            return False
        return True

    def get_merged_models(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        models = {}

        for idx, model_list in enumerate(model_lists):
            if model_list is not None and "error" not in model_list:
                for model in model_list:
                    model_id = model.get("id") or model.get("name")

                    if (
                        "api.openai.com"
                        in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                        and not is_supported_openai_models(model_id)
                    ):
                        # Skip unwanted OpenAI models
                        continue

                    if model_id and model_id not in models:
                        models[model_id] = {
                            **model,
                            "name": model.get("name", model_id),
                            "owned_by": "openai",
                            "openai": model,
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }

        return models

    models = get_merged_models(map(extract_data, responses))
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = models
    return {"data": list(models.values())}


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = request.app.state.config.OPENAI_API_KEYS[url_idx]

        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(url_idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        r = None
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                headers, cookies = await get_headers_and_cookies(
                    request, url, key, api_config, user=user
                )

                if api_config.get("azure", False):
                    models = {
                        "data": api_config.get("model_ids", []) or [],
                        "object": "list",
                    }
                else:
                    async with session.get(
                        f"{url}/models",
                        headers=headers,
                        cookies=cookies,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as r:
                        response_data = await _safe_response_json(r)
                        if r.status != 200:
                            # Extract response error details if available
                            error_detail = f"HTTP Error: {r.status}"
                            if isinstance(response_data, dict) and "error" in response_data:
                                error_detail = f"External Error: {response_data['error']}"
                            raise Exception(error_detail)

                        if response_data is None:
                            raise Exception("Invalid JSON response from model list endpoint")

                        # Check if we're calling OpenAI API based on the URL
                        if "api.openai.com" in url:
                            # Filter models according to the specified conditions
                            response_data["data"] = [
                                model
                                for model in response_data.get("data", [])
                                if not any(
                                    name in model["id"]
                                    for name in [
                                        "babbage",
                                        "dall-e",
                                        "davinci",
                                        "embedding",
                                        "tts",
                                        "whisper",
                                    ]
                                )
                            ]

                        models = response_data
            except aiohttp.ClientError as e:
                # ClientError covers all aiohttp requests issues
                log.exception(f"Client error: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Open WebUI: Server Connection Error"
                )
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                error_detail = f"Unexpected error: {str(e)}"
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str

    config: Optional[dict] = None


@router.post("/verify")
async def verify_connection(
    request: Request,
    form_data: ConnectionVerificationForm,
    user=Depends(get_admin_user),
):
    url = form_data.url
    key = form_data.key

    api_config = form_data.config or {}

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            headers, cookies = await get_headers_and_cookies(
                request, url, key, api_config, user=user
            )

            if api_config.get("azure", False):
                # Only set api-key header if not using Azure Entra ID authentication
                auth_type = api_config.get("auth_type", "bearer")
                if auth_type not in ("azure_ad", "microsoft_entra_id"):
                    headers["api-key"] = key

                api_version = api_config.get("api_version", "") or "2023-03-15-preview"
                async with session.get(
                    url=f"{url}/openai/models?api-version={api_version}",
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    try:
                        response_data = await r.json()
                    except Exception:
                        response_data = await r.text()

                    if r.status != 200:
                        if isinstance(response_data, (dict, list)):
                            return JSONResponse(
                                status_code=r.status, content=response_data
                            )
                        else:
                            return PlainTextResponse(
                                status_code=r.status, content=response_data
                            )

                    return response_data
            else:
                async with session.get(
                    f"{url}/models",
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    try:
                        response_data = await r.json()
                    except Exception:
                        response_data = await r.text()

                    if r.status != 200:
                        if isinstance(response_data, (dict, list)):
                            return JSONResponse(
                                status_code=r.status, content=response_data
                            )
                        else:
                            return PlainTextResponse(
                                status_code=r.status, content=response_data
                            )

                    return response_data

        except aiohttp.ClientError as e:
            # ClientError covers all aiohttp requests issues
            log.exception(f"Client error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )


def get_azure_allowed_params(api_version: str) -> set[str]:
    allowed_params = {
        "messages",
        "temperature",
        "role",
        "content",
        "contentPart",
        "contentPartImage",
        "enhancements",
        "dataSources",
        "n",
        "stream",
        "stop",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "user",
        "function_call",
        "functions",
        "tools",
        "tool_choice",
        "top_p",
        "log_probs",
        "top_logprobs",
        "response_format",
        "seed",
        "max_completion_tokens",
        "reasoning_effort",
    }

    try:
        if api_version >= "2024-09-01-preview":
            allowed_params.add("stream_options")
    except ValueError:
        log.debug(
            f"Invalid API version {api_version} for Azure OpenAI. Defaulting to allowed parameters."
        )

    return allowed_params


def is_openai_reasoning_model(model: str) -> bool:
    return model.lower().startswith(("o1", "o3", "o4", "gpt-5"))


def convert_to_azure_payload(url, payload: dict, api_version: str):
    model = payload.get("model", "")

    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = get_azure_allowed_params(api_version)

    # Special handling for o-series models
    if is_openai_reasoning_model(model):
        # Convert max_tokens to max_completion_tokens for o-series models
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]

        # Remove temperature if not 1 for o-series models
        if "temperature" in payload and payload["temperature"] != 1:
            log.debug(
                f"Removing temperature parameter for o-series model {model} as only default value (1) is supported"
            )
            del payload["temperature"]

    # Filter out unsupported parameters
    payload = {k: v for k, v in payload.items() if k in allowed_params}

    url = f"{url}/openai/deployments/{model}"
    return url, payload


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
    bypass_system_prompt: bool = False,
    db: Session = Depends(get_session),
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id, db=db)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            base_model_id = (
                request.base_model_id
                if hasattr(request, "base_model_id")
                else model_info.base_model_id
            )  # Use request's base_model_id if available
            payload["model"] = base_model_id
            model_id = base_model_id

        params = model_info.params.model_dump()

        if params:
            system = params.pop("system", None)

            payload = apply_model_params_to_body_openai(params, payload)
            if not bypass_system_prompt:
                payload = apply_system_prompt_to_body(system, payload, metadata, user)

        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id,
                    type="read",
                    access_control=model_info.access_control,
                    db=db,
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    await get_all_models(request, user=user)
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # Add user info to the payload if the model is a pipeline
    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Check if model is a reasoning model that needs special handling
    if is_openai_reasoning_model(payload["model"]):
        payload = openai_reasoning_model_handler(payload)
    elif "api.openai.com" not in url:
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    if "max_tokens" in payload and "max_completion_tokens" in payload:
        del payload["max_tokens"]

    # Convert the modified body back to JSON
    if "logit_bias" in payload and payload["logit_bias"]:
        logit_bias = convert_logit_bias_input_to_json(payload["logit_bias"])

        if logit_bias:
            payload["logit_bias"] = json.loads(logit_bias)

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, metadata, user=user
    )

    # Initialize Responses API flag (only applicable to non-Azure connections)
    use_responses_api = False

    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        request_url, payload = convert_to_azure_payload(url, payload, api_version)

        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get("auth_type", "bearer")
        if auth_type not in ("azure_ad", "microsoft_entra_id"):
            headers["api-key"] = key

        headers["api-version"] = api_version
        request_url = f"{request_url}/chat/completions?api-version={api_version}"
    else:
        # Check if Responses API is enabled for this connection
        use_responses_api = api_config.get("use_responses_api", False)
        if use_responses_api:
            request_url = f"{url}/responses"
            # Convert Chat Completions format to Responses API format
            payload = convert_to_responses_payload(payload)
            log.info(f"Using Responses API for model {model_id}")

            # WORKAROUND: Force streaming when using Responses API with native functions in non-streaming mode
            # to prevent infinite tool call loops where the model never returns final content
            has_tools = "tools" in payload or "tool_choice" in payload
            is_streaming = payload.get("stream", False)
            if has_tools and not is_streaming:
                log.warning(f"[RESPONSES API] Detected native functions with stream=False. Forcing stream=True to prevent infinite tool call loops.")
                payload["stream"] = True
        else:
            request_url = f"{url}/chat/completions"

    # Force stream=False for image generation models to prevent "Chunk too big" errors
    # These models return large base64 image data that can't be streamed properly
    image_edit_keywords = ["image-preview", "image-edit", "imagen"]
    image_gen_keywords = ["image", "draw", "paint", "picture", "art", "create-preview"]
    is_image_edit_model = any(keyword in model_id.lower() for keyword in image_edit_keywords)
    is_image_gen_model = any(keyword in model_id.lower() for keyword in image_gen_keywords)
    
    if is_image_gen_model:
        log.info(f"Detected image generation model in OpenAI router: {model_id}, forcing stream=False")
        payload["stream"] = False
    
    # For image editing models, only use the last user message to save tokens
    # Image editing is a single-shot operation that doesn't need conversation history
    if is_image_edit_model and "messages" in payload:
        original_count = len(payload.get("messages", []))
        messages = payload["messages"]
        
        # Extract system message if present
        system_msg = None
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg
                break
        
        # Helper function to check if a message contains an image
        # Supports both OpenAI format {"type": "image_url"} and Markdown format ![...](data:image/...)
        import re
        markdown_image_pattern = re.compile(r'!\[.*?\]\((data:image/[^;]+;base64,[A-Za-z0-9+/=]+)\)')
        
        def has_image(msg):
            content = msg.get("content", "")
            # Check OpenAI multimodal format
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") in ["image_url", "image"]:
                            return True
            # Check for Markdown embedded base64 image in string content
            if isinstance(content, str):
                if markdown_image_pattern.search(content):
                    return True
            return False
            
        # Helper function to extract images from a message
        # Converts Markdown images to OpenAI format for consistency
        def extract_images(msg):
            images = []
            content = msg.get("content", "")
            # Extract from OpenAI multimodal format
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") in ["image_url", "image"]:
                        images.append(item)
            # Extract from Markdown format and convert to OpenAI format
            if isinstance(content, str):
                matches = markdown_image_pattern.findall(content)
                for data_url in matches:
                    images.append({
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    })
            return images
        
        # Helper function to extract text from a message
        def extract_text(msg):
            content = msg.get("content", "")
            if isinstance(content, str):
                # Remove Markdown image syntax from text
                text = markdown_image_pattern.sub('', content).strip()
                return text if text else content
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        texts.append(item)
                return " ".join(texts)
            return ""

        # DEBUG LOGGING: Print structure of last few messages to understand why image is not found
        log.info(f"DEBUG: Scanning {len(messages)} messages for images. Dumping structure:")
        for i, msg in enumerate(reversed(messages)):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            content_type = type(content).__name__
            content_preview = "..."
            if isinstance(content, list):
                content_preview = str([
                    {k: v for k, v in item.items() if k != 'image_url'} 
                    if isinstance(item, dict) else str(item)[:50] 
                    for item in content
                ])
            elif isinstance(content, str):
                content_preview = content[:100]
            
            log.info(f"DEBUG Msg {len(messages)-1-i} [{role}]: type={content_type}, content={content_preview}")
            if i >= 4: # Only check last 5 messages to avoid log spam
                break

        # Find the last message with an image (from ANY role: user or assistant)
        last_image_msg = None
        last_image_index = -1
        for i, msg in enumerate(reversed(messages)):
            if has_image(msg):
                last_image_msg = msg
                last_image_index = len(messages) - 1 - i
                log.info(f"Found image in message {last_image_index} (Role: {msg.get('role')})")
                break
        
        # Find the last user message (the edit instruction)
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg
                break
        
        # CRITICAL FIX: Only modify messages if we actually found what we need
        if last_image_msg and last_user_msg:
            # Build the combined message
            if last_image_msg != last_user_msg:
                # Image and instruction are in different messages - merge them
                images = extract_images(last_image_msg)
                instruction_text = extract_text(last_user_msg)
                
                # Create combined content: images + instruction text
                combined_content = images + [{"type": "text", "text": instruction_text}]
                combined_msg = {"role": "user", "content": combined_content}
                
                new_messages = [combined_msg]
                log.info(f"Image edit mode: Merged image from msg {last_image_index} with instruction from last user msg")
            else:
                # Last message already contains the image, use it directly
                new_messages = [last_user_msg]
                log.info("Image edit mode: Last user message already contains the image")
            
            if system_msg:
                new_messages.insert(0, system_msg)
            
            payload["messages"] = new_messages
            log.info(f"Image edit mode: Trimmed messages from {original_count} to {len(new_messages)} to save tokens")
        else:
            log.warning(f"Image edit mode: Aborted optimization. Found Image: {bool(last_image_msg)}, Found User Msg: {bool(last_user_msg)}. Sending original messages.")

    # Force add stream_options if streaming is enabled to always get usage data
    # NOTE: Responses API does not support stream_options, it includes usage in response.completed event
    if payload.get("stream", False) and "stream_options" not in payload and not use_responses_api:
        payload["stream_options"] = {"include_usage": True}
        log.info(f"[DEBUG] Forced stream_options: {payload['stream_options']}")
    elif "stream_options" in payload:
        if use_responses_api:
            # Remove stream_options for Responses API as it's not supported
            del payload["stream_options"]
            log.info("[DEBUG] Removed stream_options for Responses API (not supported)")
        else:
            log.info(f"[DEBUG] stream_options in payload: {payload.get('stream_options')}")

    # Save original payload for potential retry without tools
    payload_dict = payload.copy()
    has_tools = "tools" in payload_dict or "tool_choice" in payload_dict
    
    payload = json.dumps(payload_dict)



    r = None
    session = None
    streaming = False
    response = None
    retry_without_tools = False

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.request(
            method="POST",
            url=request_url,
            data=payload,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is an error first (even for SSE responses)
        # Some upstream APIs return error status codes with non-SSE content types
        if r.status >= 400:
            try:
                response = await r.json()
            except Exception as e:
                log.error(f"Error parsing error response: {e}")
                response = await r.text()
            
            # Check if this is a "tool calling disabled" error and we can retry
            if has_tools and is_tool_calling_disabled_error(response):
                log.info("Tool calling disabled by API, retrying without tools...")
                retry_without_tools = True
                await cleanup_response(r, session)
                
                # Remove tools and retry
                payload_dict.pop("tools", None)
                payload_dict.pop("tool_choice", None)
                retry_payload = json.dumps(payload_dict)
                
                session = aiohttp.ClientSession(
                    trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
                )
                r = await session.request(
                    method="POST",
                    url=request_url,
                    data=retry_payload,
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                )
                
                # Check retry result
                if r.status >= 400:
                    try:
                        response = await r.json()
                    except Exception as e:
                        log.error(f"Error parsing retry error response: {e}")
                        response = await r.text()
                    
                    await cleanup_response(r, session)
                    
                    if form_data.get("stream"):
                        error_msg = f"HTTP Error {r.status}"
                        if isinstance(response, dict) and "error" in response:
                            err = response["error"]
                            if isinstance(err, dict):
                                error_msg = f"{err.get('message', str(err))} (Code: {r.status})"
                            else:
                                error_msg = f"{str(err)} (Code: {r.status})"
                        elif isinstance(response, str):
                            error_msg = f"{response} (Code: {r.status})"
                        
                        return StreamingResponse(
                            error_stream_generator(model_id, error_msg),
                            media_type="text/event-stream"
                        )
                    
                    if isinstance(response, (dict, list)):
                        return JSONResponse(status_code=r.status, content=response)
                    else:
                        return PlainTextResponse(status_code=r.status, content=response)
            else:
                # Not a tool calling error or no tools in payload, handle normally
                await cleanup_response(r, session)
                
                # IMPROVEMENT: Stream error to frontend if streaming was requested
                # This ensures the error is visible in the chat UI instead of a generic failure
                if form_data.get("stream"):
                    error_msg = f"HTTP Error {r.status}"
                    if isinstance(response, dict) and "error" in response:
                        # Extract message from OpenAI error format
                         err = response["error"]
                         if isinstance(err, dict):
                             error_msg = f"{err.get('message', str(err))} (Code: {r.status})"
                         else:
                             error_msg = f"{str(err)} (Code: {r.status})"
                    elif isinstance(response, str):
                         error_msg = f"{response} (Code: {r.status})"
                    
                    return StreamingResponse(
                        error_stream_generator(model_id, error_msg),
                        media_type="text/event-stream"
                    )

                # Fallback to standard JSON/Text response for non-stream requests
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

        # Log response info for debugging
        content_type = r.headers.get("Content-Type", "")
        log.info(f"[DEBUG] Response status={r.status}, Content-Type={content_type}, stream_requested={form_data.get('stream', False)}")

        # Check if response is SSE
        if "text/event-stream" in content_type:
            streaming = True
            log.info(f"[DEBUG] Streaming response detected, use_responses_api={use_responses_api}")

            # Use Responses API stream converter if enabled
            if use_responses_api:
                return StreamingResponse(
                    responses_stream_to_chat_completions_stream(r, model_id),
                    status_code=r.status,
                    headers={"Content-Type": "text/event-stream"},
                    background=BackgroundTask(
                        cleanup_response, response=r, session=session
                    ),
                )
            else:
                return StreamingResponse(
                    stream_chunks_handler(HeartbeatStreamWrapper(r.content)),
                    status_code=r.status,
                    headers=dict(r.headers),
                    background=BackgroundTask(
                        cleanup_response, response=r, session=session
                    ),
                )
        else:
            # Non-streaming response (JSON)
            log.info(f"[DEBUG] Non-streaming response, attempting to parse JSON")
            try:
                response = await r.json()
                log.info(f"[DEBUG] JSON response parsed, keys={list(response.keys()) if isinstance(response, dict) else 'not a dict'}")
                # DEBUG: Log full choices structure to see where content actually is
                if isinstance(response, dict) and "choices" in response:
                    choices = response.get("choices", [])
                    if choices and len(choices) > 0:
                        import json as json_mod
                        log.info(f"[DEBUG] choices[0] FULL: {json_mod.dumps(choices[0], ensure_ascii=False, default=str)[:1000]}")
            except Exception as e:
                log.error(e)
                response = await r.text()
                log.info(f"[DEBUG] Fallback to text response, length={len(response)}")

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            # Convert Responses API format to Chat Completions format if needed
            if use_responses_api and isinstance(response, dict):
                response = convert_responses_to_chat_completions(response, model_id)
            if isinstance(response, dict):
                response = _normalize_chat_completion_response(response)

            # IMPORTANT: If stream was requested but API returned JSON (not SSE),
            # we need to convert it to SSE format for the frontend to handle correctly
            if form_data.get("stream") and isinstance(response, dict):
                log.warning(f"[DEBUG] Stream requested but got JSON response, converting to SSE format")
                streaming = True  # Mark as streaming to prevent double cleanup

                async def json_to_sse_stream():
                    """Convert a JSON chat completion response to SSE stream format."""
                    # Send the response as a single chunk
                    yield f"data: {json.dumps(response)}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(
                    json_to_sse_stream(),
                    status_code=r.status,
                    headers={"Content-Type": "text/event-stream"},
                    background=BackgroundTask(
                        cleanup_response, response=r, session=session
                    ),
                )

            return response
    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


async def embeddings(request: Request, form_data: dict, user):
    """
    Calls the embeddings endpoint for OpenAI-compatible providers.

    Args:
        request (Request): The FastAPI request context.
        form_data (dict): OpenAI-compatible embeddings payload.
        user (UserModel): The authenticated user.

    Returns:
        dict: OpenAI-compatible embeddings response.
    """
    idx = 0
    # Prepare payload/body
    body = json.dumps(form_data)
    # Find correct backend url/key based on model
    await get_all_models(request, user=user)
    model_id = form_data.get("model")
    models = request.app.state.OPENAI_MODELS
    if model_id in models:
        idx = models[model_id]["urlIdx"]

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, user=user
    )
    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method="POST",
            url=f"{url}/embeddings",
            data=body,
            headers=headers,
            cookies=cookies,
        )

        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(
                        status_code=r.status, content=response_data
                    )

            return response_data
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Deprecated: proxy all requests to OpenAI API
    """

    body = await request.body()

    idx = 0
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    try:
        headers, cookies = await get_headers_and_cookies(
            request, url, key, api_config, user=user
        )

        if api_config.get("azure", False):
            api_version = api_config.get("api_version", "2023-03-15-preview")

            # Only set api-key header if not using Azure Entra ID authentication
            auth_type = api_config.get("auth_type", "bearer")
            if auth_type not in ("azure_ad", "microsoft_entra_id"):
                headers["api-key"] = key

            headers["api-version"] = api_version

            payload = json.loads(body)
            url, payload = convert_to_azure_payload(url, payload, api_version)
            body = json.dumps(payload).encode()

            request_url = f"{url}/{path}?api-version={api_version}"
        else:
            request_url = f"{url}/{path}"

        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=request_url,
            data=body,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(
                        status_code=r.status, content=response_data
                    )

            return response_data

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)

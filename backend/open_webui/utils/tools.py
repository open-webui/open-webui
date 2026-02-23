import inspect
import logging
import re
import inspect
import aiohttp
import asyncio
import yaml
import json
import copy

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing import (
    Any,
    Awaitable,
    Callable,
    get_type_hints,
    get_args,
    get_origin,
    Dict,
    List,
    Tuple,
    Union,
    Optional,
    Type,
)
from functools import update_wrapper, partial


from fastapi import Request
from pydantic import BaseModel, Field, create_model
from starlette.responses import Response

from langchain_core.utils.function_calling import (
    convert_to_openai_function as convert_pydantic_model_to_openai_function_spec,
)


from open_webui.utils.misc import is_string_allowed
from open_webui.models.tools import Tools
from open_webui.models.models import Models
from open_webui.models.users import UserModel
from open_webui.models.groups import Groups
from open_webui.models.access_grants import AccessGrants
from open_webui.utils.plugin import load_tool_module_by_id
from open_webui.utils.access_control import has_access
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA,
    AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    FORWARD_SESSION_INFO_HEADER_CHAT_ID,
    FORWARD_SESSION_INFO_HEADER_MESSAGE_ID,
)
from open_webui.utils.headers import include_user_info_headers
from open_webui.tools.builtin import (
    search_web,
    fetch_url,
    generate_image,
    edit_image,
    execute_code,
    search_memories,
    add_memory,
    replace_memory_content,
    get_current_timestamp,
    calculate_timestamp,
    search_notes,
    search_chats,
    search_channels,
    search_channel_messages,
    view_note,
    view_chat,
    view_channel_message,
    view_channel_thread,
    replace_note_content,
    write_note,
    list_knowledge_bases,
    search_knowledge_bases,
    query_knowledge_bases,
    search_knowledge_files,
    query_knowledge_files,
    view_file,
    view_knowledge_file,
    view_skill,
)

log = logging.getLogger(__name__)
WORKSPACE_AGENT_TOOL_PREFIX = "agent:"
# Legacy prefix retained for backward compatibility with older saved configs/chats.
LEGACY_WORKSPACE_MODEL_TOOL_PREFIX = "model:"
MAX_WORKSPACE_MODEL_TOOL_DEPTH = 3
AGENT_ORCHESTRATION_PROTOCOL = """You are a spawned sub-agent collaborating with an orchestrator model.
Always respond with either:
1) JSON object:
{
  "message_to_orchestrator": "your concise update or result",
  "recommended_next_instruction": "optional suggestion for what the orchestrator could ask you next"
}
2) Plain text if JSON is not possible.
The orchestrator decides whether your task is complete.
Focus on agent-to-orchestrator communication, not end-user formatting."""


def sanitize_workspace_model_tool_name(model_id: str) -> str:
    sanitized_id = re.sub(r"[^a-zA-Z0-9_]", "_", model_id).strip("_").lower()
    if not sanitized_id:
        sanitized_id = "workspace_model"
    return f"workspace_model_{sanitized_id}"


def extract_workspace_model_tool_result(response_payload: dict | list | str) -> str:
    if isinstance(response_payload, str):
        return response_payload

    if isinstance(response_payload, dict):
        choices = response_payload.get("choices", [])
        if choices and isinstance(choices, list):
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(
                    [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict)
                        and item.get("type") in ("text", "output_text")
                    ]
                )
            return str(content)

        output = response_payload.get("output", [])
        if output and isinstance(output, list):
            chunks = []
            for item in output:
                if item.get("type") != "message":
                    continue
                for content_item in item.get("content", []):
                    if content_item.get("type") in ("output_text", "text"):
                        chunks.append(content_item.get("text", ""))
            if chunks:
                return "\n".join(chunks)

        if "response" in response_payload and isinstance(response_payload["response"], str):
            return response_payload["response"]

    try:
        return json.dumps(response_payload, ensure_ascii=False)
    except Exception:
        return str(response_payload)


def extract_workspace_model_tool_sources(
    response_payload: dict | list | str,
) -> list[dict]:
    if not isinstance(response_payload, dict):
        return []

    sources = response_payload.get("sources") or response_payload.get("citations") or []
    if not isinstance(sources, list):
        return []

    normalized_sources = []
    for source in sources:
        if not isinstance(source, dict):
            continue

        source_obj = source.get("source", {}) if isinstance(source.get("source"), dict) else {}
        source_name = source_obj.get("name", "")
        if isinstance(source_name, str) and source_name.startswith("agent:"):
            # Avoid turning agent labels into inline citation source names.
            continue

        normalized_sources.append(source)

    return normalized_sources


def extract_workspace_model_tool_annotations(
    response_payload: dict | list | str,
) -> list[dict]:
    if not isinstance(response_payload, dict):
        return []

    annotations: list[dict] = []

    choices = response_payload.get("choices", [])
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        message_annotations = message.get("annotations", [])
        if isinstance(message_annotations, list):
            annotations.extend(
                [annotation for annotation in message_annotations if isinstance(annotation, dict)]
            )

    output = response_payload.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            for content_item in item.get("content", []):
                if not isinstance(content_item, dict):
                    continue
                content_annotations = content_item.get("annotations", [])
                if isinstance(content_annotations, list):
                    annotations.extend(
                        [annotation for annotation in content_annotations if isinstance(annotation, dict)]
                    )

    return annotations


def parse_response_to_payload(response: Any) -> dict | list | str:
    if isinstance(response, Response):
        body = response.body.decode("utf-8") if response.body else ""
        if response.status_code >= 400:
            detail = body
            try:
                parsed_error = json.loads(body) if body else {}
                detail = parsed_error.get("detail", body)
            except Exception:
                pass
            raise Exception(detail or "Failed to call workspace model tool")

        if body:
            try:
                return json.loads(body)
            except Exception:
                return body
        return ""

    return response


def extract_model_description(target_model: dict, target_model_id: str) -> str:
    info = target_model.get("info", {}) if isinstance(target_model, dict) else {}
    meta = info.get("meta", {}) if isinstance(info, dict) else {}

    for value in [
        meta.get("description"),
        info.get("description") if isinstance(info, dict) else None,
        target_model.get("description")
        if isinstance(target_model, dict)
        else None,
    ]:
        if isinstance(value, str) and value.strip():
            return value.strip()

    return f"Workspace model {target_model_id}"


def get_target_model_tool_ids(target_model: dict, target_model_id: str) -> list[str]:
    info = target_model.get("info", {}) if isinstance(target_model, dict) else {}
    meta = info.get("meta", {}) if isinstance(info, dict) else {}

    raw_tool_ids = meta.get("toolIds") or meta.get("tool_ids") or []
    raw_agent_ids = meta.get("agentIds") or meta.get("agent_ids") or []

    tool_ids: list[str] = []
    for item in [*raw_tool_ids, *raw_agent_ids]:
        if not isinstance(item, str) or not item.strip():
            continue
        normalized_item = item
        if item.startswith(LEGACY_WORKSPACE_MODEL_TOOL_PREFIX):
            normalized_item = (
                f"{WORKSPACE_AGENT_TOOL_PREFIX}{item[len(LEGACY_WORKSPACE_MODEL_TOOL_PREFIX):]}"
            )

        if normalized_item == f"{WORKSPACE_AGENT_TOOL_PREFIX}{target_model_id}":
            # Prevent direct self-recursion by tool selection.
            continue
        tool_ids.append(normalized_item)

    return list(dict.fromkeys(tool_ids))


def parse_agent_channel_response(response_text: str) -> tuple[str, str, str]:
    """
    Returns (status_suggestion, message_to_orchestrator, recommended_next_instruction).
    """
    status_suggestion = ""
    message_to_orchestrator = response_text.strip()
    recommended_next_instruction = ""

    if not response_text:
        return status_suggestion, message_to_orchestrator, recommended_next_instruction

    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, dict):
            parsed_status = str(parsed.get("status", "")).strip().lower()
            if parsed_status in ("needs_more_input", "completed"):
                status_suggestion = parsed_status

            msg = parsed.get("message_to_orchestrator")
            if isinstance(msg, str) and msg.strip():
                message_to_orchestrator = msg.strip()

            next_request = (
                parsed.get("recommended_next_instruction")
                or parsed.get("next_instruction_request")
            )
            if isinstance(next_request, str):
                recommended_next_instruction = next_request.strip()
    except Exception:
        pass

    return status_suggestion, message_to_orchestrator, recommended_next_instruction


async def call_workspace_model_tool(
    request: Request,
    user: UserModel,
    target_model_id: str,
    target_model: dict,
    prompt: str,
    context: str | None = None,
    system: str | None = None,
    metadata: Optional[dict] = None,
) -> str:
    from open_webui.functions import (
        generate_function_chat_completion as generate_function_model_chat_completion,
    )
    from open_webui.routers.openai import (
        generate_chat_completion as generate_openai_chat_completion,
    )
    from open_webui.routers.ollama import (
        generate_chat_completion as generate_ollama_chat_completion,
    )

    if not prompt or not isinstance(prompt, str):
        raise Exception("'prompt' must be a non-empty string")

    call_depth = int((metadata or {}).get("model_tool_depth", 0))
    if call_depth >= MAX_WORKSPACE_MODEL_TOOL_DEPTH:
        raise Exception("Maximum workspace model tool call depth reached")

    agent_name = target_model.get("name", target_model_id)
    agent_description = extract_model_description(target_model, target_model_id)
    protocol_system_prompt = (
        f"{AGENT_ORCHESTRATION_PROTOCOL}\n\n"
        f"Agent Name: {agent_name}\n"
        f"Agent Description: {agent_description}"
    )

    messages: list[dict] = []
    if system:
        messages.append(
            {
                "role": "system",
                "content": f"{system.rstrip()}\n\n{protocol_system_prompt}",
            }
        )
    else:
        messages.append({"role": "system", "content": protocol_system_prompt})

    user_content = prompt if not context else f"{context}\n\n{prompt}"
    messages.append({"role": "user", "content": user_content})

    nested_tool_ids = get_target_model_tool_ids(target_model, target_model_id)
    parent_features = (metadata or {}).get("features", {})

    nested_form_data = {
        "model": target_model_id,
        "messages": messages,
        "stream": False,
        "tool_ids": nested_tool_ids,
        "features": parent_features if isinstance(parent_features, dict) else {},
        "metadata": {
            "model_tool_call": True,
            "model_tool_depth": call_depth + 1,
            "user_id": user.id,
        },
        "params": {"function_calling": "default"},
    }

    if target_model.get("pipe"):
        response = await generate_function_model_chat_completion(
            request, nested_form_data, user=user, models=request.app.state.MODELS
        )
    elif target_model.get("owned_by") == "ollama":
        response = await generate_ollama_chat_completion(
            request=request,
            form_data=nested_form_data,
            user=user,
            bypass_filter=False,
            bypass_system_prompt=False,
        )
    else:
        response = await generate_openai_chat_completion(
            request=request,
            form_data=nested_form_data,
            user=user,
            bypass_filter=False,
            bypass_system_prompt=False,
        )

    response_payload = parse_response_to_payload(response)
    response_text = extract_workspace_model_tool_result(response_payload).strip()
    response_sources = extract_workspace_model_tool_sources(response_payload)
    response_annotations = extract_workspace_model_tool_annotations(response_payload)
    (
        agent_status_suggestion,
        message_to_orchestrator,
        recommended_next_instruction,
    ) = parse_agent_channel_response(response_text)

    # Include explicit provenance so the parent model can attribute information to the spawned agent.
    result = (
        f"[Agent Channel]\n"
        f"agent_name: {agent_name}\n"
        f"agent_model_id: {target_model_id}\n"
        f"orchestrator_decides_completion: true\n"
        f"agent_status_suggestion: {agent_status_suggestion}\n"
        f"message_to_orchestrator:\n{message_to_orchestrator}\n"
        f"recommended_next_instruction:\n{recommended_next_instruction}\n"
        f"raw_agent_response:\n{response_text}"
    )

    if response_sources:
        result = (
            f"{result}\n"
            f"[Agent Sources JSON]\n"
            f"{json.dumps(response_sources, ensure_ascii=False)}"
        )

    if response_annotations:
        result = (
            f"{result}\n"
            f"[Agent Annotations JSON]\n"
            f"{json.dumps(response_annotations, ensure_ascii=False)}"
        )

    return result


def get_async_tool_function_and_apply_extra_params(
    function: Callable, extra_params: dict
) -> Callable[..., Awaitable]:
    sig = inspect.signature(function)
    extra_params = {k: v for k, v in extra_params.items() if k in sig.parameters}
    partial_func = partial(function, **extra_params)

    # Remove the 'frozen' keyword arguments from the signature
    # python-genai uses the signature to infer the tool properties for native function calling
    parameters = []
    for name, parameter in sig.parameters.items():
        # Exclude keyword arguments that are frozen
        if name in extra_params:
            continue
        # Keep remaining parameters
        parameters.append(parameter)

    new_sig = inspect.Signature(
        parameters=parameters, return_annotation=sig.return_annotation
    )

    if inspect.iscoroutinefunction(function):
        # wrap the functools.partial as python-genai has trouble with it
        # https://github.com/googleapis/python-genai/issues/907
        async def new_function(*args, **kwargs):
            return await partial_func(*args, **kwargs)

    else:
        # Make it a coroutine function when it is not already
        async def new_function(*args, **kwargs):
            return partial_func(*args, **kwargs)

    update_wrapper(new_function, function)
    new_function.__signature__ = new_sig

    new_function.__function__ = function  # type: ignore
    new_function.__extra_params__ = extra_params  # type: ignore

    return new_function


def get_updated_tool_function(function: Callable, extra_params: dict):
    # Get the original function and merge updated params
    __function__ = getattr(function, "__function__", None)
    __extra_params__ = getattr(function, "__extra_params__", None)

    if __function__ is not None and __extra_params__ is not None:
        return get_async_tool_function_and_apply_extra_params(
            __function__,
            {**__extra_params__, **extra_params},
        )

    return function


def has_tool_server_access(
    user: UserModel, server_connection: dict, user_group_ids: set = None
) -> bool:
    """Check if user has access to a tool server (MCP or OpenAPI)."""
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        return True

    if user_group_ids is None:
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}

    server_config = server_connection.get("config", {})
    access_grants = server_config.get("access_grants", [])
    return has_access(user.id, "read", access_grants, user_group_ids)


async def get_tools(
    request: Request, tool_ids: list[str], user: UserModel, extra_params: dict
) -> dict[str, dict]:
    """Load tools for the given tool_ids, checking access control."""
    tools_dict = {}

    # Get user's group memberships for access control checks
    user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user.id)}

    for tool_id in tool_ids:
        if tool_id.startswith(WORKSPACE_AGENT_TOOL_PREFIX) or tool_id.startswith(
            LEGACY_WORKSPACE_MODEL_TOOL_PREFIX
        ):
            if tool_id.startswith(WORKSPACE_AGENT_TOOL_PREFIX):
                target_model_id = tool_id[len(WORKSPACE_AGENT_TOOL_PREFIX) :]
            else:
                target_model_id = tool_id[len(LEGACY_WORKSPACE_MODEL_TOOL_PREFIX) :]
            target_model_info = Models.get_model_by_id(target_model_id)

            if not target_model_info:
                log.warning(f"Workspace model tool target not found: {target_model_id}")
                continue

            target_model = request.app.state.MODELS.get(target_model_id)
            if not target_model:
                base_model = request.app.state.MODELS.get(target_model_info.base_model_id)
                if not base_model:
                    log.warning(
                        f"Workspace agent target base model not found: {target_model_info.base_model_id}"
                    )
                    continue

                target_model = {
                    "id": target_model_info.id,
                    "name": target_model_info.name,
                    "info": target_model_info.model_dump(),
                    "pipe": base_model.get("pipe"),
                    "owned_by": base_model.get("owned_by"),
                }

            if target_model_info.base_model_id is None:
                log.warning(
                    f"Model {target_model_id} is not a workspace model tool target"
                )
                continue

            if getattr(target_model_info, "kind", "model") != "agent":
                log.warning(f"Model {target_model_id} is not an agent")
                continue

            if (
                not (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                and target_model_info.user_id != user.id
                and not AccessGrants.has_access(
                    user_id=user.id,
                    resource_type="model",
                    resource_id=target_model_id,
                    permission="read",
                    user_group_ids=user_group_ids,
                )
            ):
                log.warning(
                    f"Access denied to workspace model tool {target_model_id} for user {user.id}"
                )
                continue

            function_name = sanitize_workspace_model_tool_name(target_model_id)
            spec = {
                "name": function_name,
                "description": (
                    f"Spawn and message workspace agent '{target_model.get('name', target_model_id)}'. "
                    "Use repeated calls for back-and-forth coordination until status is completed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Instruction/message to send to the spawned agent.",
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional prior agent/orchestrator context for continued back-and-forth.",
                        },
                        "system": {
                            "type": "string",
                            "description": "Optional system prompt for this model call.",
                        },
                    },
                    "required": ["prompt"],
                },
            }

            async def workspace_model_tool_function(
                prompt: str,
                context: str | None = None,
                system: str | None = None,
                __target_model_id__: str = target_model_id,
                __target_model__: dict = target_model,
            ):
                return await call_workspace_model_tool(
                    request=request,
                    user=user,
                    target_model_id=__target_model_id__,
                    target_model=__target_model__,
                    prompt=prompt,
                    context=context,
                    system=system,
                    metadata=extra_params.get("__metadata__", {}),
                )

            callable = get_async_tool_function_and_apply_extra_params(
                workspace_model_tool_function,
                {},
            )

            tool_dict = {
                "tool_id": f"{WORKSPACE_AGENT_TOOL_PREFIX}{target_model_id}",
                "callable": callable,
                "spec": spec,
                "type": "workspace_agent",
                "agent_name": target_model.get("name", target_model_id),
                "display_name": f"Spawn Agent: {target_model.get('name', target_model_id)}",
            }

            while function_name in tools_dict:
                log.warning(
                    f"Workspace model tool {function_name} already exists in another tools!"
                )
                function_name = f"{target_model_id}_{function_name}"

            tools_dict[function_name] = tool_dict
            continue

        tool = Tools.get_tool_by_id(tool_id)
        if tool:
            # Check access control for local tools
            if (
                not (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                and tool.user_id != user.id
                and not AccessGrants.has_access(
                    user_id=user.id,
                    resource_type="tool",
                    resource_id=tool.id,
                    permission="read",
                    user_group_ids=user_group_ids,
                )
            ):
                log.warning(f"Access denied to tool {tool_id} for user {user.id}")
                continue

            module = request.app.state.TOOLS.get(tool_id, None)
            if module is None:
                module, _ = load_tool_module_by_id(tool_id)
                request.app.state.TOOLS[tool_id] = module

            __user__ = {
                **extra_params["__user__"],
            }

            # Set valves for the tool
            if hasattr(module, "valves") and hasattr(module, "Valves"):
                valves = Tools.get_tool_valves_by_id(tool_id) or {}
                module.valves = module.Valves(**valves)
            if hasattr(module, "UserValves"):
                __user__["valves"] = module.UserValves(  # type: ignore
                    **Tools.get_user_valves_by_id_and_user_id(tool_id, user.id)
                )

            for spec in tool.specs:
                # TODO: Fix hack for OpenAI API
                # Some times breaks OpenAI but others don't. Leaving the comment
                for val in spec.get("parameters", {}).get("properties", {}).values():
                    if val.get("type") == "str":
                        val["type"] = "string"

                # Remove internal reserved parameters (e.g. __id__, __user__)
                spec["parameters"]["properties"] = {
                    key: val
                    for key, val in spec["parameters"]["properties"].items()
                    if not key.startswith("__")
                }

                # convert to function that takes only model params and inserts custom params
                function_name = spec["name"]
                tool_function = getattr(module, function_name)
                callable = get_async_tool_function_and_apply_extra_params(
                    tool_function,
                    {
                        **extra_params,
                        "__id__": tool_id,
                        "__user__": __user__,
                    },
                )

                # TODO: Support Pydantic models as parameters
                if callable.__doc__ and callable.__doc__.strip() != "":
                    s = re.split(":(param|return)", callable.__doc__, 1)
                    spec["description"] = s[0]
                else:
                    spec["description"] = function_name

                tool_dict = {
                    "tool_id": tool_id,
                    "callable": callable,
                    "spec": spec,
                    # Misc info
                    "metadata": {
                        "file_handler": hasattr(module, "file_handler")
                        and module.file_handler,
                        "citation": hasattr(module, "citation") and module.citation,
                    },
                }

                # Handle function name collisions
                while function_name in tools_dict:
                    log.warning(
                        f"Tool {function_name} already exists in another tools!"
                    )
                    # Prepend tool ID to function name
                    function_name = f"{tool_id}_{function_name}"

                tools_dict[function_name] = tool_dict
        else:
            if tool_id.startswith("server:"):
                splits = tool_id.split(":")

                if len(splits) == 2:
                    type = "openapi"
                    server_id = splits[1]
                elif len(splits) == 3:
                    type = splits[1]
                    server_id = splits[2]

                server_id_splits = server_id.split("|")
                if len(server_id_splits) == 2:
                    server_id = server_id_splits[0]
                    function_names = server_id_splits[1].split(",")

                if type == "openapi":

                    tool_server_data = None
                    for server in await get_tool_servers(request):
                        if server["id"] == server_id:
                            tool_server_data = server
                            break

                    if tool_server_data is None:
                        log.warning(f"Tool server data not found for {server_id}")
                        continue

                    tool_server_idx = tool_server_data.get("idx", 0)
                    tool_server_connection = (
                        request.app.state.config.TOOL_SERVER_CONNECTIONS[
                            tool_server_idx
                        ]
                    )

                    # Check access control for tool server
                    if not has_tool_server_access(
                        user, tool_server_connection, user_group_ids
                    ):
                        log.warning(
                            f"Access denied to tool server {server_id} for user {user.id}"
                        )
                        continue

                    specs = tool_server_data.get("specs", [])
                    function_name_filter_list = tool_server_connection.get(
                        "config", {}
                    ).get("function_name_filter_list", "")

                    if isinstance(function_name_filter_list, str):
                        function_name_filter_list = function_name_filter_list.split(",")

                    for spec in specs:
                        function_name = spec["name"]
                        if function_name_filter_list:
                            if not is_string_allowed(
                                function_name, function_name_filter_list
                            ):
                                # Skip this function
                                continue

                        auth_type = tool_server_connection.get("auth_type", "bearer")

                        cookies = {}
                        headers = {
                            "Content-Type": "application/json",
                        }

                        if auth_type == "bearer":
                            headers["Authorization"] = (
                                f"Bearer {tool_server_connection.get('key', '')}"
                            )
                        elif auth_type == "none":
                            # No authentication
                            pass
                        elif auth_type == "session":
                            cookies = request.cookies
                            headers["Authorization"] = (
                                f"Bearer {request.state.token.credentials}"
                            )
                        elif auth_type == "system_oauth":
                            cookies = request.cookies
                            oauth_token = extra_params.get("__oauth_token__", None)
                            if oauth_token:
                                headers["Authorization"] = (
                                    f"Bearer {oauth_token.get('access_token', '')}"
                                )

                        connection_headers = tool_server_connection.get("headers", None)
                        if connection_headers and isinstance(connection_headers, dict):
                            for key, value in connection_headers.items():
                                headers[key] = value

                        # Add user info headers if enabled
                        if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                            headers = include_user_info_headers(headers, user)
                            metadata = extra_params.get("__metadata__", {})
                            if metadata and metadata.get("chat_id"):
                                headers[FORWARD_SESSION_INFO_HEADER_CHAT_ID] = (
                                    metadata.get("chat_id")
                                )
                            if metadata and metadata.get("message_id"):
                                headers[FORWARD_SESSION_INFO_HEADER_MESSAGE_ID] = (
                                    metadata.get("message_id")
                                )

                        def make_tool_function(
                            function_name, tool_server_data, headers
                        ):
                            async def tool_function(**kwargs):
                                return await execute_tool_server(
                                    url=tool_server_data["url"],
                                    headers=headers,
                                    cookies=cookies,
                                    name=function_name,
                                    params=kwargs,
                                    server_data=tool_server_data,
                                )

                            return tool_function

                        tool_function = make_tool_function(
                            function_name, tool_server_data, headers
                        )

                        callable = get_async_tool_function_and_apply_extra_params(
                            tool_function,
                            {},
                        )

                        tool_dict = {
                            "tool_id": tool_id,
                            "callable": callable,
                            "spec": spec,
                            # Misc info
                            "type": "external",
                        }

                        # Handle function name collisions
                        while function_name in tools_dict:
                            log.warning(
                                f"Tool {function_name} already exists in another tools!"
                            )
                            # Prepend server ID to function name
                            function_name = f"{server_id}_{function_name}"

                        tools_dict[function_name] = tool_dict

                else:
                    continue

    return tools_dict


def get_builtin_tools(
    request: Request, extra_params: dict, features: dict = None, model: dict = None
) -> dict[str, dict]:
    """
    Get built-in tools for native function calling.
    Only returns tools when BOTH the global config is enabled AND the model capability allows it.
    """
    tools_dict = {}
    builtin_functions = []
    features = features or {}
    model = model or {}

    # Helper to get model capabilities (defaults to True if not specified)
    def get_model_capability(name: str, default: bool = True) -> bool:
        return (model.get("info", {}).get("meta", {}).get("capabilities") or {}).get(
            name, default
        )

    # Helper to check if a builtin tool category is enabled via meta.builtinTools
    # Defaults to True if not specified (backward compatible)
    def is_builtin_tool_enabled(category: str) -> bool:
        builtin_tools = model.get("info", {}).get("meta", {}).get("builtinTools", {})
        return builtin_tools.get(category, True)

    # Time utilities - available for date calculations
    if is_builtin_tool_enabled("time"):
        builtin_functions.extend([get_current_timestamp, calculate_timestamp])

    # Knowledge base tools - conditional injection based on model knowledge
    # If model has attached knowledge (any type), only provide query_knowledge_files
    # Otherwise, provide all KB browsing tools
    model_knowledge = model.get("info", {}).get("meta", {}).get("knowledge", [])
    if is_builtin_tool_enabled("knowledge"):
        if model_knowledge:
            # Model has attached knowledge - only allow semantic search within it
            builtin_functions.append(query_knowledge_files)

            knowledge_types = {item.get("type") for item in model_knowledge}
            if "file" in knowledge_types or "collection" in knowledge_types:
                builtin_functions.append(view_file)
            if "note" in knowledge_types:
                builtin_functions.append(view_note)
        else:
            # No model knowledge - allow full KB browsing
            builtin_functions.extend(
                [
                    list_knowledge_bases,
                    search_knowledge_bases,
                    query_knowledge_bases,
                    search_knowledge_files,
                    query_knowledge_files,
                    view_knowledge_file,
                ]
            )

    # Chats tools - search and fetch user's chat history
    if is_builtin_tool_enabled("chats"):
        builtin_functions.extend([search_chats, view_chat])

    # Add memory tools if builtin category enabled AND enabled for this chat
    if is_builtin_tool_enabled("memory") and features.get("memory"):
        builtin_functions.extend([search_memories, add_memory, replace_memory_content])

    # Add web search tools if builtin category enabled AND enabled globally AND model has web_search capability
    if (
        is_builtin_tool_enabled("web_search")
        and getattr(request.app.state.config, "ENABLE_WEB_SEARCH", False)
        and get_model_capability("web_search")
        and features.get("web_search")
    ):
        builtin_functions.extend([search_web, fetch_url])

    # Add image generation/edit tools if builtin category enabled AND enabled globally AND model has image_generation capability
    if (
        is_builtin_tool_enabled("image_generation")
        and getattr(request.app.state.config, "ENABLE_IMAGE_GENERATION", False)
        and get_model_capability("image_generation")
        and features.get("image_generation")
    ):
        builtin_functions.append(generate_image)
    if (
        is_builtin_tool_enabled("image_generation")
        and getattr(request.app.state.config, "ENABLE_IMAGE_EDIT", False)
        and get_model_capability("image_generation")
        and features.get("image_generation")
    ):
        builtin_functions.append(edit_image)

    # Add code interpreter tool if builtin category enabled AND enabled globally AND model has code_interpreter capability
    if (
        is_builtin_tool_enabled("code_interpreter")
        and getattr(request.app.state.config, "ENABLE_CODE_INTERPRETER", True)
        and get_model_capability("code_interpreter")
        and features.get("code_interpreter")
    ):
        builtin_functions.append(execute_code)

    # Notes tools - search, view, create, and update user's notes (if builtin category enabled AND notes enabled globally)
    if is_builtin_tool_enabled("notes") and getattr(
        request.app.state.config, "ENABLE_NOTES", False
    ):
        builtin_functions.extend(
            [search_notes, view_note, write_note, replace_note_content]
        )

    # Channels tools - search channels and messages (if builtin category enabled AND channels enabled globally)
    if is_builtin_tool_enabled("channels") and getattr(
        request.app.state.config, "ENABLE_CHANNELS", False
    ):
        builtin_functions.extend(
            [
                search_channels,
                search_channel_messages,
                view_channel_thread,
                view_channel_message,
            ]
        )

    # Skills tools - view_skill allows model to load full skill instructions on demand
    if extra_params.get("__skill_ids__"):
        builtin_functions.append(view_skill)

    for func in builtin_functions:
        callable = get_async_tool_function_and_apply_extra_params(
            func,
            {
                "__request__": request,
                "__user__": extra_params.get("__user__", {}),
                "__event_emitter__": extra_params.get("__event_emitter__"),
                "__event_call__": extra_params.get("__event_call__"),
                "__metadata__": extra_params.get("__metadata__"),
                "__chat_id__": extra_params.get("__chat_id__"),
                "__message_id__": extra_params.get("__message_id__"),
                "__model_knowledge__": model_knowledge,
            },
        )

        # Generate spec from function
        pydantic_model = convert_function_to_pydantic_model(func)
        spec = convert_pydantic_model_to_openai_function_spec(pydantic_model)

        tools_dict[func.__name__] = {
            "tool_id": f"builtin:{func.__name__}",
            "callable": callable,
            "spec": spec,
            "type": "builtin",
        }

    return tools_dict


def parse_description(docstring: str | None) -> str:
    """
    Parse a function's docstring to extract the description.

    Args:
        docstring (str): The docstring to parse.

    Returns:
        str: The description.
    """

    if not docstring:
        return ""

    lines = [line.strip() for line in docstring.strip().split("\n")]
    description_lines: list[str] = []

    for line in lines:
        if re.match(r":param", line) or re.match(r":return", line):
            break

        description_lines.append(line)

    return "\n".join(description_lines)


def parse_docstring(docstring):
    """
    Parse a function's docstring to extract parameter descriptions in reST format.

    Args:
        docstring (str): The docstring to parse.

    Returns:
        dict: A dictionary where keys are parameter names and values are descriptions.
    """
    if not docstring:
        return {}

    # Regex to match `:param name: description` format
    param_pattern = re.compile(r":param (\w+):\s*(.+)")
    param_descriptions = {}

    for line in docstring.splitlines():
        match = param_pattern.match(line.strip())
        if not match:
            continue
        param_name, param_description = match.groups()
        if param_name.startswith("__"):
            continue
        param_descriptions[param_name] = param_description

    return param_descriptions


def convert_function_to_pydantic_model(func: Callable) -> type[BaseModel]:
    """
    Converts a Python function's type hints and docstring to a Pydantic model,
    including support for nested types, default values, and descriptions.

    Args:
        func: The function whose type hints and docstring should be converted.
        model_name: The name of the generated Pydantic model.

    Returns:
        A Pydantic model class.
    """
    type_hints = get_type_hints(func)
    signature = inspect.signature(func)
    parameters = signature.parameters

    docstring = func.__doc__

    function_description = parse_description(docstring)
    function_param_descriptions = parse_docstring(docstring)

    field_defs = {}
    for name, param in parameters.items():
        type_hint = type_hints.get(name, Any)
        default_value = param.default if param.default is not param.empty else ...

        param_description = function_param_descriptions.get(name, None)

        if param_description:
            field_defs[name] = (
                type_hint,
                Field(default_value, description=param_description),
            )
        else:
            field_defs[name] = type_hint, default_value

    model = create_model(func.__name__, **field_defs)
    model.__doc__ = function_description

    return model


def get_functions_from_tool(tool: object) -> list[Callable]:
    return [
        getattr(tool, func)
        for func in dir(tool)
        if callable(
            getattr(tool, func)
        )  # checks if the attribute is callable (a method or function).
        and not func.startswith(
            "__"
        )  # filters out special (dunder) methods like init, str, etc. — these are usually built-in functions of an object that you might not need to use directly.
        and not inspect.isclass(
            getattr(tool, func)
        )  # ensures that the callable is not a class itself, just a method or function.
    ]


def get_tool_specs(tool_module: object) -> list[dict]:
    function_models = map(
        convert_function_to_pydantic_model, get_functions_from_tool(tool_module)
    )

    specs = [
        convert_pydantic_model_to_openai_function_spec(function_model)
        for function_model in function_models
    ]

    return specs


def resolve_schema(schema, components):
    """
    Recursively resolves a JSON schema using OpenAPI components.
    """
    if not schema:
        return {}

    if "$ref" in schema:
        ref_path = schema["$ref"]
        ref_parts = ref_path.strip("#/").split("/")
        resolved = components
        for part in ref_parts[1:]:  # Skip the initial 'components'
            resolved = resolved.get(part, {})
        return resolve_schema(resolved, components)

    resolved_schema = copy.deepcopy(schema)

    # Recursively resolve inner schemas
    if "properties" in resolved_schema:
        for prop, prop_schema in resolved_schema["properties"].items():
            resolved_schema["properties"][prop] = resolve_schema(
                prop_schema, components
            )

    if "items" in resolved_schema:
        resolved_schema["items"] = resolve_schema(resolved_schema["items"], components)

    return resolved_schema


def convert_openapi_to_tool_payload(openapi_spec):
    """
    Converts an OpenAPI specification into a custom tool payload structure.

    Args:
        openapi_spec (dict): The OpenAPI specification as a Python dict.

    Returns:
        list: A list of tool payloads.
    """
    tool_payload = []

    for path, methods in openapi_spec.get("paths", {}).items():
        for method, operation in methods.items():
            if operation.get("operationId"):
                tool = {
                    "name": operation.get("operationId"),
                    "description": operation.get(
                        "description",
                        operation.get("summary", "No description available."),
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                }

                for param in operation.get("parameters", []):
                    param_name = param.get("name")
                    if not param_name:
                        continue
                    param_schema = param.get("schema", {})
                    description = param_schema.get("description", "")
                    if not description:
                        description = param.get("description") or ""
                    if param_schema.get("enum") and isinstance(
                        param_schema.get("enum"), list
                    ):
                        description += (
                            f". Possible values: {', '.join(param_schema.get('enum'))}"
                        )
                    param_property = {
                        "type": param_schema.get("type"),
                        "description": description,
                    }

                    # Include items property for array types (required by OpenAI)
                    if param_schema.get("type") == "array" and "items" in param_schema:
                        param_property["items"] = param_schema["items"]

                    tool["parameters"]["properties"][param_name] = param_property
                    if param.get("required"):
                        tool["parameters"]["required"].append(param_name)

                # Extract and resolve requestBody if available
                request_body = operation.get("requestBody")
                if request_body:
                    content = request_body.get("content", {})
                    json_schema = content.get("application/json", {}).get("schema")
                    if json_schema:
                        resolved_schema = resolve_schema(
                            json_schema, openapi_spec.get("components", {})
                        )

                        if resolved_schema.get("properties"):
                            tool["parameters"]["properties"].update(
                                resolved_schema["properties"]
                            )
                            if "required" in resolved_schema:
                                tool["parameters"]["required"] = list(
                                    set(
                                        tool["parameters"]["required"]
                                        + resolved_schema["required"]
                                    )
                                )
                        elif resolved_schema.get("type") == "array":
                            tool["parameters"] = (
                                resolved_schema  # special case for array
                            )

                tool_payload.append(tool)

    return tool_payload


async def set_tool_servers(request: Request):
    request.app.state.TOOL_SERVERS = await get_tool_servers_data(
        request.app.state.config.TOOL_SERVER_CONNECTIONS
    )

    if request.app.state.redis is not None:
        await request.app.state.redis.set(
            "tool_servers", json.dumps(request.app.state.TOOL_SERVERS)
        )

    return request.app.state.TOOL_SERVERS


async def get_tool_servers(request: Request):
    tool_servers = []
    if request.app.state.redis is not None:
        try:
            tool_servers = json.loads(await request.app.state.redis.get("tool_servers"))
            request.app.state.TOOL_SERVERS = tool_servers
        except Exception as e:
            log.error(f"Error fetching tool_servers from Redis: {e}")

    if not tool_servers:
        tool_servers = await set_tool_servers(request)

    return tool_servers


async def get_tool_server_data(url: str, headers: Optional[dict]) -> Dict[str, Any]:
    _headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if headers:
        _headers.update(headers)

    error = None
    try:
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url, headers=_headers, ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
            ) as response:
                if response.status != 200:
                    error_body = await response.json()
                    raise Exception(error_body)

                text_content = None

                # Check if URL ends with .yaml or .yml to determine format
                if url.lower().endswith((".yaml", ".yml")):
                    text_content = await response.text()
                    res = yaml.safe_load(text_content)
                else:
                    text_content = await response.text()

                try:
                    res = json.loads(text_content)
                except json.JSONDecodeError:
                    try:
                        res = yaml.safe_load(text_content)
                    except Exception as e:
                        raise e

    except Exception as err:
        log.exception(f"Could not fetch tool server spec from {url}")
        if isinstance(err, dict) and "detail" in err:
            error = err["detail"]
        else:
            error = str(err)
        raise Exception(error)

    log.debug(f"Fetched data: {res}")
    return res


async def get_tool_servers_data(servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Prepare list of enabled servers along with their original index

    tasks = []
    server_entries = []
    for idx, server in enumerate(servers):
        if (
            server.get("config", {}).get("enable")
            and server.get("type", "openapi") == "openapi"
        ):
            info = server.get("info", {})

            auth_type = server.get("auth_type", "bearer")
            token = None

            if auth_type == "bearer":
                token = server.get("key", "")
            elif auth_type == "none":
                # No authentication
                pass

            id = info.get("id")
            if not id:
                id = str(idx)

            server_url = server.get("url")
            spec_type = server.get("spec_type", "url")

            # Create async tasks to fetch data
            task = None
            if spec_type == "url":
                # Path (to OpenAPI spec URL) can be either a full URL or a path to append to the base URL
                openapi_path = server.get("path", "openapi.json")
                spec_url = get_tool_server_url(server_url, openapi_path)
                # Fetch from URL
                task = get_tool_server_data(
                    spec_url,
                    {"Authorization": f"Bearer {token}"} if token else None,
                )
            elif spec_type == "json" and server.get("spec", ""):
                # Use provided JSON spec
                spec_json = None
                try:
                    spec_json = json.loads(server.get("spec", ""))
                except Exception as e:
                    log.error(f"Error parsing JSON spec for tool server {id}: {e}")

                if spec_json:
                    task = asyncio.sleep(
                        0,
                        result=spec_json,
                    )

            if task:
                tasks.append(task)
                server_entries.append((id, idx, server, server_url, info, token))

    # Execute tasks concurrently
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Build final results with index and server metadata
    results = []
    for (id, idx, server, url, info, _), response in zip(server_entries, responses):
        if isinstance(response, Exception):
            log.error(f"Failed to connect to {url} OpenAPI tool server")
            continue

        response = {
            "openapi": response,
            "info": response.get("info", {}),
            "specs": convert_openapi_to_tool_payload(response),
        }

        openapi_data = response.get("openapi", {})
        if info and isinstance(openapi_data, dict):
            openapi_data["info"] = openapi_data.get("info", {})

            if "name" in info:
                openapi_data["info"]["title"] = info.get("name", "Tool Server")

            if "description" in info:
                openapi_data["info"]["description"] = info.get("description", "")

        results.append(
            {
                "id": str(id),
                "idx": idx,
                "url": server.get("url"),
                "openapi": openapi_data,
                "info": response.get("info"),
                "specs": response.get("specs"),
            }
        )

    return results


async def execute_tool_server(
    url: str,
    headers: Dict[str, str],
    cookies: Dict[str, str],
    name: str,
    params: Dict[str, Any],
    server_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    error = None
    try:
        openapi = server_data.get("openapi", {})
        paths = openapi.get("paths", {})

        matching_route = None
        for route_path, methods in paths.items():
            for http_method, operation in methods.items():
                if isinstance(operation, dict) and operation.get("operationId") == name:
                    matching_route = (route_path, methods)
                    break
            if matching_route:
                break

        if not matching_route:
            raise Exception(f"No matching route found for operationId: {name}")

        route_path, methods = matching_route

        method_entry = None
        for http_method, operation in methods.items():
            if operation.get("operationId") == name:
                method_entry = (http_method.lower(), operation)
                break

        if not method_entry:
            raise Exception(f"No matching method found for operationId: {name}")

        http_method, operation = method_entry

        path_params = {}
        query_params = {}
        body_params = {}

        for param in operation.get("parameters", []):
            param_name = param.get("name")
            if not param_name:
                continue
            param_in = param.get("in")
            if param_name in params:
                if param_in == "path":
                    path_params[param_name] = params[param_name]
                elif param_in == "query":
                    query_params[param_name] = params[param_name]

        final_url = f"{url}{route_path}"
        for key, value in path_params.items():
            final_url = final_url.replace(f"{{{key}}}", str(value))

        if query_params:
            query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
            final_url = f"{final_url}?{query_string}"

        if operation.get("requestBody", {}).get("content"):
            if params:
                body_params = params

        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            request_method = getattr(session, http_method.lower())

            if http_method in ["post", "put", "patch", "delete"]:
                async with request_method(
                    final_url,
                    json=body_params,
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                    allow_redirects=False,
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise Exception(f"HTTP error {response.status}: {text}")

                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = await response.text()

                    response_headers = response.headers
                    return (response_data, response_headers)
            else:
                async with request_method(
                    final_url,
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                    allow_redirects=False,
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise Exception(f"HTTP error {response.status}: {text}")

                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = await response.text()

                    response_headers = response.headers
                    return (response_data, response_headers)

    except Exception as err:
        error = str(err)
        log.exception(f"API Request Error: {error}")
        return ({"error": error}, None)


def get_tool_server_url(url: Optional[str], path: str) -> str:
    """
    Build the full URL for a tool server, given a base url and a path.
    """
    if "://" in path:
        # If it contains "://", it's a full URL
        return path
    if not path.startswith("/"):
        # Ensure the path starts with a slash
        path = f"/{path}"
    return f"{url}{path}"

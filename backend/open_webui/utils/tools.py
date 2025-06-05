import inspect
import logging
import re
import json
import asyncio
from typing import Any, Awaitable, Callable, get_type_hints
from functools import update_wrapper, partial


from fastapi import Request
from pydantic import BaseModel, Field, create_model
from langchain_core.utils.function_calling import convert_to_openai_function


from open_webui.models.tools import Tools
from open_webui.models.users import UserModel
from open_webui.utils.plugin import load_tools_module_by_id

log = logging.getLogger(__name__)


def apply_extra_params_to_tool_function(
    function: Callable, extra_params: dict
) -> Callable[..., Awaitable]:
    sig = inspect.signature(function)
    extra_params = {k: v for k, v in extra_params.items() if k in sig.parameters}
    partial_func = partial(function, **extra_params)
    if inspect.iscoroutinefunction(function):
        update_wrapper(partial_func, function)
        return partial_func

    async def new_function(*args, **kwargs):
        return partial_func(*args, **kwargs)

    update_wrapper(new_function, function)
    return new_function


async def call_mcp_tool(
    request: Request, tool_name: str, arguments: dict, server_idx: int = None
) -> str:
    """Call an MCP tool using the MCP router"""
    try:
        # Import here to avoid circular imports
        from open_webui.routers.mcp import MCPToolCallForm, call_mcp_tool as router_call_mcp_tool
        
        # Create the form data for the router
        form_data = MCPToolCallForm(
            name=tool_name,
            arguments=arguments,
            server_idx=server_idx
        )
        
        # Get the user (this is a simplified version for internal calls)
        user = getattr(request.state, 'user', None)
        
        # Call the router function directly
        result = await router_call_mcp_tool(request, form_data, user)
        
        # Extract the text content from the result
        content = result.get("content", [])
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(text_parts)
        else:
            return str(content)
        
    except Exception as e:
        log.error(f"Error calling MCP tool {tool_name}: {e}")
        return f"Error calling MCP tool {tool_name}: {str(e)}"


async def get_mcp_tools(request: Request) -> dict:
    """Get all available MCP tools"""
    try:
        # Import here to avoid circular imports
        from open_webui.routers.mcp import get_all_mcp_tools
        
        if not request.app.state.config.ENABLE_MCP_API:
            return {}
        
        mcp_tools_response = await get_all_mcp_tools(request)
        mcp_tools = mcp_tools_response.get("tools", [])
        
        tools_dict = {}
        
        for tool in mcp_tools:
            tool_name = tool.get("name", "")
            tool_description = tool.get("description", "")
            tool_input_schema = tool.get("inputSchema", {})
            server_idx = tool.get("mcp_server_idx", 0)
            
            if not tool_name:
                continue
            
            # Create a callable function for this MCP tool with proper closure
            def make_mcp_tool_wrapper(name, idx):
                async def mcp_tool_wrapper(**kwargs):
                    # Remove internal parameters from kwargs
                    clean_kwargs = {
                        k: v for k, v in kwargs.items() if not k.startswith("__")
                    }
                    return await call_mcp_tool(
                        request, name, clean_kwargs, idx
                    )
                return mcp_tool_wrapper
            
            mcp_tool_wrapper = make_mcp_tool_wrapper(tool_name, server_idx)
            
            # Set function metadata for documentation
            mcp_tool_wrapper.__name__ = tool_name
            mcp_tool_wrapper.__doc__ = tool_description
            
            # Convert inputSchema to OpenAI function spec format
            spec = {
                "name": tool_name,
                "description": tool_description,
                "parameters": tool_input_schema
            }
            
            tool_dict = {
                "toolkit_id": f"mcp_server_{server_idx}",
                "callable": mcp_tool_wrapper,
                "spec": spec,
                "pydantic_model": None,  # We'll create this dynamically if needed
                "file_handler": False,
                "citation": True,  # MCP tools should show citations
            }
            
            tools_dict[tool_name] = tool_dict
        
        return tools_dict
        
    except Exception as e:
        log.error(f"Error getting MCP tools: {e}")
        return {}


# Mutation on extra_params
async def get_tools_async(
    request: Request, tool_ids: list[str], user: UserModel, extra_params: dict
) -> dict[str, dict]:
    tools_dict = {}

    # Add regular tools
    for tool_id in tool_ids:
        tools = Tools.get_tool_by_id(tool_id)
        if tools is None:
            continue

        module = request.app.state.TOOLS.get(tool_id, None)
        if module is None:
            module, _ = load_tools_module_by_id(tool_id)
            request.app.state.TOOLS[tool_id] = module

        extra_params["__id__"] = tool_id
        if hasattr(module, "valves") and hasattr(module, "Valves"):
            valves = Tools.get_tool_valves_by_id(tool_id) or {}
            module.valves = module.Valves(**valves)

        if hasattr(module, "UserValves"):
            extra_params["__user__"]["valves"] = module.UserValves(  # type: ignore
                **Tools.get_user_valves_by_id_and_user_id(tool_id, user.id)
            )

        for spec in tools.specs:
            # Remove internal parameters
            spec["parameters"]["properties"] = {
                key: val
                for key, val in spec["parameters"]["properties"].items()
                if not key.startswith("__")
            }

            function_name = spec["name"]

            # convert to function that takes only model params and inserts custom params
            original_func = getattr(module, function_name)
            callable = apply_extra_params_to_tool_function(original_func, extra_params)
            # TODO: This needs to be a pydantic model
            tool_dict = {
                "toolkit_id": tool_id,
                "callable": callable,
                "spec": spec,
                "pydantic_model": function_to_pydantic_model(callable),
                "file_handler": hasattr(module, "file_handler") and module.file_handler,
                "citation": hasattr(module, "citation") and module.citation,
            }

            # TODO: if collision, prepend toolkit name
            if function_name in tools_dict:
                log.warning(f"Tool {function_name} already exists in another tools!")
                log.warning(f"Collision between {tools} and {tool_id}.")
                log.warning(f"Discarding {tools}.{function_name}")
            else:
                tools_dict[function_name] = tool_dict

    # Add MCP tools if enabled and requested
    try:
        mcp_tools = await get_mcp_tools(request)
        log.info(f"=== MCP TOOLS DEBUG ===")
        log.info(f"Available MCP tools: {list(mcp_tools.keys())}")
        log.info(f"Requested tool_ids: {tool_ids}")
        log.info(f"=======================")
        
        for tool_name, tool_dict in mcp_tools.items():
            # Check if this MCP tool is in the requested tool_ids
            # Try multiple matching strategies:
            # 1. Exact match with mcp_ prefix
            mcp_tool_id = f"mcp_{tool_name}"
            # 2. Direct tool name match (for backward compatibility)
            # 3. Check if any tool_id ends with the tool name (for prefixed cases)
            
            is_requested = (
                mcp_tool_id in tool_ids or  # Exact match with mcp_ prefix
                tool_name in tool_ids or    # Direct tool name match
                any(tid.endswith(f"_{tool_name}") or tid.endswith(f".{tool_name}") for tid in tool_ids)  # Suffix match
            )
            
            if not is_requested:
                log.debug(f"Skipping MCP tool {tool_name} (ID: {mcp_tool_id}) - not in selected tool_ids: {tool_ids}")
                continue
                
            if tool_name in tools_dict:
                log.warning(f"MCP tool {tool_name} already exists in regular tools!")
                log.warning(f"Prepending 'mcp_' to avoid collision")
                tool_name = f"mcp_{tool_name}"
                tool_dict["spec"]["name"] = tool_name
            
            log.info(f"Adding MCP tool {tool_name} (ID: {mcp_tool_id}) to tools_dict")
            tools_dict[tool_name] = tool_dict
    except Exception as e:
        log.error(f"Error loading MCP tools: {e}")

    return tools_dict


# Legacy synchronous wrapper for backward compatibility
def get_tools(
    request: Request, tool_ids: list[str], user: UserModel, extra_params: dict
) -> dict[str, dict]:
    """Synchronous wrapper for get_tools_async for backward compatibility"""
    try:
        return asyncio.run(get_tools_async(request, tool_ids, user, extra_params))
    except Exception as e:
        log.error(f"Error in synchronous get_tools wrapper: {e}")
        return {}


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


def function_to_pydantic_model(func: Callable) -> type[BaseModel]:
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
    descriptions = parse_docstring(docstring)

    tool_description = parse_description(docstring)

    field_defs = {}
    for name, param in parameters.items():
        type_hint = type_hints.get(name, Any)
        default_value = param.default if param.default is not param.empty else ...
        description = descriptions.get(name, None)
        if not description:
            field_defs[name] = type_hint, default_value
            continue
        field_defs[name] = type_hint, Field(default_value, description=description)

    model = create_model(func.__name__, **field_defs)
    model.__doc__ = tool_description

    return model


def get_callable_attributes(tool: object) -> list[Callable]:
    return [
        getattr(tool, func)
        for func in dir(tool)
        if callable(getattr(tool, func))
        and not func.startswith("__")
        and not inspect.isclass(getattr(tool, func))
    ]


def get_tools_specs(tool_class: object) -> list[dict]:
    function_list = get_callable_attributes(tool_class)
    models = map(function_to_pydantic_model, function_list)
    return [convert_to_openai_function(tool) for tool in models]

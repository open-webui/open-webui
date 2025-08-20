import inspect
import logging
import re
import inspect
import aiohttp
import asyncio
import yaml

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

from langchain_core.utils.function_calling import (
    convert_to_openai_function as convert_pydantic_model_to_openai_function_spec,
)


from open_webui.models.tools import Tools
from open_webui.models.users import UserModel
from open_webui.utils.plugin import load_tool_module_by_id
from open_webui.env import (
    SRC_LOG_LEVELS,
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA,
    AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
)

import copy

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


def get_async_tool_function_and_apply_extra_params(
    function: Callable, extra_params: dict
) -> Callable[..., Awaitable]:
    sig = inspect.signature(function)
    extra_params = {k: v for k, v in extra_params.items() if k in sig.parameters}
    partial_func = partial(function, **extra_params)

    if inspect.iscoroutinefunction(function):
        update_wrapper(partial_func, function)
        return partial_func
    else:
        # Make it a coroutine function
        async def new_function(*args, **kwargs):
            return partial_func(*args, **kwargs)

        update_wrapper(new_function, function)
        return new_function


def get_tools(
    request: Request, tool_ids: list[str], user: UserModel, extra_params: dict
) -> dict[str, dict]:
    tools_dict = {}

    for tool_id in tool_ids:
        tool = Tools.get_tool_by_id(tool_id)
        if tool is None:
            if tool_id.startswith("server:"):
                server_idx = int(tool_id.split(":")[1])
                tool_server_connection = (
                    request.app.state.config.TOOL_SERVER_CONNECTIONS[server_idx]
                )
                tool_server_data = None
                for server in request.app.state.TOOL_SERVERS:
                    if server["idx"] == server_idx:
                        tool_server_data = server
                        break
                assert tool_server_data is not None
                specs = tool_server_data.get("specs", [])

                for spec in specs:
                    function_name = spec["name"]

                    auth_type = tool_server_connection.get("auth_type", "bearer")
                    token = None

                    if auth_type == "bearer":
                        token = tool_server_connection.get("key", "")
                    elif auth_type == "session":
                        token = request.state.token.credentials

                    def make_tool_function(function_name, token, tool_server_data):
                        async def tool_function(**kwargs):
                            return await execute_tool_server(
                                token=token,
                                url=tool_server_data["url"],
                                name=function_name,
                                params=kwargs,
                                server_data=tool_server_data,
                            )

                        return tool_function

                    tool_function = make_tool_function(
                        function_name, token, tool_server_data
                    )

                    callable = get_async_tool_function_and_apply_extra_params(
                        tool_function,
                        {},
                    )

                    tool_dict = {
                        "tool_id": tool_id,
                        "callable": callable,
                        "spec": spec,
                    }

                    # TODO: if collision, prepend toolkit name
                    if function_name in tools_dict:
                        log.warning(
                            f"Tool {function_name} already exists in another tools!"
                        )
                        log.warning(f"Discarding {tool_id}.{function_name}")
                    else:
                        tools_dict[function_name] = tool_dict
            else:
                continue
        else:
            module = request.app.state.TOOLS.get(tool_id, None)
            if module is None:
                module, _ = load_tool_module_by_id(tool_id)
                request.app.state.TOOLS[tool_id] = module

            extra_params["__id__"] = tool_id

            # Set valves for the tool
            if hasattr(module, "valves") and hasattr(module, "Valves"):
                valves = Tools.get_tool_valves_by_id(tool_id) or {}
                module.valves = module.Valves(**valves)
            if hasattr(module, "UserValves"):
                extra_params["__user__"]["valves"] = module.UserValves(  # type: ignore
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
                    tool_function, extra_params
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

                # TODO: if collision, prepend toolkit name
                if function_name in tools_dict:
                    log.warning(
                        f"Tool {function_name} already exists in another tools!"
                    )
                    log.warning(f"Discarding {tool_id}.{function_name}")
                else:
                    tools_dict[function_name] = tool_dict

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
            field_defs[name] = type_hint, Field(
                default_value, description=param_description
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

                # Extract path and query parameters
                for param in operation.get("parameters", []):
                    param_name = param["name"]
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


async def get_tool_server_data(token: str, url: str) -> Dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    error = None
    try:
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
            ) as response:
                if response.status != 200:
                    error_body = await response.json()
                    raise Exception(error_body)

                # Check if URL ends with .yaml or .yml to determine format
                if url.lower().endswith((".yaml", ".yml")):
                    text_content = await response.text()
                    res = yaml.safe_load(text_content)
                else:
                    res = await response.json()
    except Exception as err:
        log.exception(f"Could not fetch tool server spec from {url}")
        if isinstance(err, dict) and "detail" in err:
            error = err["detail"]
        else:
            error = str(err)
        raise Exception(error)

    data = {
        "openapi": res,
        "info": res.get("info", {}),
        "specs": convert_openapi_to_tool_payload(res),
    }

    log.info(f"Fetched data: {data}")
    return data


async def get_tool_servers_data(
    servers: List[Dict[str, Any]], session_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    # Prepare list of enabled servers along with their original index
    server_entries = []
    for idx, server in enumerate(servers):
        if server.get("config", {}).get("enable"):
            # Path (to OpenAPI spec URL) can be either a full URL or a path to append to the base URL
            openapi_path = server.get("path", "openapi.json")
            full_url = get_tool_server_url(server.get("url"), openapi_path)

            info = server.get("info", {})

            auth_type = server.get("auth_type", "bearer")
            token = None

            if auth_type == "bearer":
                token = server.get("key", "")
            elif auth_type == "session":
                token = session_token
            server_entries.append((idx, server, full_url, info, token))

    # Create async tasks to fetch data
    tasks = [
        get_tool_server_data(token, url) for (_, _, url, _, token) in server_entries
    ]

    # Execute tasks concurrently
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Build final results with index and server metadata
    results = []
    for (idx, server, url, info, _), response in zip(server_entries, responses):
        if isinstance(response, Exception):
            log.error(f"Failed to connect to {url} OpenAPI tool server")
            continue

        openapi_data = response.get("openapi", {})

        if info and isinstance(openapi_data, dict):
            openapi_data["info"] = openapi_data.get("info", {})

            if "name" in info:
                openapi_data["info"]["title"] = info.get("name", "Tool Server")

            if "description" in info:
                openapi_data["info"]["description"] = info.get("description", "")

        results.append(
            {
                "idx": idx,
                "url": server.get("url"),
                "openapi": openapi_data,
                "info": response.get("info"),
                "specs": response.get("specs"),
            }
        )

    return results


async def execute_tool_server(
    token: str, url: str, name: str, params: Dict[str, Any], server_data: Dict[str, Any]
) -> Any:
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
            param_name = param["name"]
            param_in = param["in"]
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
            else:
                raise Exception(
                    f"Request body expected for operation '{name}' but none found."
                )

        headers = {"Content-Type": "application/json"}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession(trust_env=True) as session:
            request_method = getattr(session, http_method.lower())

            if http_method in ["post", "put", "patch"]:
                async with request_method(
                    final_url,
                    json=body_params,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise Exception(f"HTTP error {response.status}: {text}")
                    return await response.json()
            else:
                async with request_method(
                    final_url,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise Exception(f"HTTP error {response.status}: {text}")
                    return await response.json()

    except Exception as err:
        error = str(err)
        log.exception(f"API Request Error: {error}")
        return {"error": error}


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

import inspect
import logging
from typing import Awaitable, Callable, get_type_hints

from open_webui.apps.webui.models.tools import Tools
from open_webui.apps.webui.models.users import UserModel
from open_webui.apps.webui.utils import load_tools_module_by_id
from open_webui.utils.schemas import json_schema_to_model

log = logging.getLogger(__name__)


def apply_extra_params_to_tool_function(
    function: Callable, extra_params: dict
) -> Callable[..., Awaitable]:
    sig = inspect.signature(function)
    extra_params = {
        key: value for key, value in extra_params.items() if key in sig.parameters
    }
    is_coroutine = inspect.iscoroutinefunction(function)

    async def new_function(**kwargs):
        extra_kwargs = kwargs | extra_params
        if is_coroutine:
            return await function(**extra_kwargs)
        return function(**extra_kwargs)

    return new_function


# Mutation on extra_params
def get_tools(
    webui_app, tool_ids: list[str], user: UserModel, extra_params: dict
) -> dict[str, dict]:
    tools_dict = {}

    for tool_id in tool_ids:
        tools = Tools.get_tool_by_id(tool_id)
        if tools is None:
            continue

        module = webui_app.state.TOOLS.get(tool_id, None)
        if module is None:
            module, _ = load_tools_module_by_id(tool_id)
            webui_app.state.TOOLS[tool_id] = module

        extra_params["__id__"] = tool_id
        if hasattr(module, "valves") and hasattr(module, "Valves"):
            valves = Tools.get_tool_valves_by_id(tool_id) or {}
            module.valves = module.Valves(**valves)

        if hasattr(module, "UserValves"):
            extra_params["__user__"]["valves"] = module.UserValves(  # type: ignore
                **Tools.get_user_valves_by_id_and_user_id(tool_id, user.id)
            )

        for spec in tools.specs:
            # TODO: Fix hack for OpenAI API
            for val in spec.get("parameters", {}).get("properties", {}).values():
                if val["type"] == "str":
                    val["type"] = "string"

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
            if hasattr(original_func, "__doc__"):
                callable.__doc__ = original_func.__doc__

            # TODO: This needs to be a pydantic model
            tool_dict = {
                "toolkit_id": tool_id,
                "callable": callable,
                "spec": spec,
                "pydantic_model": json_schema_to_model(spec),
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

    return tools_dict


def doc_to_dict(docstring):
    lines = docstring.split("\n")
    description = lines[1].strip()
    param_dict = {}

    for line in lines:
        if ":param" in line:
            line = line.replace(":param", "").strip()
            param, desc = line.split(":", 1)
            param_dict[param.strip()] = desc.strip()
    ret_dict = {"description": description, "params": param_dict}
    return ret_dict


def get_tools_specs(tools) -> list[dict]:
    function_list = [
        {"name": func, "function": getattr(tools, func)}
        for func in dir(tools)
        if callable(getattr(tools, func))
        and not func.startswith("__")
        and not inspect.isclass(getattr(tools, func))
    ]

    specs = []
    for function_item in function_list:
        function_name = function_item["name"]
        function = function_item["function"]

        function_doc = doc_to_dict(function.__doc__ or function_name)
        specs.append(
            {
                "name": function_name,
                # TODO: multi-line desc?
                "description": function_doc.get("description", function_name),
                "parameters": {
                    "type": "object",
                    "properties": {
                        param_name: {
                            "type": param_annotation.__name__.lower(),
                            **(
                                {
                                    "enum": (
                                        str(param_annotation.__args__)
                                        if hasattr(param_annotation, "__args__")
                                        else None
                                    )
                                }
                                if hasattr(param_annotation, "__args__")
                                else {}
                            ),
                            "description": function_doc.get("params", {}).get(
                                param_name, param_name
                            ),
                        }
                        for param_name, param_annotation in get_type_hints(
                            function
                        ).items()
                        if param_name != "return"
                        and not (
                            param_name.startswith("__") and param_name.endswith("__")
                        )
                    },
                    "required": [
                        name
                        for name, param in inspect.signature(
                            function
                        ).parameters.items()
                        if param.default is param.empty
                        and not (name.startswith("__") and name.endswith("__"))
                    ],
                },
            }
        )

    return specs

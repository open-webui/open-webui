import inspect
from typing import get_type_hints, List, Dict, Any


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


def get_tools_specs(tools) -> List[dict]:
    function_list = [
        {"name": func, "function": getattr(tools, func)}
        for func in dir(tools)
        if callable(getattr(tools, func)) and not func.startswith("__")
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
                        if param_name != "return" and param_name != "__user__"
                    },
                    "required": [
                        name
                        for name, param in inspect.signature(
                            function
                        ).parameters.items()
                        if param.default is param.empty
                    ],
                },
            }
        )

    return specs

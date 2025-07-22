Question: 

The content of "params" function argument for the execute_pipe(pipe, params) function argument under * **File:** `backend/open_webui/functions.py` * **Function:** `generate_function_chat_completion` * **Line of code:** `res = await execute_pipe(pipe, params)` contains information of available tools. I want to modify the code base to include endpoint and api-key of available tools, as additional attributes under "params" argument, so functions can actually use whatever tool that's chosen by the user on the open-webui frontend. Which part of code should I focus on modifying?

Answer:

Based on your requirement to include endpoint and api-key information for available tools in the `params` argument, you should focus on modifying these specific parts of the codebase:

## Primary Focus Areas:

**1. Tool Information Collection (`get_tools` function)**
The `get_tools` function is where tool information is currently gathered and structured. You'll need to modify this function to include endpoint and api-key information in the returned tool data structure. [backend/open_webui/utils/tools.py]
```python
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
                            print(
                                f"Executing tool function {function_name} with params: {kwargs}"
                            )
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
                    if val["type"] == "str":
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
```

**2. Tool Server Connection Data**
The tool server connection information (including auth_type and key) is already available in the tool server data structure. You can extract this information and include it in the tool data. [backend/open_webui/utils/tools.py]
```python
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

```


**3. Parameter Building in Function Execution**
The `extra_params` object construction is where you should add the endpoint and api-key information as additional attributes. This happens before the `get_tools` call where tool information is added to the params. [backend/open_webui/functions.py]
```python
    extra_params["__tools__"] = get_tools(
        request,
        tool_ids,
        user,
        {
            **extra_params,
            "__model__": models.get(form_data["model"], None),
            "__messages__": form_data["messages"],
            "__files__": files,
        },
    )
```

**4. Function Parameter Assembly**
The `get_function_params` function assembles the final parameters that get passed to `execute_pipe`. You may need to modify this function to ensure endpoint and api-key information is properly included in the params structure. [backend/open_webui/functions.py]
```python
    def get_function_params(function_module, form_data, user, extra_params=None):
        if extra_params is None:
            extra_params = {}

        pipe_id = get_pipe_id(form_data)

        # Get the signature of the function
        sig = inspect.signature(function_module.pipe)
        params = {"body": form_data} | {
            k: v for k, v in extra_params.items() if k in sig.parameters
        }

        if "__user__" in params and hasattr(function_module, "UserValves"):
            user_valves = Functions.get_user_valves_by_id_and_user_id(pipe_id, user.id)
            try:
                params["__user__"]["valves"] = function_module.UserValves(**user_valves)
            except Exception as e:
                log.exception(e)
                params["__user__"]["valves"] = function_module.UserValves()

        return params
```
## Tool Server Configuration Structure:

The tool server connection configuration already contains the endpoint and authentication information you need. [backend/open_webui/routers/configs.py]
```python
class ToolServerConnection(BaseModel):
    url: str
    path: str
    auth_type: Optional[str]
    key: Optional[str]
    config: Optional[dict]

    model_config = ConfigDict(extra="allow")
```

## Notes:

The endpoint and api-key information is already available in the tool server connection data (`auth_type` and `key` fields), but it's currently only used internally for authentication during tool execution. You'll need to extract this information and make it available as additional attributes in the `params` object so that functions can access and use whatever tool endpoint and credentials are chosen by the user on the Open WebUI frontend.

The modification should ensure that each tool in the `__tools__` parameter includes its corresponding endpoint URL and api-key information as additional metadata that functions can access programmatically.

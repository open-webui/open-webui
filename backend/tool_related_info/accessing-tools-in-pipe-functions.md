Question: 

The content of "params" argument in the execute_pipe(pipe, params) function under * **File:** `backend/open_webui/functions.py` * **Function:** `generate_function_chat_completion` * **Line of code:** `res = await execute_pipe(pipe, params)` contains information of available tools, under params['__tools__']. I want to use that tool information in my pipe function, how do I use the "params" argument iny my pipe function?

Answer:

Based on my analysis of the Open WebUI codebase, here's how to use the `params` argument in your pipe function to access tool information:

## How to Access `__tools__` in Your Pipe Function

The `params` argument in `execute_pipe(pipe, params)` contains various parameters including the available tools under `params['__tools__']`. To use this in your pipe function, you need to understand how the parameter passing works.

### Parameter Construction

The `params` dictionary is constructed by the `get_function_params` function, which includes the request body and extra parameters. [backend/open_webui/functions.py]. 
```python
    def get_function_params(function_module, form_data, user, extra_params=None):
        if extra_params is None:
            extra_params = {}

        pipe_id = get_pipe_id(form_data)

        # Get the signature of the function
        sig = inspect.signature(function_module.pipe)
        params = {"body": form_data} | {
            k: v
            for k, v in extra_params.items()
            if k in sig.parameters or k == "__tools__"
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
The `__tools__` parameter is specifically added to the extra parameters [backend/open_webui/functions.py].
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

### Function Signature Requirements

The system uses `inspect.signature` to determine which parameters your pipe function can accept [backend/open_webui/functions.py]. 
```python
        # Get the signature of the function
        sig = inspect.signature(function_module.pipe)
        params = {"body": form_data} | {
            k: v for k, v in extra_params.items() if k in sig.parameters
        }
```

This means you need to explicitly include the parameters you want to receive in your function signature.

### How to Structure Your Pipe Function

To access tools in your pipe function, you have several options:

**Option 1: Accept `__tools__` directly as a parameter**
```python
def pipe(self, body: dict, __tools__: dict = None):
    # Access tools directly
    if __tools__:
        # Use tools here
        for tool_name, tool_info in __tools__.items():
            # tool_info contains 'callable', 'spec', 'tool_id', etc.
            pass
```

**Option 2: Use **kwargs to accept all extra parameters**
```python
def pipe(self, body: dict, **kwargs):
    tools = kwargs.get('__tools__', {})
    # Use tools here
```

### Understanding the Tools Structure

The `__tools__` parameter contains a dictionary where each key is a tool name and each value is a dictionary with the tool information. [backend/open_webui/utils/tools.py]
```python
                    tool_dict = {
                        "tool_id": tool_id,
                        "callable": callable,
                        "spec": spec,
                        "endpoint": tool_server_data["url"],
                        "api_key": token,
                    }

                    # TODO: if collision, prepend toolkit name
                    if function_name in tools_dict:
                        log.warning(
                            f"Tool {function_name} already exists in another tools!"
                        )
                        log.warning(f"Discarding {tool_id}.{function_name}")
                    else:
                        tools_dict[function_name] = tool_dict
```  
Each tool dictionary contains:
- `tool_id`: The identifier of the tool
- `callable`: The actual function you can call
- `spec`: The tool specification (parameters, description, etc.)
- `metadata`: Additional information about the tool
- `endpoint`: The URL of the tool's server
- `api_key`: The API key for authentication

### Example Implementation Structure

Based on the boilerplate examples in the codebase [src/lib/components/admin/Functions/FunctionEditor.svelte]
```python
    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        if "user" in body:
            print(body["user"])
            del body["user"]

        headers = {}
        headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
        headers["Content-Type"] = "application/json"

        model_id = body["model"][body["model"].find(".") + 1 :]
        payload = {**body, "model": model_id}
        print(payload)

        try:
            r = requests.post(
                url=f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
`;
```

, your pipe function should follow this pattern:

```python
class Pipe:
    def __init__(self):
        # Your initialization code
        pass

    def pipe(self, body: dict, __tools__: dict = None, **kwargs):
        # Access tools
        if __tools__:
            # Iterate through available tools
            for tool_name, tool_data in __tools__.items():
                # Call a tool if needed
                # result = await tool_data['callable'](param1=value1, param2=value2)
                pass
        
        # Process the body and return response
        return "Your response"
```

### Key Points

1. The parameter filtering ensures only parameters that exist in your function signature are passed [backend/open_webui/functions.py]
```python
        params = {"body": form_data} | {
            k: v for k, v in extra_params.items() if k in sig.parameters
        }
```
2. Tools are loaded and made available through the `get_tools` utility function [backend/open_webui/utils/tools.py]
```python
def get_tools(
    request: Request, tool_ids: list[str], user: UserModel, extra_params: dict
) -> dict[str, dict]:
```
3. Each tool's `callable` is an async function that you can invoke with the appropriate parameters

## Notes

- Make sure to include `__tools__` in your function signature if you want to access tools directly
- The tools dictionary contains callable functions that are already configured with the necessary authentication and parameters
- Tools can be from various sources including local tool modules and external tool servers
- Always check if `__tools__` exists and contains the tools you need before attempting to use them

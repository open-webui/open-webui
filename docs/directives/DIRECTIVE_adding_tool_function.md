# Directive: Adding Tools and Functions

> **Pattern type:** Platform extension
> **Complexity:** Medium-High
> **Files touched:** 2-4

---

## Prerequisites

- `DOMAIN_GLOSSARY.md` — Tool, Function, Valves terms
- `ARCHITECTURE_OVERVIEW.md` — System design

---

## Structural Pattern

Open WebUI supports two extension mechanisms:

1. **Tools:** External capabilities models can invoke via function calling (OpenAPI specs)
2. **Functions:** Server-side Python code (filters/actions) that modify behavior

| Type | Storage | Execution | Use Case |
|------|---------|-----------|----------|
| Tool | Database (OpenAPI YAML) | External API call | Web search, calculator, API integrations |
| Function | Database (Python code) | RestrictedPython sandbox | Request/response modification, automation |

---

## Illustrative Application: Adding a Tool

### Step 1: Define Tool Specification (OpenAPI)

Tools are defined as OpenAPI specifications stored in the database:

```yaml
# Tool specification (stored in tools.content)
openapi: 3.0.0
info:
  title: Weather Tool
  version: 1.0.0
  description: Get current weather for a location

servers:
  - url: https://api.weather.example.com

paths:
  /weather:
    get:
      operationId: get_weather
      summary: Get current weather
      parameters:
        - name: location
          in: query
          required: true
          schema:
            type: string
          description: City name or coordinates
        - name: units
          in: query
          required: false
          schema:
            type: string
            enum: [metric, imperial]
            default: metric
      responses:
        '200':
          description: Weather data
          content:
            application/json:
              schema:
                type: object
                properties:
                  temperature:
                    type: number
                  conditions:
                    type: string
```

### Step 2: Create Tool via API

```python
# Creating a tool programmatically
tool_data = {
    "id": "weather_tool",
    "name": "Weather Tool",
    "content": OPENAPI_YAML_STRING,  # The spec above
    "meta": {
        "description": "Get current weather information",
        "manifest": {
            "api_key_required": True,
        }
    },
    "valves": {
        "api_key": "",  # User configurable
    },
    "access_control": {
        "read": {"group_ids": [], "user_ids": []},
        "write": {"group_ids": [], "user_ids": []},
    }
}

# Via router
@router.post("/")
async def create_tool(
    body: ToolCreate,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    tool = Tools.insert_tool(user.id, body, db=db)
    return tool
```

### Step 3: Tool Execution Flow

```python
# backend/open_webui/utils/tools.py
async def execute_tool(
    tool: Tool,
    function_name: str,
    arguments: dict,
    user: UserModel,
) -> dict:
    """Execute a tool function."""
    # Parse OpenAPI spec
    spec = parse_openapi(tool.content)

    # Find the operation
    operation = find_operation(spec, function_name)

    # Build request
    url = build_url(spec, operation, arguments)
    headers = build_headers(tool.valves)

    # Execute
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=operation.method,
            url=url,
            headers=headers,
            json=arguments if operation.method in ['POST', 'PUT'] else None,
        ) as response:
            return await response.json()
```

---

## Illustrative Application: Adding a Function

### Step 1: Define Function Code

Functions are Python code with specific entry points:

```python
# Function code (stored in functions.content)
"""
title: Message Logger
description: Logs all messages for debugging
author: developer
version: 0.1.0
"""

from pydantic import BaseModel
from typing import Optional


class Valves(BaseModel):
    """Configuration options for this function."""
    log_level: str = "info"
    include_content: bool = True


class Filter:
    """
    Filter functions intercept and can modify requests/responses.
    """

    def __init__(self):
        self.valves = Valves()

    async def inlet(self, body: dict, __user__: dict) -> dict:
        """
        Called before the request is sent to the model.

        Args:
            body: The request body
            __user__: Current user info

        Returns:
            Modified request body
        """
        print(f"[{self.valves.log_level}] User {__user__.get('name')} sent message")

        if self.valves.include_content:
            messages = body.get("messages", [])
            if messages:
                print(f"Content: {messages[-1].get('content', '')[:100]}")

        return body

    async def outlet(self, body: dict, __user__: dict) -> dict:
        """
        Called after receiving the model response.

        Args:
            body: The response body
            __user__: Current user info

        Returns:
            Modified response body
        """
        print(f"[{self.valves.log_level}] Response generated for {__user__.get('name')}")
        return body
```

### Step 2: Action Function Example

```python
# Action function (stored in functions.content)
"""
title: Summarize Chat
description: Generates a summary of the current chat
author: developer
version: 0.1.0
"""

from pydantic import BaseModel


class Valves(BaseModel):
    """Configuration options."""
    max_length: int = 200


class Action:
    """
    Action functions are triggered explicitly by the user or system.
    """

    def __init__(self):
        self.valves = Valves()

    async def action(
        self,
        body: dict,
        __user__: dict,
        __event_emitter__=None,
    ) -> dict:
        """
        Execute the action.

        Args:
            body: Request context
            __user__: Current user
            __event_emitter__: For streaming responses

        Returns:
            Action result
        """
        messages = body.get("messages", [])

        # Build summary prompt
        content = "\n".join([
            f"{m['role']}: {m['content'][:100]}"
            for m in messages[-10:]  # Last 10 messages
        ])

        summary = f"Chat with {len(messages)} messages about: {content[:self.valves.max_length]}"

        return {"summary": summary}
```

### Step 3: Register Function

```python
# Via API
function_data = {
    "id": "message_logger",
    "name": "Message Logger",
    "type": "filter",  # or "action"
    "content": PYTHON_CODE_STRING,
    "meta": {
        "description": "Logs messages for debugging",
    },
    "valves": {},  # Defaults from Valves class
    "is_active": True,
    "is_global": False,  # True = applies to all users
}
```

---

## Transfer Prompt

**When you need to add a Tool (external API):**

1. **Write OpenAPI spec** defining the API:
   ```yaml
   openapi: 3.0.0
   info:
     title: My Tool
     version: 1.0.0
   paths:
     /endpoint:
       get:
         operationId: my_operation
         parameters:
           - name: param
             in: query
             required: true
             schema:
               type: string
   ```

2. **Create tool** via Admin UI or API with spec in `content` field

3. **Configure valves** for API keys and settings

4. **Enable for users** via access control

**When you need to add a Function (Python code):**

1. **Choose function type:**
   - `filter`: Modify requests/responses (inlet/outlet methods)
   - `action`: Triggered operations (action method)

2. **Write function class:**
   ```python
   from pydantic import BaseModel

   class Valves(BaseModel):
       setting: str = "default"

   class Filter:  # or Action
       def __init__(self):
           self.valves = Valves()

       async def inlet(self, body: dict, __user__: dict) -> dict:
           # Modify request
           return body
   ```

3. **Create function** via Admin UI or API

4. **Set scope:**
   - `is_global=True`: Applies to all users
   - `is_global=False`: User enables manually

**Special variables in functions:**
- `__user__`: Current user dict
- `__event_emitter__`: For streaming responses
- `self.valves`: Configuration values

**Signals that this pattern applies:**
- Integrating external APIs for models
- Modifying request/response behavior
- Adding automation or logging
- Custom model behaviors

---

## Related Documents

- `DOMAIN_GLOSSARY.md` — Tool, Function, Valves definitions
- `backend/open_webui/routers/tools.py` — Tool API
- `backend/open_webui/routers/functions.py` — Function API

---

*Last updated: 2026-02-03*

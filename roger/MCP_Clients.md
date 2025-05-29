Clients

Client Overview
===============

Learn how to use the FastMCP Client to interact with MCP servers.

`New in version: 2.0.0
`

The `fastmcp.Client` provides a high-level, asynchronous interface for interacting with any Model Context Protocol (MCP) server, whether it's built with FastMCP or another implementation. It simplifies communication by handling protocol details and connection management.

[​

](https://gofastmcp.com/clients/client#fastmcp-client)
FastMCP Client
-------------------------------------------------------------------------

The FastMCP Client architecture separates the protocol logic (`Client`) from the connection mechanism (`Transport`).

-   **`Client`**: Handles sending MCP requests (like `tools/call`, `resources/read`), receiving responses, and managing callbacks.
-   **`Transport`**: Responsible for establishing and maintaining the connection to the server (e.g., via WebSockets, SSE, Stdio, or in-memory).

### [​

](https://gofastmcp.com/clients/client#transports)
Transports

Clients must be initialized with a `transport`. You can either provide an already instantiated transport object, or provide a transport source and let FastMCP attempt to infer the correct transport to use.

The following inference rules are used to determine the appropriate `ClientTransport` based on the input type:

1.  **`ClientTransport` Instance**: If you provide an already instantiated transport object, it's used directly.
2.  **`FastMCP` Instance**: Creates a `FastMCPTransport` for efficient in-memory communication (ideal for testing).
3.  **`Path` or `str` pointing to an existing file**:
    -   If it ends with `.py`: Creates a `PythonStdioTransport` to run the script using `python`.
    -   If it ends with `.js`: Creates a `NodeStdioTransport` to run the script using `node`.
4.  **`AnyUrl` or `str` pointing to a URL**:
    -   If it starts with `http://` or `https://`: Creates an `SSETransport`.
    -   If it starts with `ws://` or `wss://`: Creates a `WSTransport`.
5.  **Other**: Raises a `ValueError` if the type cannot be inferred.

Copy

```
import asyncio
from fastmcp import Client, FastMCP

# Example transports (more details in Transports page)
server_instance = FastMCP(name="TestServer") # In-memory server
sse_url = "http://localhost:8000/sse"       # SSE server URL
ws_url = "ws://localhost:9000"             # WebSocket server URL
server_script = "my_mcp_server.py"         # Path to a Python server file

# Client automatically infers the transport type
client_in_memory = Client(server_instance)
client_sse = Client(sse_url)
client_ws = Client(ws_url)
client_stdio = Client(server_script)

print(client_in_memory.transport)
print(client_sse.transport)
print(client_ws.transport)
print(client_stdio.transport)

# Expected Output (types may vary slightly based on environment):
# <FastMCP(server='TestServer')>
# <SSE(url='http://localhost:8000/sse')>
# <WebSocket(url='ws://localhost:9000')>
# <PythonStdioTransport(command='python', args=['/path/to/your/my_mcp_server.py'])>

```

For more control over connection details (like headers for SSE, environment variables for Stdio), you can instantiate the specific `ClientTransport` class yourself and pass it to the `Client`. See the [Transports](https://gofastmcp.com/clients/transports) page for details.

[​

](https://gofastmcp.com/clients/client#client-usage)
Client Usage
---------------------------------------------------------------------

### [​

](https://gofastmcp.com/clients/client#connection-lifecycle)
Connection Lifecycle

The client operates asynchronously and must be used within an `async with` block. This context manager handles establishing the connection, initializing the MCP session, and cleaning up resources upon exit.

Copy

```
import asyncio
from fastmcp import Client

client = Client("my_mcp_server.py") # Assumes my_mcp_server.py exists

async def main():
    # Connection is established here
    async with client:
        print(f"Client connected: {client.is_connected()}")

        # Make MCP calls within the context
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        if any(tool.name == "greet" for tool in tools):
            result = await client.call_tool("greet", {"name": "World"})
            print(f"Greet result: {result}")

    # Connection is closed automatically here
    print(f"Client connected: {client.is_connected()}")

if __name__ == "__main__":
    asyncio.run(main())

```

You can make multiple calls to the server within the same `async with` block using the established session.

### [​

](https://gofastmcp.com/clients/client#client-methods)
Client Methods

The `Client` provides methods corresponding to standard MCP requests:

The standard client methods return user-friendly representations that may change as the protocol evolves. For consistent access to the complete data structure, use the `*_mcp` methods described later.

#### [​

](https://gofastmcp.com/clients/client#tool-operations)
Tool Operations

-   **`list_tools()`**: Retrieves a list of tools available on the server.Copy

    ```
    tools = await client.list_tools()
    # tools -> list[mcp.types.Tool]

    ```

-   **`call_tool(name: str, arguments: dict[str, Any] | None = None)`**: Executes a tool on the server.Copy

    ```
    result = await client.call_tool("add", {"a": 5, "b": 3})
    # result -> list[mcp.types.TextContent | mcp.types.ImageContent | ...]
    print(result[0].text) # Assuming TextContent, e.g., '8'

    ```

    -   Arguments are passed as a dictionary. FastMCP servers automatically handle JSON string parsing for complex types if needed.
    -   Returns a list of content objects (usually `TextContent` or `ImageContent`).

#### [​

](https://gofastmcp.com/clients/client#resource-operations)
Resource Operations

-   **`list_resources()`**: Retrieves a list of static resources.Copy

    ```
    resources = await client.list_resources()
    # resources -> list[mcp.types.Resource]

    ```

-   **`list_resource_templates()`**: Retrieves a list of resource templates.Copy

    ```
    templates = await client.list_resource_templates()
    # templates -> list[mcp.types.ResourceTemplate]

    ```

-   **`read_resource(uri: str | AnyUrl)`**: Reads the content of a resource or a resolved template.Copy

    ```
    # Read a static resource
    readme_content = await client.read_resource("file:///path/to/README.md")
    # readme_content -> list[mcp.types.TextResourceContents | mcp.types.BlobResourceContents]
    print(readme_content[0].text) # Assuming text

    # Read a resource generated from a template
    weather_content = await client.read_resource("data://weather/london")
    print(weather_content[0].text) # Assuming text JSON

    ```

#### [​

](https://gofastmcp.com/clients/client#prompt-operations)
Prompt Operations

-   **`list_prompts()`**: Retrieves available prompt templates.
-   **`get_prompt(name: str, arguments: dict[str, Any] | None = None)`**: Retrieves a rendered prompt message list.

### [​

](https://gofastmcp.com/clients/client#raw-mcp-protocol-objects)
Raw MCP Protocol Objects

`New in version: 2.2.7
`

The FastMCP client attempts to provide a "friendly" interface to the MCP protocol, but sometimes you may need access to the raw MCP protocol objects. Each of the main client methods that returns data has a corresponding `*_mcp` method that returns the raw MCP protocol objects directly.

The standard client methods (without `_mcp`) return user-friendly representations of MCP data, while `*_mcp` methods will always return the complete MCP protocol objects. As the protocol evolves, changes to these user-friendly representations may occur and could potentially be breaking. If you need consistent, stable access to the full data structure, prefer using the `*_mcp` methods.

Copy

```
# Standard method - returns just the list of tools
tools = await client.list_tools()
# tools -> list[mcp.types.Tool]

# Raw MCP method - returns the full protocol object
result = await client.list_tools_mcp()
# result -> mcp.types.ListToolsResult
tools = result.tools

```

Available raw MCP methods:

-   **`list_tools_mcp()`**: Returns `mcp.types.ListToolsResult`
-   **`call_tool_mcp(name, arguments)`**: Returns `mcp.types.CallToolResult`
-   **`list_resources_mcp()`**: Returns `mcp.types.ListResourcesResult`
-   **`list_resource_templates_mcp()`**: Returns `mcp.types.ListResourceTemplatesResult`
-   **`read_resource_mcp(uri)`**: Returns `mcp.types.ReadResourceResult`
-   **`list_prompts_mcp()`**: Returns `mcp.types.ListPromptsResult`
-   **`get_prompt_mcp(name, arguments)`**: Returns `mcp.types.GetPromptResult`
-   **`complete_mcp(ref, argument)`**: Returns `mcp.types.CompleteResult`

These methods are especially useful for debugging or when you need to access metadata or fields that aren't exposed by the simplified methods.

### [​

](https://gofastmcp.com/clients/client#advanced-features)
Advanced Features

MCP allows servers to interact with clients in order to provide additional capabilities. The `Client` constructor accepts additional configuration to handle these server requests.

#### [​

](https://gofastmcp.com/clients/client#llm-sampling)
LLM Sampling

MCP Servers can request LLM completions from clients. The client can provide a `sampling_handler` to handle these requests. The sampling handler receives a list of messages and other parameters from the server, and should return a string completion.

The following example uses the `marvin` library to generate a completion:

Copy

```
import marvin
from fastmcp import Client
from fastmcp.client.sampling import (
    SamplingMessage,
    SamplingParams,
    RequestContext,
)

async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    return await marvin.say_async(
        message=[m.content.text for m in messages],
        instructions=params.systemPrompt,
    )

client = Client(
    ...,
    sampling_handler=sampling_handler,
)

```

#### [​

](https://gofastmcp.com/clients/client#logging)
Logging

MCP servers can emit logs to clients. The client can set a logging callback to receive these logs.

Copy

```
from fastmcp import Client
from fastmcp.client.logging import LogHandler, LogMessage

async def my_log_handler(params: LogMessage):
    print(f"[Server Log - {params.level.upper()}] {params.logger or 'default'}: {params.data}")

client_with_logging = Client(
    ...,
    log_handler=my_log_handler,
)

```

#### [​

](https://gofastmcp.com/clients/client#roots)
Roots

Roots are a way for clients to inform servers about the resources they have access to or certain boundaries on their access. The server can use this information to adjust behavior or provide more accurate responses.

Servers can request roots from clients, and clients can notify servers when their roots change.

To set the roots when creating a client, users can either provide a list of roots (which can be a list of strings) or an async function that returns a list of roots.

Static Roots

Dynamic Roots Callback

Copy

```
from fastmcp import Client

client = Client(
    ...,
    roots=["/path/to/root1", "/path/to/root2"],
)

```

### [​

](https://gofastmcp.com/clients/client#utility-methods)
Utility Methods

-   **`ping()`**: Sends a ping request to the server to verify connectivity.Copy

    ```
    async def check_connection():
        async with client:
            await client.ping()
            print("Server is reachable")

    ```

### [​

](https://gofastmcp.com/clients/client#error-handling)
Error Handling

When a `call_tool` request results in an error on the server (e.g., the tool function raised an exception), the `client.call_tool()` method will raise a `fastmcp.client.ClientError`.

Copy

```
async def safe_call_tool():
    async with client:
        try:
            # Assume 'divide' tool exists and might raise ZeroDivisionError
            result = await client.call_tool("divide", {"a": 10, "b": 0})
            print(f"Result: {result}")
        except ClientError as e:
            print(f"Tool call failed: {e}")
        except ConnectionError as e:
            print(f"Connection failed: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

# Example Output if division by zero occurs:
# Tool call failed: Division by zero is not allowed.

```

Other errors, like connection failures, will raise standard Python exceptions (e.g., `ConnectionError`, `TimeoutError`).

The client transport often has its own error-handling mechanisms, so you can not always trap errors like those raised by `call_tool` outside of the `async with` block. Instead, you can use `call_tool_mcp()` to get the raw `mcp.types.CallToolResult` object and handle errors yourself by checking its `isError` attribute.

[Authentication](https://gofastmcp.com/deployment/authentication)[Transports](https://gofastmcp.com/clients/transports)



Clients

Client Transports
=================

Understand the different ways FastMCP Clients can connect to servers.

`New in version: 2.0.0
`

The FastMCP `Client` relies on a `ClientTransport` object to handle the specifics of connecting to and communicating with an MCP server. FastMCP provides several built-in transport implementations for common connection methods.

While the `Client` often infers the correct transport automatically (see [Client Overview](https://gofastmcp.com/clients/client#transport-inference)), you can also instantiate transports explicitly for more control.

[​

](https://gofastmcp.com/clients/transports#network-transports)
Network Transports
-------------------------------------------------------------------------------------

These transports connect to servers running over a network, typically long-running services accessible via URLs.

### [​

](https://gofastmcp.com/clients/transports#streamable-http)
Streamable HTTP

`New in version: 2.3.0
`

-   **Class:** `fastmcp.client.transports.StreamableHttpTransport`
-   **Inferred From:** `http://` or `https://` URLs (default for HTTP URLs as of v2.3.0)
-   **Use Case:** Connecting to persistent MCP servers exposed over HTTP/S using FastMCP's `mcp.run(transport="streamable-http")` mode.

Streamable HTTP is the recommended transport for web-based deployments, providing efficient bidirectional communication over HTTP.

Copy

```
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

http_url = "http://localhost:8000/mcp"

# Option 1: Inferred transport (default for HTTP URLs)
client_inferred = Client(http_url)

# Option 2: Explicit transport (e.g., to add custom headers)
headers = {"Authorization": "Bearer mytoken"}
transport_explicit = StreamableHttpTransport(url=http_url, headers=headers)
client_explicit = Client(transport_explicit)

async def use_streamable_http_client(client):
    async with client:
        tools = await client.list_tools()
        print(f"Connected via Streamable HTTP, found tools: {tools}")

# asyncio.run(use_streamable_http_client(client_inferred))
# asyncio.run(use_streamable_http_client(client_explicit))

```

### [​

](https://gofastmcp.com/clients/transports#sse-server-sent-events)
SSE (Server-Sent Events)

-   **Class:** `fastmcp.client.transports.SSETransport`
-   **Inferred From:** Not automatically inferred for most HTTP URLs (as of v2.3.0)
-   **Use Case:** Connecting to MCP servers using Server-Sent Events, often using FastMCP's `mcp.run(transport="sse")` mode.

While SSE is still supported, Streamable HTTP is the recommended transport for new web-based deployments.

Copy

```
from fastmcp import Client
from fastmcp.client.transports import SSETransport

sse_url = "http://localhost:8000/sse"

# Since v2.3.0, HTTP URLs default to StreamableHttpTransport,
# so you must explicitly use SSETransport for SSE connections
transport_explicit = SSETransport(url=sse_url)
client_explicit = Client(transport_explicit)

async def use_sse_client(client):
    async with client:
        tools = await client.list_tools()
        print(f"Connected via SSE, found tools: {tools}")

# asyncio.run(use_sse_client(client_explicit))

```

[​

](https://gofastmcp.com/clients/transports#stdio-transports)
Stdio Transports
---------------------------------------------------------------------------------

These transports manage an MCP server running as a subprocess, communicating with it via standard input (stdin) and standard output (stdout). This is the standard mechanism used by clients like Claude Desktop.

### [​

](https://gofastmcp.com/clients/transports#python-stdio)
Python Stdio

-   **Class:** `fastmcp.client.transports.PythonStdioTransport`
-   **Inferred From:** Paths to `.py` files.
-   **Use Case:** Running a Python-based MCP server script (like one using FastMCP or the base `mcp` library) in a subprocess.

This is the most common way to interact with local FastMCP servers during development or when integrating with tools that expect to launch a server script.

Copy

```
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

server_script = "my_mcp_server.py" # Assumes this file exists and runs mcp.run()

# Option 1: Inferred transport
client_inferred = Client(server_script)

# Option 2: Explicit transport (e.g., to use a specific python executable or add args)
transport_explicit = PythonStdioTransport(
    script_path=server_script,
    python_cmd="/usr/bin/python3.11", # Specify python version
    # args=["--some-server-arg"], # Pass args to the script
    # env={"MY_VAR": "value"},   # Set environment variables
    # cwd="/path/to/run/in"       # Set working directory
)
client_explicit = Client(transport_explicit)

async def use_stdio_client(client):
    async with client:
        tools = await client.list_tools()
        print(f"Connected via Python Stdio, found tools: {tools}")

# asyncio.run(use_stdio_client(client_inferred))
# asyncio.run(use_stdio_client(client_explicit))

```

The server script (`my_mcp_server.py` in the example) *must* include logic to start the MCP server and listen on stdio, typically via `mcp.run()` or `fastmcp.server.run()`. The `Client` only launches the script; it doesn't inject the server logic.

### [​

](https://gofastmcp.com/clients/transports#node-js-stdio)
Node.js Stdio

-   **Class:** `fastmcp.client.transports.NodeStdioTransport`
-   **Inferred From:** Paths to `.js` files.
-   **Use Case:** Running a Node.js-based MCP server script in a subprocess.

Similar to the Python transport, but for JavaScript servers.

Copy

```
from fastmcp import Client
from fastmcp.client.transports import NodeStdioTransport

node_server_script = "my_mcp_server.js" # Assumes this JS file starts an MCP server on stdio

# Option 1: Inferred transport
client_inferred = Client(node_server_script)

# Option 2: Explicit transport
transport_explicit = NodeStdioTransport(
    script_path=node_server_script,
    node_cmd="node" # Or specify path to Node executable
)
client_explicit = Client(transport_explicit)

# Usage is the same as other clients
# async with client_explicit:
#    tools = await client_explicit.list_tools()

```

### [​

](https://gofastmcp.com/clients/transports#uvx-stdio-experimental)
UVX Stdio (Experimental)

-   **Class:** `fastmcp.client.transports.UvxStdioTransport`
-   **Inferred From:** Not automatically inferred. Must be instantiated explicitly.
-   **Use Case:** Running an MCP server packaged as a Python tool using [`uvx`](https://docs.astral.sh/uv/reference/cli/#uvx) (part of the `uv` toolchain). This allows running tools without explicitly installing them into the current environment.

This is useful for executing MCP servers distributed as command-line tools or packages.

Copy

```
from fastmcp.client.transports import UvxStdioTransport

# Example: Run a hypothetical 'cloud-analyzer-mcp' tool via uvx
# Assume this tool, when run, starts an MCP server on stdio
transport = UvxStdioTransport(
    tool_name="cloud-analyzer-mcp",
    # from_package="cloud-analyzer-cli", # Optionally specify package if tool name differs
    # with_packages=["boto3", "requests"], # Add dependencies if needed
    # tool_args=["--config", "prod.yaml"] # Pass args to the tool itself
)
client = Client(transport)

# async with client:
#     analysis = await client.call_tool("analyze_bucket", {"name": "my-data"})

```

### [​

](https://gofastmcp.com/clients/transports#npx-stdio-experimental)
NPX Stdio (Experimental)

-   **Class:** `fastmcp.client.transports.NpxStdioTransport`
-   **Inferred From:** Not automatically inferred. Must be instantiated explicitly.
-   **Use Case:** Running an MCP server packaged as an NPM package using `npx`.

Similar to `UvxStdioTransport`, but for the Node.js ecosystem.

Copy

```
from fastmcp.client.transports import NpxStdioTransport

# Example: Run a hypothetical 'npm-mcp-server-package' via npx
transport = NpxStdioTransport(
    package="npm-mcp-server-package",
    # args=["--port", "stdio"] # Args passed to the package script
)
client = Client(transport)

# async with client:
#     response = await client.call_tool("get_npm_data", {})

```

[​

](https://gofastmcp.com/clients/transports#in-memory-transports)
In-Memory Transports
-----------------------------------------------------------------------------------------

### [​

](https://gofastmcp.com/clients/transports#fastmcp-transport)
FastMCP Transport

-   **Class:** `fastmcp.client.transports.FastMCPTransport`
-   **Inferred From:** An instance of `fastmcp.server.FastMCP`.
-   **Use Case:** Connecting directly to a `FastMCP` server instance running in the *same Python process*.

This is extremely useful for:

-   **Testing:** Writing unit or integration tests for your FastMCP server without needing subprocesses or network connections.
-   **Embedding:** Using an MCP server as a component within a larger application.

Copy

```
from fastmcp import FastMCP, Client
from fastmcp.client.transports import FastMCPTransport

# 1. Create your FastMCP server instance
server = FastMCP(name="InMemoryServer")
@server.tool()
def ping(): return "pong"

# 2. Create a client pointing directly to the server instance
# Option A: Inferred
client_inferred = Client(server)

# Option B: Explicit
transport_explicit = FastMCPTransport(mcp=server)
client_explicit = Client(transport_explicit)

# 3. Use the client (no subprocess or network involved)
async def test_in_memory():
    async with client_inferred: # Or client_explicit
        result = await client_inferred.call_tool("ping")
        print(f"In-memory call result: {result[0].text}") # Output: pong

# asyncio.run(test_in_memory())

```

Communication happens through efficient in-memory queues, making it very fast.

[​

](https://gofastmcp.com/clients/transports#choosing-a-transport)
Choosing a Transport
-----------------------------------------------------------------------------------------

-   **Local Development/Testing:** Use `PythonStdioTransport` (inferred from `.py` files) or `FastMCPTransport` (for same-process testing).
-   **Connecting to Remote/Persistent Servers:** Use `StreamableHttpTransport` (recommended, default for HTTP URLs) or `SSETransport` (legacy option).
-   **Running Packaged Tools:** Use `UvxStdioTransport` (Python/uv) or `NpxStdioTransport` (Node/npm) if you need to run MCP servers without local installation.
-   **Integrating with Claude Desktop (or similar):** These tools typically expect to run a Python script, so your server should be runnable via `python your_server.py`, making `PythonStdioTransport` the relevant mechanism on the client side.
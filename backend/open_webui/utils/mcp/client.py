import asyncio
from datetime import timedelta
from typing import Optional, Callable
from contextlib import AsyncExitStack

import anyio

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
import httpx
from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL


def create_insecure_httpx_client(headers=None, timeout=None, auth=None):
    """Create an httpx AsyncClient with SSL verification disabled.

    Note: verify=False must be passed at construction time because httpx
    configures the SSL context during __init__. Setting client.verify = False
    after construction does not affect the underlying transport's SSL context.
    """
    kwargs = {
        "follow_redirects": True,
        "verify": False,
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    if headers is not None:
        kwargs["headers"] = headers
    if auth is not None:
        kwargs["auth"] = auth
    return httpx.AsyncClient(**kwargs)


class MCPClient:
    def __init__(self, elicitation_callback: Optional[Callable] = None):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None
        self._elicitation_callback = elicitation_callback

    async def connect(self, url: str, headers: Optional[dict] = None):
        async with AsyncExitStack() as exit_stack:
            try:
                if AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL:
                    self._streams_context = streamablehttp_client(url, headers=headers)
                else:
                    self._streams_context = streamablehttp_client(
                        url,
                        headers=headers,
                        httpx_client_factory=create_insecure_httpx_client,
                    )

                transport = await exit_stack.enter_async_context(self._streams_context)
                read_stream, write_stream, _ = transport

                session_kwargs = {
                    "read_timeout_seconds": timedelta(seconds=300),  # 5 min for elicitation
                }
                if self._elicitation_callback:
                    session_kwargs["elicitation_callback"] = self._elicitation_callback

                self._session_context = ClientSession(
                    read_stream, write_stream, **session_kwargs
                )  # pylint: disable=W0201

                self.session = await exit_stack.enter_async_context(
                    self._session_context
                )
                with anyio.fail_after(10):
                    await self.session.initialize()
                self.exit_stack = exit_stack.pop_all()
            except Exception as e:
                await asyncio.shield(self.disconnect())
                raise e

    async def list_tool_specs(self) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_tools()
        tools = result.tools

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description

            inputSchema = tool.inputSchema

            # TODO: handle outputSchema if needed
            outputSchema = getattr(tool, "outputSchema", None)

            tool_specs.append(
                {"name": name, "description": description, "parameters": inputSchema}
            )

        return tool_specs

    async def call_tool(
        self, function_name: str, function_args: dict
    ) -> Optional[dict]:
        import logging
        log = logging.getLogger("open_webui")

        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        log.info(f"[MCPClient] call_tool START: {function_name} args={function_args}")
        log.info(f"[MCPClient] session alive: {self.session is not None}, exit_stack: {self.exit_stack is not None}")

        # Detailed debug: check if write_stream.send blocks
        import time as _time
        from mcp.types import CallToolRequest, CallToolRequestParams, ClientRequest
        from mcp.shared.message import SessionMessage
        from mcp.types import JSONRPCMessage, JSONRPCRequest as _JSONRPCRequest

        session = self.session
        request_id = session._request_id
        session._request_id = request_id + 1

        request = ClientRequest(
            CallToolRequest(
                params=CallToolRequestParams(name=function_name, arguments=function_args)
            )
        )
        request_data = request.model_dump(by_alias=True, mode="json", exclude_none=True)

        jsonrpc_request = _JSONRPCRequest(
            jsonrpc="2.0",
            id=request_id,
            **request_data,
        )

        response_stream, response_stream_reader = anyio.create_memory_object_stream(1)
        session._response_streams[request_id] = response_stream

        try:
            msg = SessionMessage(message=JSONRPCMessage(jsonrpc_request))
            log.info(f"[MCPClient] About to write to _write_stream for {function_name} (request_id={request_id})")
            t0 = _time.monotonic()

            try:
                with anyio.fail_after(5):
                    await session._write_stream.send(msg)
                elapsed = _time.monotonic() - t0
                log.info(f"[MCPClient] _write_stream.send() completed in {elapsed:.3f}s for {function_name}")
            except TimeoutError:
                elapsed = _time.monotonic() - t0
                log.error(f"[MCPClient] _write_stream.send() TIMED OUT after {elapsed:.3f}s for {function_name}! post_writer is NOT reading.")
                raise RuntimeError(f"write_stream.send() timed out - post_writer dead for {function_name}")

            log.info(f"[MCPClient] Now waiting for response for {function_name} (timeout=300s)")
            t1 = _time.monotonic()
            try:
                with anyio.fail_after(300):
                    response_or_error = await response_stream_reader.receive()
                elapsed2 = _time.monotonic() - t1
                log.info(f"[MCPClient] Got response in {elapsed2:.3f}s for {function_name}")
            except TimeoutError:
                elapsed2 = _time.monotonic() - t1
                log.error(f"[MCPClient] Response TIMED OUT after {elapsed2:.3f}s for {function_name}")
                raise

            from mcp.types import JSONRPCError as _JSONRPCError, CallToolResult
            from mcp.shared.exceptions import McpError
            from mcp.types import ErrorData
            if isinstance(response_or_error, _JSONRPCError):
                raise McpError(response_or_error.error)
            else:
                result = CallToolResult.model_validate(response_or_error.result)
        finally:
            session._response_streams.pop(request_id, None)
            await response_stream.aclose()
            await response_stream_reader.aclose()

        log.info(f"[MCPClient] call_tool END: {function_name} result_type={type(result)}")
        if not result:
            raise Exception("No result returned from MCP tool call.")

        result_dict = result.model_dump(mode="json")
        result_content = result_dict.get("content", {})

        if result.isError:
            raise Exception(result_content)
        else:
            return result_content

    async def list_resources(self, cursor: Optional[str] = None) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_resources(cursor=cursor)
        if not result:
            raise Exception("No result returned from MCP list_resources call.")

        result_dict = result.model_dump()
        resources = result_dict.get("resources", [])

        return resources

    async def read_resource(self, uri: str) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.read_resource(uri)
        if not result:
            raise Exception("No result returned from MCP read_resource call.")
        result_dict = result.model_dump()

        return result_dict

    async def disconnect(self):
        # Clean up and close the session
        await self.exit_stack.aclose()

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()

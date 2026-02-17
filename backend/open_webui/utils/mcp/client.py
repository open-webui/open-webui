import asyncio
from typing import Optional
from contextlib import AsyncExitStack

import anyio

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
import httpx
from mcp.shared._httpx_utils import create_mcp_http_client
from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL


def create_insecure_httpx_client(headers=None, timeout=None, auth=None):
    client = create_mcp_http_client(headers=headers, timeout=timeout, auth=auth)
    client.verify = False
    return client


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

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

                self._session_context = ClientSession(
                    read_stream, write_stream
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
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.call_tool(function_name, function_args)
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

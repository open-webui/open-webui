import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(
        self, url: str, headers: Optional[dict] = None, auth: Optional[any] = None
    ):
        self._streams_context = streamablehttp_client(url, headers=headers, auth=auth)
        read_stream, write_stream, _ = (
            await self._streams_context.__aenter__()
        )  # pylint: disable=E1101

        self._session_context = ClientSession(
            read_stream, write_stream
        )  # pylint: disable=W0201
        self.session: ClientSession = (
            await self._session_context.__aenter__()
        )  # pylint: disable=C2801

        await self.session.initialize()

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
        return result.model_dump()

    async def disconnect(self):
        # Clean up and close the session
        if self.session:
            await self._session_context.__aexit__(
                None, None, None
            )  # pylint: disable=E1101
        if self._streams_context:
            await self._streams_context.__aexit__(
                None, None, None
            )  # pylint: disable=E1101
        self.session = None

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()

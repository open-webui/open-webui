import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(
        self,
        url: Optional[str] = None,
        headers: Optional[dict] = None,
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
    ):
        try:
            if command:
                server_params = StdioServerParameters(
                    command=command,
                    args=args or [],
                    env=env,
                )
                self._streams_context = stdio_client(server_params)
            elif url:
                self._streams_context = streamablehttp_client(url, headers=headers)
            else:
                raise ValueError("Either url or command must be provided")

            transport = await self.exit_stack.enter_async_context(self._streams_context)

            if command:
                read_stream, write_stream = transport
            else:
                # `streamablehttp_client()` return signature has changed across MCP
                # releases (either 2-tuple or 3-tuple). Handle both.
                try:
                    read_stream, write_stream = transport
                except ValueError:
                    read_stream, write_stream, _ = transport

            self._session_context = ClientSession(
                read_stream, write_stream
            )  # pylint: disable=W0201

            self.session = await self.exit_stack.enter_async_context(
                self._session_context
            )
            await self.session.initialize()
        except Exception as e:
            await self.disconnect()
            raise e

    async def list_tool_specs(self) -> Optional[list[dict]]:
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

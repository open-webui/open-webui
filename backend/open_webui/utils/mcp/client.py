import asyncio
from typing import Optional, List, Any
from contextlib import AsyncExitStack

import anyio

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
import httpx
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS
import mcp.types as types
from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
from open_webui.utils.mcp.models import (
    parse_tool_meta,
    is_tool_visible_to_model,
    is_tool_visible_to_app,
    get_tool_resource_uri,
)


# MCP Apps extension identifier per SEP-1865 specification
MCP_APPS_EXTENSION_ID = "io.modelcontextprotocol/ui"
MCP_APPS_MIME_TYPE = "text/html;profile=mcp-app"


class MCPAppsClientSession(ClientSession):
    """
    Extended ClientSession that announces MCP Apps capability during initialization.

    Per the MCP Apps specification (SEP-1865), clients must advertise support for
    the io.modelcontextprotocol/ui extension to receive UI metadata from servers.
    """

    def __init__(self, *args, enable_mcp_apps: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._enable_mcp_apps = enable_mcp_apps

    async def initialize(self) -> types.InitializeResult:
        """
        Initialize the MCP session with MCP Apps capability announcement.

        Overrides the base ClientSession.initialize() to include the
        io.modelcontextprotocol/ui extension in experimental capabilities.
        """
        # Import default callbacks from mcp.client.session
        from mcp.client.session import (
            _default_sampling_callback,
            _default_elicitation_callback,
            _default_list_roots_callback,
        )

        # Build sampling capability (same as base class)
        sampling = (
            (self._sampling_capabilities or types.SamplingCapability())
            if self._sampling_callback is not _default_sampling_callback
            else None
        )

        # Build elicitation capability (same as base class)
        elicitation = (
            types.ElicitationCapability(
                form=types.FormElicitationCapability(),
                url=types.UrlElicitationCapability(),
            )
            if self._elicitation_callback is not _default_elicitation_callback
            else None
        )

        # Build roots capability (same as base class)
        roots = (
            types.RootsCapability(listChanged=True)
            if self._list_roots_callback is not _default_list_roots_callback
            else None
        )

        # Build experimental capabilities with MCP Apps support
        experimental: dict[str, dict[str, Any]] | None = None
        if self._enable_mcp_apps:
            experimental = {
                MCP_APPS_EXTENSION_ID: {
                    "mimeTypes": [MCP_APPS_MIME_TYPE]
                }
            }

        result = await self.send_request(
            types.ClientRequest(
                types.InitializeRequest(
                    params=types.InitializeRequestParams(
                        protocolVersion=types.LATEST_PROTOCOL_VERSION,
                        capabilities=types.ClientCapabilities(
                            sampling=sampling,
                            elicitation=elicitation,
                            experimental=experimental,
                            roots=roots,
                            tasks=self._task_handlers.build_capability(),
                        ),
                        clientInfo=self._client_info,
                    ),
                )
            ),
            types.InitializeResult,
        )

        if result.protocolVersion not in SUPPORTED_PROTOCOL_VERSIONS:
            raise RuntimeError(f"Unsupported protocol version from the server: {result.protocolVersion}")

        self._server_capabilities = result.capabilities

        await self.send_notification(types.ClientNotification(types.InitializedNotification()))

        return result


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
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    async def connect(
        self, url: str, headers: Optional[dict] = None, enable_mcp_apps: bool = True
    ):
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

                self._session_context = MCPAppsClientSession(
                    read_stream, write_stream, enable_mcp_apps=enable_mcp_apps
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

    async def list_tool_specs(
        self, include_meta: bool = True, filter_for_model: bool = False
    ) -> Optional[List[dict]]:
        """
        List tool specifications from the MCP server.

        Args:
            include_meta: Include _meta field with UI metadata
            filter_for_model: If True, exclude app-only tools (visibility=["app"])

        Returns:
            List of tool specifications
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_tools()
        tools = result.tools

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description
            inputSchema = tool.inputSchema

            # Get meta if available (SDK field is 'meta', JSON representation is '_meta')
            meta = tool.meta
            if meta is not None:
                # Convert to dict if it's a model
                if hasattr(meta, "model_dump"):
                    meta = meta.model_dump(mode="json")

            # Build tool spec
            tool_spec = {
                "name": name,
                "description": description,
                "parameters": inputSchema,
            }

            # Include _meta if requested
            if include_meta and meta:
                tool_spec["_meta"] = meta

            # Filter for model visibility
            if filter_for_model and not is_tool_visible_to_model(tool_spec):
                continue

            tool_specs.append(tool_spec)

        return tool_specs

    async def list_tool_specs_for_app(self) -> Optional[List[dict]]:
        """
        List tool specifications visible to apps.

        Excludes model-only tools (visibility=["model"]).

        Returns:
            List of tool specifications callable by apps
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_tools()
        tools = result.tools

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description
            inputSchema = tool.inputSchema

            # Get meta if available (SDK field is 'meta', JSON representation is '_meta')
            meta = tool.meta
            if meta is not None:
                if hasattr(meta, "model_dump"):
                    meta = meta.model_dump(mode="json")

            tool_spec = {
                "name": name,
                "description": description,
                "parameters": inputSchema,
            }

            if meta:
                tool_spec["_meta"] = meta

            # Filter for app visibility
            if not is_tool_visible_to_app(tool_spec):
                continue

            tool_specs.append(tool_spec)

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

    async def list_resources(self, cursor: Optional[str] = None) -> Optional[list]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_resources(cursor=cursor)
        if not result:
            raise Exception("No result returned from MCP list_resources call.")

        result_dict = result.model_dump()
        resources = result_dict.get("resources", [])

        return resources

    async def read_resource(self, uri: str) -> Optional[list]:
        """
        Read a resource from the MCP server.

        Returns the contents array from the resource response.
        Each item typically has 'type' (text/blob), 'text' or 'data', and optional 'mimeType'.
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.read_resource(uri)
        if not result:
            raise Exception("No result returned from MCP read_resource call.")
        result_dict = result.model_dump()

        # Return the contents array
        return result_dict.get("contents", [])

    async def list_prompts(self, cursor: Optional[str] = None) -> Optional[list]:
        """
        List prompts from the MCP server.
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_prompts(cursor=cursor)
        if not result:
            return []

        result_dict = result.model_dump()
        return result_dict.get("prompts", [])

    async def disconnect(self):
        # Clean up and close the session
        if self.exit_stack is not None:
            await self.exit_stack.aclose()

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()

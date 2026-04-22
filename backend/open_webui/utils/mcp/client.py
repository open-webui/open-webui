import asyncio
import logging
from typing import Optional
from contextlib import AsyncExitStack

log = logging.getLogger(__name__)

import anyio

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
import httpx
from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL, AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER


def _build_httpx_client(headers=None, timeout=None, auth=None, verify=True):
    """Create an httpx AsyncClient for MCP transport.

    Falls back to AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER when the caller
    (i.e. the MCP SDK) does not supply an explicit timeout.

    Note: verify must be passed at construction time because httpx
    configures the SSL context during __init__. Setting client.verify = False
    after construction does not affect the underlying transport's SSL context.
    """
    kwargs = {
        'follow_redirects': True,
        'verify': verify,
    }
    if timeout is not None:
        kwargs['timeout'] = timeout
    elif AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER is not None:
        kwargs['timeout'] = float(AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER)
    if headers is not None:
        kwargs['headers'] = headers
    if auth is not None:
        kwargs['auth'] = auth
    return httpx.AsyncClient(**kwargs)


def create_httpx_client(headers=None, timeout=None, auth=None):
    return _build_httpx_client(headers=headers, timeout=timeout, auth=auth, verify=True)


async def create_insecure_httpx_client(headers=None, timeout=None, auth=None):
    return _build_httpx_client(headers=headers, timeout=timeout, auth=auth, verify=False)


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    async def connect(self, url: str, headers: Optional[dict] = None):
        async with AsyncExitStack() as exit_stack:
            try:
                self._streams_context = streamablehttp_client(
                    url,
                    headers=headers,
                    httpx_client_factory=create_httpx_client
                    if AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
                    else create_insecure_httpx_client,
                )

                transport = await exit_stack.enter_async_context(self._streams_context)
                read_stream, write_stream, _ = transport

                self._session_context = ClientSession(read_stream, write_stream)  # pylint: disable=W0201

                self.session = await exit_stack.enter_async_context(self._session_context)
                with anyio.fail_after(10):
                    await self.session.initialize()
                self.exit_stack = exit_stack.pop_all()
            except Exception as e:
                await asyncio.shield(self.disconnect())
                raise e

    async def list_tool_specs(self) -> Optional[dict]:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        result = await self.session.list_tools()
        tools = result.tools

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description

            inputSchema = tool.inputSchema

            # TODO: handle outputSchema if needed
            outputSchema = getattr(tool, 'outputSchema', None)

            tool_specs.append({'name': name, 'description': description, 'parameters': inputSchema})

        return tool_specs

    async def call_tool(self, function_name: str, function_args: dict) -> Optional[dict]:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        result = await self.session.call_tool(function_name, function_args)
        if not result:
            raise Exception('No result returned from MCP tool call.')

        result_dict = result.model_dump(mode='json')
        result_content = result_dict.get('content', {})

        if result.isError:
            raise Exception(result_content)
        else:
            return result_content

    async def list_resources(self, cursor: Optional[str] = None) -> Optional[dict]:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        result = await self.session.list_resources(cursor=cursor)
        if not result:
            raise Exception('No result returned from MCP list_resources call.')

        result_dict = result.model_dump()
        resources = result_dict.get('resources', [])

        return resources

    async def read_resource(self, uri: str) -> Optional[dict]:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        result = await self.session.read_resource(uri)
        if not result:
            raise Exception('No result returned from MCP read_resource call.')
        result_dict = result.model_dump()

        return result_dict

    async def disconnect(self):
        """Clean up and close the session.

        This method is idempotent — calling it multiple times or on a
        client that was never connected is safe.  It shields the close
        operation from CancelledError and adds a timeout so a hung MCP
        server cannot block the event loop indefinitely.
        """
        exit_stack = self.exit_stack
        if exit_stack is None:
            return

        # Prevent double-close from concurrent callers
        self.exit_stack = None
        self.session = None

        try:
            await asyncio.wait_for(
                asyncio.shield(exit_stack.aclose()),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            log.warning('MCPClient.disconnect() timed out after 5 s')
        except RuntimeError as exc:
            # The MCP SDK's streamable_http transport uses anyio task
            # groups and async generators internally.  When we close
            # a session that was interrupted mid-flight these can
            # raise RuntimeError ("aclose(): asynchronous generator is
            # already running" or "Attempted to exit cancel scope in a
            # different task").  Swallowing the error here prevents the
            # orphaned coroutines from spinning at 100 % CPU.
            log.debug('MCPClient.disconnect() suppressed RuntimeError: %s', exc)
        except Exception as exc:
            log.debug('MCPClient.disconnect() error: %s', exc)

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()

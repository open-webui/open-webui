import asyncio
import logging
from contextlib import AsyncExitStack

import anyio
import httpx
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER,
    MCP_INITIALIZE_TIMEOUT,
)

log = logging.getLogger(__name__)

MCP_CLIENT_CAPABILITIES_META_KEY = 'io.modelcontextprotocol/clientCapabilities'


class OpenWebUIClientSession(ClientSession):
    async def send_request(self, request, result_type, *args, **kwargs):
        """Advertise citation rendering support on every MCP request."""
        request_root = getattr(request, 'root', None)
        if request_root is not None:
            params = getattr(request_root, 'params', None)
            if params is None:
                params = types.RequestParams()
                request_root.params = params

            if isinstance(params, dict):
                existing_meta = dict(params.get('_meta') or {})
            else:
                existing_meta = params.meta.model_dump(exclude_none=True) if params.meta else {}
            client_capabilities = existing_meta.get(MCP_CLIENT_CAPABILITIES_META_KEY, {})
            citation_capabilities = client_capabilities.get('citations', {})
            updated_meta = {
                **existing_meta,
                MCP_CLIENT_CAPABILITIES_META_KEY: {
                    **client_capabilities,
                    'citations': {
                        **citation_capabilities,
                        'render': {},
                    },
                },
            }
            if isinstance(params, dict):
                params['_meta'] = updated_meta
            else:
                params.meta = types.RequestParams.Meta(**updated_meta)

        return await super().send_request(request, result_type, *args, **kwargs)


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
    # AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL may be True, False, or an
    # ssl.SSLContext (when a custom CA bundle path is configured).
    # httpx's verify= accepts bool | str | ssl.SSLContext, so all three work.
    ssl_setting = AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
    verify = ssl_setting if ssl_setting is not True else True
    return _build_httpx_client(headers=headers, timeout=timeout, auth=auth, verify=verify)


def create_insecure_httpx_client(headers=None, timeout=None, auth=None):
    return _build_httpx_client(headers=headers, timeout=timeout, auth=auth, verify=False)


class MCPClient:
    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = None

    async def connect(self, url: str, headers: dict | None = None):
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

                self._session_context = OpenWebUIClientSession(read_stream, write_stream)  # pylint: disable=W0201

                self.session = await exit_stack.enter_async_context(self._session_context)
                with anyio.fail_after(MCP_INITIALIZE_TIMEOUT):
                    await self.session.initialize()
                self.exit_stack = exit_stack.pop_all()
            except Exception as e:
                await self.disconnect()
                raise e

    async def list_tool_specs(self) -> dict | None:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        tools = []
        cursor = None
        while True:
            result = await self.session.list_tools(cursor=cursor)
            tools.extend(result.tools)
            cursor = result.nextCursor
            if cursor is None:
                break

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description

            inputSchema = tool.inputSchema

            # TODO: handle outputSchema if needed
            outputSchema = getattr(tool, 'outputSchema', None)

            tool_specs.append({'name': name, 'description': description, 'parameters': inputSchema})

        return tool_specs

    async def call_tool(self, function_name: str, function_args: dict) -> dict:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        result = await self.session.call_tool(function_name, function_args)
        if not result:
            raise Exception('No result returned from MCP tool call.')

        result_dict = result.model_dump(mode='json')
        content = result_dict.get('content')
        citations = result_dict.get('citations')

        return {
            'content': content if isinstance(content, list) else [],
            'citations': citations if isinstance(citations, list) else [],
            'isError': bool(result_dict.get('isError')),
        }

    async def list_resources(self, cursor: str | None = None) -> dict | None:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        result = await self.session.list_resources(cursor=cursor)
        if not result:
            raise Exception('No result returned from MCP list_resources call.')

        result_dict = result.model_dump()
        resources = result_dict.get('resources', [])

        return resources

    async def read_resource(self, uri: str) -> dict | None:
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
        client that was never connected is safe.
        """
        exit_stack = self.exit_stack
        if exit_stack is None:
            return

        # Prevent double-close from concurrent callers
        self.exit_stack = None
        self.session = None

        try:
            # IMPORTANT: Do NOT use asyncio.shield() or asyncio.wait_for()
            # because they create a new asyncio task, which violates the MCP SDK's
            # requirement that its TaskGroup be exited in the exact same task.
            # ALSO do NOT use anyio.CancelScope(shield=True) or anyio.fail_after(),
            # because they push a new cancel scope onto the task, violating LIFO
            # order when aclose() attempts to exit the inner TaskGroup.
            # We simply call aclose() directly. If the task is cancelled, the
            # sockets will eventually be cleaned up by garbage collection.
            await exit_stack.aclose()
        except asyncio.CancelledError as exc:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise
            log.debug('MCPClient.disconnect() suppressed internal cancellation: %s', exc)
        except RuntimeError as exc:
            log.debug('MCPClient.disconnect() suppressed RuntimeError: %s', exc)
        except Exception as exc:
            log.debug('MCPClient.disconnect() error: %s', exc)

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()

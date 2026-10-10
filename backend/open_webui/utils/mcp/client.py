import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Optional

log = logging.getLogger(__name__)

import anyio
import httpx
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER,
    MCP_INITIALIZE_TIMEOUT,
)
from open_webui.utils.json_codec import JSONCodec


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


class OAuthTokenAuth(httpx.Auth):
    """Resolve current credentials per request and recover from concurrent token rotation."""

    requires_request_body = True

    def __init__(self, get_headers):
        self.get_headers = get_headers

    async def async_auth_flow(self, request):
        headers = httpx.Headers(await self.get_headers())
        authorization = headers.get('Authorization')
        if not authorization:
            raise httpx.RequestError('No OAuth access token available', request=request)
        request.headers.update(headers)
        response = yield request

        if response.status_code == 401:
            headers = httpx.Headers(await self.get_headers())
            if headers.get('Authorization') and headers['Authorization'] != authorization:
                request.headers.update(headers)
                yield request


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    async def connect(self, url: str, headers: Optional[dict] = None, auth: Optional[httpx.Auth] = None):
        async with AsyncExitStack() as exit_stack:
            try:
                self._streams_context = streamablehttp_client(
                    url,
                    headers=headers,
                    auth=auth,
                    httpx_client_factory=create_httpx_client
                    if AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
                    else create_insecure_httpx_client,
                )

                transport = await exit_stack.enter_async_context(self._streams_context)
                read_stream, write_stream, _ = transport

                self._session_context = ClientSession(read_stream, write_stream)  # pylint: disable=W0201

                self.session = await exit_stack.enter_async_context(self._session_context)
                with anyio.fail_after(MCP_INITIALIZE_TIMEOUT):
                    await self.session.initialize()
                self.exit_stack = exit_stack.pop_all()
            except Exception as e:
                await self.disconnect()
                raise e

    async def list_tool_specs(self) -> Optional[dict]:
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

    async def call_tool(self, function_name: str, function_args: dict) -> list[dict]:
        if not self.session:
            raise RuntimeError('MCP client is not connected.')

        tool_call_timeout = None
        if AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER is not None and AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER > 0:
            tool_call_timeout = timedelta(seconds=AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER)

        result = await self.session.call_tool(function_name, function_args, read_timeout_seconds=tool_call_timeout)
        if not result:
            raise Exception('No result returned from MCP tool call.')

        result_dict = result.model_dump(mode='json')
        result_content = result_dict['content']

        if result.isError:
            raise Exception(result_content)

        structured_content = result_dict.get('structuredContent')
        if structured_content is None:
            return result_content

        # Compare serialized JSON: Python equality treats True and 1 as the same value.
        structured_json = JSONCodec.dumps(structured_content, sort_keys=True)
        texts = [item['text'] for item in result_content if item['type'] == 'text']
        text_jsons = []
        for text in texts:
            try:
                text_content = JSONCodec.loads(text)
            except JSONCodec.JSONDecodeError:
                text_content = text
            text_json = JSONCodec.dumps(text_content, sort_keys=True)
            if text_json == structured_json:
                return result_content
            text_jsons.append(text_json)

        # FastMCP wraps scalar/list results while keeping their original text blocks.
        values = structured_content.get('result')
        values = values if isinstance(values, list) else [values]
        if (
            structured_content.keys() == {'result'}
            and texts
            and len(texts) == len(values)
            and all(
                text == value or text_json == JSONCodec.dumps(value, sort_keys=True)
                for text, text_json, value in zip(texts, text_jsons, values)
            )
        ):
            return result_content

        result_content.append({'type': 'text', 'text': structured_json})
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

import asyncio
import logging
import math
from typing import Optional
from urllib.parse import urlsplit

import httpx2
from jsonschema import Draft202012Validator, FormatChecker
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import ElicitRequestFormParams, ElicitResult
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER,
    MCP_INITIALIZE_TIMEOUT,
)
from open_webui.utils.json_codec import JSONCodec
from referencing import Registry

log = logging.getLogger(__name__)


def create_httpx_client(headers=None, auth=None):
    """Create the httpx2 AsyncClient that carries MCP traffic.

    Note: verify must be passed at construction time because httpx2
    configures the SSL context during __init__. AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
    may be True, False, or an ssl.SSLContext (when a custom CA bundle path is
    configured); verify= accepts all three.

    Redirects are not configured here: the MCP SDK follows same-origin
    redirects itself and ignores the client's follow_redirects setting.
    """
    return httpx2.AsyncClient(
        headers=headers,
        auth=auth,
        verify=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
        # The SDK's transport defaults: reads stay open for long-lived SSE streams.
        timeout=httpx2.Timeout(30, read=300),
    )


class OAuthTokenAuth(httpx2.Auth):
    """Resolve current credentials per request and recover from concurrent token rotation."""

    requires_request_body = True

    def __init__(self, get_headers):
        self.get_headers = get_headers

    async def async_auth_flow(self, request):
        headers = httpx2.Headers(await self.get_headers())
        authorization = headers.get('Authorization')
        if not authorization:
            raise httpx2.RequestError('No OAuth access token available', request=request)
        request.headers.update(headers)
        response = yield request

        if response.status_code == 401:
            headers = httpx2.Headers(await self.get_headers())
            if headers.get('Authorization') and headers['Authorization'] != authorization:
                request.headers.update(headers)
                yield request


class MCPClient:
    def __init__(self, event_caller=None, server_name=''):
        self.client: Optional[Client] = None
        self.session_task: Optional[asyncio.Task] = None
        self.event_caller = event_caller
        self.server_name = server_name
        self.instructions: Optional[str] = None

    async def elicit(self, context, params):
        try:
            if isinstance(params, ElicitRequestFormParams):
                Draft202012Validator.check_schema(params.requested_schema)
            else:
                url = urlsplit(params.url)
                if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
                    return ElicitResult(action='cancel')

            response = await self.event_caller(
                {
                    'type': 'request:elicitation',
                    'data': {
                        **params.model_dump(
                            mode='json', by_alias=True, include={'mode', 'message', 'requested_schema', 'url'}
                        ),
                        'server_name': self.server_name,
                    },
                }
            )
            if not isinstance(response, dict) or response.get('action') not in ('accept', 'decline', 'cancel'):
                return ElicitResult(action='cancel')

            content = None
            if response['action'] == 'accept' and isinstance(params, ElicitRequestFormParams):
                content = response.get('content')
                # Never fetch server-supplied schema references or coerce user answers.
                Draft202012Validator(
                    params.requested_schema, format_checker=FormatChecker(), registry=Registry()
                ).validate(content)
            return ElicitResult(action=response['action'], content=content)
        except Exception as e:
            log.warning('MCP elicitation failed: %s', type(e).__name__)
            return ElicitResult(action='cancel')

    async def connect(self, url: str, headers: Optional[dict] = None, auth: Optional[httpx2.Auth] = None):
        # A failed request makes the SDK cancel the task that opened the session, so it gets its own task.
        connected = asyncio.get_running_loop().create_future()
        self.session_task = asyncio.create_task(self.run_session(url, headers, auth, connected))
        try:
            await connected
        except BaseException:
            await self.disconnect()
            raise

    async def run_session(
        self, url: str, headers: Optional[dict], auth: Optional[httpx2.Auth], connected: asyncio.Future
    ) -> None:
        try:
            async with create_httpx_client(headers=headers, auth=auth) as http_client:
                # mode='auto' (the default) probes server/discover for the stateless
                # 2026-07-28 protocol and falls back to the initialize handshake on
                # legacy servers. The read timeout bounds that handshake and every
                # later request that does not set its own; the SDK caps the probe itself.
                async with Client(
                    streamable_http_client(url, http_client=http_client),
                    read_timeout_seconds=MCP_INITIALIZE_TIMEOUT,
                    elicitation_callback=self.elicit if self.event_caller else None,
                ) as client:
                    self.client = client
                    self.instructions = client.instructions
                    connected.set_result(None)
                    await asyncio.sleep(math.inf)
        except Exception as e:
            if connected.done():
                log.exception("Lost connection to MCP server '%s'", self.server_name)
            else:
                connected.set_exception(e)
        finally:
            self.client = None
            if not connected.done():
                connected.set_exception(RuntimeError('MCP client failed to connect.'))

    async def list_tool_specs(self) -> Optional[dict]:
        if not self.client:
            raise RuntimeError('MCP client is not connected.')

        tools = []
        cursor = None
        while True:
            result = await self.client.list_tools(cursor=cursor)
            tools.extend(result.tools)
            cursor = result.next_cursor
            if cursor is None:
                break

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description

            input_schema = tool.input_schema

            # TODO: handle output_schema if needed

            tool_specs.append({'name': name, 'description': description, 'parameters': input_schema})

        return tool_specs

    async def call_tool(self, function_name: str, function_args: dict) -> list[dict]:
        if not self.client:
            raise RuntimeError('MCP client is not connected.')

        # math.inf is the SDK's own "no timeout"; None would fall back to MCP_INITIALIZE_TIMEOUT.
        tool_call_timeout = math.inf
        if AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER is not None and AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER > 0:
            tool_call_timeout = AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER

        result = await self.client.call_tool(function_name, function_args, read_timeout_seconds=tool_call_timeout)
        if not result:
            raise Exception('No result returned from MCP tool call.')

        result_dict = result.model_dump(mode='json', by_alias=True)
        result_content = result_dict['content']
        texts = [item['text'] for item in result_content if item['type'] == 'text']

        if result.is_error:
            raise Exception('\n'.join(texts) or 'MCP tool call returned an error.')

        structured_content = result_dict.get('structuredContent')
        if structured_content is None:
            return result_content

        # Compare serialized JSON: Python equality treats True and 1 as the same value.
        structured_json = JSONCodec.dumps(structured_content, sort_keys=True)
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
        # The standalone fastmcp package sends the whole list as one text block.
        if structured_content.keys() == {'result'} and text_jsons == [JSONCodec.dumps(values, sort_keys=True)]:
            return result_content
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
        if not self.client:
            raise RuntimeError('MCP client is not connected.')

        result = await self.client.list_resources(cursor=cursor)
        if not result:
            raise Exception('No result returned from MCP list_resources call.')

        result_dict = result.model_dump(by_alias=True)
        resources = result_dict.get('resources', [])

        return resources

    async def read_resource(self, uri: str) -> Optional[dict]:
        if not self.client:
            raise RuntimeError('MCP client is not connected.')

        result = await self.client.read_resource(uri)
        if not result:
            raise Exception('No result returned from MCP read_resource call.')
        result_dict = result.model_dump(by_alias=True)

        return result_dict

    async def disconnect(self):
        """Clean up and close the session.

        This method is idempotent — calling it multiple times or on a
        client that was never connected is safe.
        """
        session_task = self.session_task
        if session_task is None:
            return

        # Prevent double-close from concurrent callers
        self.session_task = None
        self.client = None
        session_task.cancel()

        try:
            await session_task
        except asyncio.CancelledError:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise
        except Exception as exc:
            log.debug('MCPClient.disconnect() error: %s', exc)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.disconnect()

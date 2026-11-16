"""MCP transports over Tether. Commands, endpoints and credentials stay on the device."""

import time
from contextlib import asynccontextmanager

import aiohttp
import anyio
import httpx2
import mcp_types
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.message import SessionMessage
from open_webui.models.auth_sessions import AuthSessions
from open_webui.utils.tether import CHUNK, MAX_MESSAGE, RelayClient, RelayInterrupted, hub


class Target:
    def __init__(self, user_id, device_id, service, transport):
        self.user_id, self.device_id, self.service, self.transport = user_id, device_id, service, transport
        self.connection = None
        self.revision = None

    async def check(self):
        presence = await hub.presence(self.user_id, self.device_id)
        if not presence or presence['user'] != self.user_id or self.service not in presence.get('services', []):
            raise RelayInterrupted('MCP service unavailable')
        item = next(
            (
                item
                for item in presence.get('connections', [])
                if item['service'] == self.service and item['type'] == 'mcp' and item.get('transport') == self.transport
            ),
            None,
        )
        if item is None:
            raise RelayInterrupted('MCP service unavailable')
        revision = item.get('revision', '')
        if self.revision is not None and self.revision != revision:
            raise RelayInterrupted('MCP configuration changed; reconnect before making another call')
        self.revision = revision
        row = await AuthSessions.get(presence['session'])
        if not row or row.user_id != self.user_id or row.refresh_token_id is None or row.expires_at <= time.time():
            raise RelayInterrupted('MCP sign-in expired')
        if self.connection is not None and self.connection != presence['connection']:
            raise RelayInterrupted('MCP connection changed; reconnect before making another call')
        self.connection = presence['connection']


class ResponseStream(httpx2.AsyncByteStream):
    def __init__(self, response):
        self.response = response

    async def __aiter__(self):
        try:
            async for data in self.response.iter_any():
                yield data
        except RelayInterrupted as error:
            raise httpx2.ReadError(str(error)) from error

    async def aclose(self):
        await self.response.close()


class MCPRelayClient(RelayClient):
    def __init__(self, target):
        super().__init__(target.user_id, target.service)
        self.target = target

    async def _open(self, device):
        stream = await super()._open(device)
        if stream.presence['connection'] != self.target.connection:
            await stream.close()
            raise RelayInterrupted('MCP connection changed before the request was sent')
        return stream


class TetherHTTPTransport(httpx2.AsyncBaseTransport):
    def __init__(self, target):
        self.target = target
        self.relay = MCPRelayClient(target)

    async def handle_async_request(self, request):
        # A synthetic endpoint keeps local URLs out of the backend. Reject redirects
        # and alternate paths even when the MCP SDK follows them itself.
        if str(request.url) != 'http://tether.invalid/':
            raise httpx2.RequestError('Only the configured MCP endpoint is available', request=request)
        await self.target.check()
        timeout = request.extensions.get('timeout', {})
        try:
            response = await self.relay.request(
                request.method,
                f'tether://{self.target.device_id}/',
                headers=dict(request.headers),
                data=request.stream,
                idempotent=False,
                revision=self.target.revision,
                timeout=aiohttp.ClientTimeout(total=None, sock_read=timeout.get('read', 300)),
            )
        except RelayInterrupted as error:
            raise httpx2.ReadError(str(error), request=request) from error
        return httpx2.Response(response.status, headers=dict(response.headers), stream=ResponseStream(response))

    async def aclose(self):
        await self.relay.close()


async def read_stdio(stream, incoming_writer):
    buffer = bytearray()
    async with incoming_writer:
        while True:
            header, data = await stream.receive()
            if header['type'] == 'end':
                if buffer:
                    raise ValueError('Incomplete MCP message')
                return
            if header['type'] != 'data':
                raise ValueError('Invalid MCP stream')
            buffer.extend(data)
            if len(buffer) > MAX_MESSAGE:
                raise ValueError('MCP message too large')
            # Replenish credit before waiting for a complete line: messages may
            # exceed the relay window, but never the separate framing limit.
            await stream.consumed(len(data))
            while b'\n' in buffer:
                line, _, rest = buffer.partition(b'\n')
                buffer = bytearray(rest)
                message = mcp_types.jsonrpc_message_adapter.validate_json(line, by_name=False)
                await incoming_writer.send(SessionMessage(message))


@asynccontextmanager
async def stdio_transport(target):
    await target.check()
    stream = await hub.open(target.user_id, target.device_id, target.service)
    if stream.presence['connection'] != target.connection:
        await stream.close()
        raise RelayInterrupted('Connection changed before the process was started')
    incoming_writer, incoming = anyio.create_memory_object_stream(0)
    outgoing, outgoing_reader = anyio.create_memory_object_stream(0)

    async def write():
        async with outgoing_reader:
            async for message in outgoing_reader:
                await target.check()
                data = (message.message.model_dump_json(by_alias=True, exclude_unset=True) + '\n').encode()
                if len(data) > MAX_MESSAGE:
                    raise ValueError('MCP message too large')
                for offset in range(0, len(data), CHUNK):
                    await stream.send('data', data[offset : offset + CHUNK])

    try:
        with anyio.fail_after(15):
            await stream.send('stdio-open', service=target.service, revision=target.revision)
            header, _ = await stream.receive()
            if header['type'] != 'stdio-ready':
                raise ValueError('MCP process did not start')
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(read_stdio, stream, incoming_writer)
            tasks.start_soon(write)
            try:
                yield incoming, outgoing
            finally:
                tasks.cancel_scope.cancel()
    finally:
        with anyio.CancelScope(shield=True):
            await stream.close()
            await incoming.aclose()
            await incoming_writer.aclose()
            await outgoing.aclose()
            await outgoing_reader.aclose()


@asynccontextmanager
async def tether_transport(user_id, device_id, service, transport):
    target = Target(user_id, device_id, service, transport)
    if transport == 'stdio':
        async with stdio_transport(target) as streams:
            yield streams
    elif transport == 'streamable-http':
        async with httpx2.AsyncClient(
            transport=TetherHTTPTransport(target), timeout=httpx2.Timeout(30, read=300)
        ) as http:
            async with streamable_http_client(
                'http://tether.invalid/', http_client=http, max_sse_event_size=None
            ) as streams:
                yield streams
    else:
        raise ValueError('Unsupported MCP transport')

"""Reconnectable carrier for native agent JSONL, through direct terminals or Tether."""

import asyncio
import contextlib
import json
import time

import aiohttp
from fastapi import HTTPException

from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL
from open_webui.utils.terminals import get_terminal_server_url, resolve_terminal_connection
from open_webui.utils.tether import get_terminal_client


class TerminalTransport:
    def __init__(self, connection, headers, cookies, user_id):
        self.url = get_terminal_server_url(connection)
        self.headers, self.cookies, self.user_id = headers, cookies, user_id
        self.session_id = None
        self.socket = None
        self.task = None
        self.cursor = 0
        self.sequence = 0
        self.pending = {}
        self.messages = asyncio.Queue(maxsize=128)
        self.lock = asyncio.Lock()
        self.ready = asyncio.Event()
        self.closed = False
        self.failure = None

    @classmethod
    async def resolve(cls, request, user, metadata):
        resolved = await resolve_terminal_connection(request, user, metadata)
        if not resolved:
            raise ValueError('Select an accessible server or Tether terminal to use agents')
        return cls(*resolved, user.id)

    async def request(self, method, path, body=None):
        async with get_terminal_client(
            self.url, self.user_id, timeout=aiohttp.ClientTimeout(total=30), trust_env=True
        ) as client:
            async with client.request(
                method,
                self.url + path,
                headers=self.headers,
                cookies=self.cookies,
                json=body,
                ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                allow_redirects=False,
            ) as response:
                data = await response.json()
                if response.status >= 400:
                    raise ValueError(data.get('detail', 'Agent environment request failed'))
                return data

    async def start(self, provider, options):
        session = await self.request('POST', f'/agents/{provider}/sessions', options)
        self.session_id = session['id']
        self.task = asyncio.create_task(self._pump())
        return session

    async def _send(self, frame):
        encoded = json.dumps(frame)
        if len(encoded.encode()) > 16 * 1024 * 1024:
            raise ValueError('Agent protocol frame is too large')
        if self.socket is None:
            raise ConnectionError('Agent socket disconnected')
        await self.socket.send_str(encoded)

    async def _pump(self):
        disconnected = time.monotonic()
        try:
            while not self.closed:
                try:
                    async with get_terminal_client(
                        self.url,
                        self.user_id,
                        timeout=aiohttp.ClientTimeout(total=None, connect=30),
                        trust_env=True,
                        cookies=self.cookies,
                    ) as client:
                        async with client.ws_connect(
                            self.url + f'/agents/sessions/{self.session_id}/connect',
                            headers=self.headers,
                            ssl=AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL,
                            max_msg_size=20 * 1024 * 1024,
                            heartbeat=20,
                        ) as ws:
                            async with self.lock:
                                self.socket = ws
                                token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                                await self._send({'type': 'auth', 'token': token, 'cursor': self.cursor})
                                for sequence, (data, _) in self.pending.items():
                                    await self._send({'type': 'input', 'sequence': sequence, 'data': data})
                                self.ready.set()
                            async for message in ws:
                                if message.type != aiohttp.WSMsgType.TEXT:
                                    raise ConnectionError('Agent socket disconnected')
                                frame = json.loads(message.data)
                                disconnected = time.monotonic()
                                if frame['type'] == 'ack':
                                    pending = self.pending.pop(frame['sequence'], None)
                                    if pending:
                                        pending[1].set_result(None)
                                elif frame['type'] == 'output':
                                    if frame['sequence'] > self.cursor:
                                        if frame['sequence'] != self.cursor + 1:
                                            raise ValueError('Agent protocol output was lost')
                                        await self.messages.put(json.loads(frame['data']))
                                        self.cursor = frame['sequence']
                                    await self._send({'type': 'ack', 'sequence': self.cursor})
                                elif frame['type'] == 'exit':
                                    raise ValueError(frame.get('error') or f'Agent exited ({frame.get("code")})')
                            raise ConnectionError('Agent socket disconnected')
                except (ConnectionError, aiohttp.ClientError, TimeoutError, HTTPException) as exc:
                    if isinstance(exc, HTTPException) and exc.status_code not in {404, 503}:
                        raise
                    self.ready.clear()
                    self.socket = None
                    if time.monotonic() - disconnected > 60:
                        raise ConnectionError('Agent environment disconnected. Reconnect before continuing this chat.')
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.failure = exc
            self.ready.set()
            for _, future in self.pending.values():
                if not future.done():
                    future.set_exception(exc)
            await self.messages.put(exc)

    def raise_if_failed(self):
        if self.failure:
            raise self.failure

    async def write(self, data):
        if len(data.encode()) > 16 * 1024 * 1024:
            raise ValueError('Agent input is too large')
        await asyncio.wait_for(self.ready.wait(), 65)
        self.raise_if_failed()
        async with self.lock:
            self.sequence += 1
            sequence = self.sequence
            future = asyncio.get_running_loop().create_future()
            self.pending[sequence] = (data, future)
            try:
                await self._send({'type': 'input', 'sequence': sequence, 'data': data})
            except (ConnectionError, aiohttp.ClientError):
                if self.socket:
                    await self.socket.close()
            except Exception:
                self.pending.pop(sequence, None)
                future.cancel()
                raise
        try:
            await asyncio.wait_for(asyncio.shield(future), 65)
        finally:
            self.pending.pop(sequence, None)
            if not future.done():
                future.cancel()

    async def read_messages(self):
        while True:
            message = await self.messages.get()
            if isinstance(message, Exception):
                raise message
            yield message

    async def close(self):
        self.closed = True
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        for _, future in self.pending.values():
            if not future.done():
                future.cancel()
        if self.session_id:
            with contextlib.suppress(Exception):
                await self.request('DELETE', f'/agents/sessions/{self.session_id}')

    async def end_input(self):
        if self.socket:
            await self._send({'type': 'eof'})

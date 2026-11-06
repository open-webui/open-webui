"""Persist native agent output and approvals using WebUI chat messages."""

import asyncio
import copy
import json
import time
from uuid import uuid4

from open_webui.models.chats import Chats
from open_webui.socket.main import get_event_emitter
from open_webui.utils.auth import create_token


class Output:
    """Use WebUI's persisted output cards; provider runners retain native item data."""

    def __init__(self, metadata, user, check_connection):
        self.metadata, self.user = metadata, user
        self.check_connection = check_connection
        self.items = []
        self.state = {}
        self.content = ''
        self.usage = None
        self.emitter = None
        self.last_flush = 0
        self.lock = asyncio.Lock()

    async def flush(self, done=False, force=False):
        if not force and not done and time.monotonic() - self.last_flush < 0.1:
            return
        async with self.lock:
            async with Chats.edit_message_output(self.metadata['chat_id'], self.metadata['message_id']) as message:
                if message is None:
                    raise ValueError('Agent chat message no longer exists')
                # Approval responses arrive through another request/worker. Never overwrite them.
                resolutions = {
                    i.get('call_id'): i.get('agent_resolution')
                    for i in message.get('output', [])
                    if i.get('agent_resolution')
                }
                for item in self.items:
                    if item.get('call_id') in resolutions:
                        item['agent_resolution'] = resolutions[item['call_id']]
                message.update(content=self.content, output=copy.deepcopy(self.items), done=done)
                if self.usage is not None:
                    message['usage'] = self.usage
                meta = dict(message.get('meta') or {})
                meta['agent'] = create_token(
                    {'purpose': 'terminal-agent', 'user': self.user.id, 'chat': self.metadata['chat_id'], **self.state}
                )
                if done:
                    meta['response_ended_at'] = time.time()
                message['meta'] = meta
            if self.emitter is None:
                self.emitter = await get_event_emitter(self.metadata, update_db=False)
            await self.emitter(
                {
                    'type': 'chat:completion',
                    'data': {
                        'content': self.content,
                        'output': copy.deepcopy(self.items),
                        'done': done,
                        'usage': self.usage,
                    },
                }
            )
            self.last_flush = time.monotonic()

    async def text(self, text, reasoning=False):
        kind = 'reasoning' if reasoning else 'message'
        if not self.items or self.items[-1]['type'] != kind:
            if not reasoning and self.content:
                self.content += '\n\n'
            self.items.append(
                {
                    'id': uuid4().hex,
                    'type': kind,
                    'role': 'assistant',
                    'status': 'in_progress',
                    'content': [{'type': 'reasoning_text' if reasoning else 'output_text', 'text': ''}],
                }
            )
        self.items[-1]['content'][0]['text'] += text
        if not reasoning:
            self.content += text
        await self.flush()

    async def tool(self, call_id, name, arguments, native=None, result=None, done=False):
        item = next((i for i in self.items if i.get('call_id') == call_id and i['type'] == 'function_call'), None)
        if item is None:
            item = {'type': 'function_call', 'id': call_id, 'call_id': call_id}
            self.items.append(item)
        item.update(
            name=name, arguments=json.dumps(arguments), status='completed' if done else 'in_progress', native=native
        )
        if done:
            self.items[:] = [
                i for i in self.items if not (i['type'] == 'function_call_output' and i.get('call_id') == call_id)
            ]
            self.items.append(
                {
                    'type': 'function_call_output',
                    'id': f'out_{call_id}',
                    'call_id': call_id,
                    'output': [
                        {'type': 'input_text', 'text': result if isinstance(result, str) else json.dumps(result)}
                    ],
                    'status': 'completed',
                }
            )
        await self.flush(force=True)

    async def approve(self, name, arguments, native, timeout=None):
        call_id = f'approval_{uuid4().hex}'
        item = {
            'type': 'function_call',
            'id': call_id,
            'call_id': call_id,
            'name': name,
            'arguments': json.dumps(arguments),
            'status': 'pending',
            'native': native,
        }
        self.items.append(item)
        await self.flush(force=True)
        deadline = time.monotonic() + timeout if timeout is not None else None
        # Persisted resolutions work across workers and survive browser refreshes.
        while True:
            self.check_connection()
            message = await Chats.get_message_by_id_and_message_id(
                self.metadata['chat_id'], self.metadata['message_id']
            )
            if not message:
                raise ValueError('Agent conversation was removed')
            saved = next((i for i in message.get('output', []) if i.get('call_id') == call_id), {})
            resolution = saved.get('agent_resolution')
            if not resolution and deadline is not None and time.monotonic() >= deadline:
                resolution = {'action': 'reject', 'timed_out': True}
            if resolution:
                item['agent_resolution'] = resolution
                item['status'] = 'rejected' if resolution['action'] == 'reject' else 'completed'
                self.items.append(
                    {
                        'type': 'function_call_output',
                        'id': f'out_{call_id}',
                        'call_id': call_id,
                        'output': [{'type': 'input_text', 'text': json.dumps(resolution)}],
                        'status': 'completed',
                    }
                )
                await self.flush(force=True)
                return resolution
            await asyncio.sleep(0.5)

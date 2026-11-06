"""Codex app-server client, adapted from Computer's native JSON-RPC runner."""

import asyncio
import contextlib
import json


class CodexAppServer:
    def __init__(self, transport):
        self.transport = transport
        self.pending = {}
        self.events = asyncio.Queue()
        self.next_id = 0
        self.reader = None

    async def start(self):
        self.reader = asyncio.create_task(self._read())
        await self.request(
            'initialize',
            {'clientInfo': {'name': 'open_webui', 'version': '1'}, 'capabilities': {'experimentalApi': True}},
        )
        await self.send({'method': 'initialized'})

    async def send(self, payload):
        await self.transport.write(json.dumps(payload) + '\n')

    async def request(self, method, params):
        self.next_id += 1
        request_id = self.next_id
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        try:
            await self.send({'id': request_id, 'method': method, 'params': params})
            return await asyncio.wait_for(future, 120)
        finally:
            self.pending.pop(request_id, None)

    async def _read(self):
        try:
            async for message in self.transport.read_messages():
                if 'id' in message and 'method' not in message:
                    future = self.pending.get(message['id'])
                    if future and not future.done():
                        if 'error' in message:
                            future.set_exception(ValueError(str(message['error'].get('message', message['error']))))
                        else:
                            future.set_result(message.get('result', {}))
                elif 'method' in message:
                    await self.events.put(message)
        except Exception as exc:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(exc)
            await self.events.put(exc)

    async def close(self):
        if self.reader:
            self.reader.cancel()
            await asyncio.gather(self.reader, return_exceptions=True)
        for future in self.pending.values():
            if not future.done():
                future.cancel()


async def run(transport, output, prompt, images, options):
    client = CodexAppServer(transport)
    thread_id = turn_id = None
    try:
        await client.start()
        params = {
            'cwd': options['cwd'],
            'model': options['model'],
            'approvalPolicy': 'untrusted',
            'sandbox': 'workspace-write',
        }
        if options.get('instructions'):
            params['developerInstructions'] = options['instructions']
        if options.get('resume'):
            params['threadId'] = options['resume']
        result = await client.request('thread/resume' if options.get('resume') else 'thread/start', params)
        thread_id = result['thread']['id']
        output.state['session_id'] = thread_id
        await output.flush(force=True)
        turn_options = {}
        chat_params = options.get('params') or {}
        chat_params = {**chat_params, **(chat_params.get('custom_params') or {})}
        for field, aliases in {
            'effort': ('reasoningEffort', 'reasoning_effort'),
            'serviceTier': ('serviceTier', 'service_tier'),
        }.items():
            value = next((chat_params.get(key) for key in aliases if chat_params.get(key)), None)
            if isinstance(value, str) and value.strip():
                turn_options[field] = value.strip()
        result = await client.request(
            'turn/start',
            {
                'threadId': thread_id,
                'input': [{'type': 'text', 'text': prompt}, *[{'type': 'image', 'url': image} for image in images]],
                **turn_options,
            },
        )
        turn_id = result['turn']['id']
        while True:
            event = await client.events.get()
            if isinstance(event, Exception):
                raise event
            method, params = event['method'], event.get('params') or {}
            if params.get('turnId') and params['turnId'] != turn_id:
                continue
            if 'id' in event:
                if method in {'item/commandExecution/requestApproval', 'item/fileChange/requestApproval'}:
                    resolution = await output.approve('agent_tool', params, event)
                    result = {'decision': 'accept' if resolution['action'] == 'approve' else 'decline'}
                elif method == 'item/tool/requestUserInput':
                    resolution = await output.approve('ask_user', {'questions': params.get('questions', [])}, event)
                    answers = resolution.get('answers') or {}
                    answers = {
                        key: (value.get('text', '') if value.get('type') == 'other' else value.get('label', ''))
                        if isinstance(value, dict)
                        else value
                        for key, value in answers.items()
                    }
                    result = {
                        'answers': {
                            key: {'answers': value if isinstance(value, list) else [str(value)]}
                            for key, value in answers.items()
                        }
                    }
                else:
                    await client.send(
                        {'id': event['id'], 'error': {'code': -32601, 'message': f'Unsupported request: {method}'}}
                    )
                    continue
                await client.send({'id': event['id'], 'result': result})
            elif method == 'item/agentMessage/delta':
                await output.text(params.get('delta', ''))
            elif method in {'item/reasoning/textDelta', 'item/reasoning/summaryTextDelta'}:
                await output.text(params.get('delta', ''), reasoning=True)
            elif method in {'item/started', 'item/completed'}:
                item = params.get('item') or {}
                if item.get('type') not in {'agentMessage', 'userMessage', 'reasoning', 'plan'}:
                    await output.tool(
                        item.get('id', params.get('itemId')),
                        item.get('type', 'agent_tool'),
                        item,
                        native=item,
                        result=item.get('aggregatedOutput', item),
                        done=method == 'item/completed',
                    )
            elif method == 'turn/completed':
                turn = params.get('turn') or {}
                if turn.get('status') == 'failed' or turn.get('error'):
                    raise ValueError(str(turn.get('error') or 'Codex turn failed'))
                return
            elif method == 'thread/tokenUsage/updated':
                usage = (params.get('tokenUsage') or {}).get('last') or {}
                output.usage = {
                    key: usage[native]
                    for key, native in {
                        'input_tokens': 'inputTokens',
                        'output_tokens': 'outputTokens',
                        'total_tokens': 'totalTokens',
                    }.items()
                    if native in usage
                }
            elif method == 'error' and not params.get('willRetry'):
                raise ValueError(str(params.get('error') or params))
    except asyncio.CancelledError:
        if thread_id and turn_id:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(client.request('turn/interrupt', {'threadId': thread_id, 'turnId': turn_id}), 5)
        raise
    finally:
        await client.close()

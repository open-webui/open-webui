"""Claude's native stream-json/control protocol; message handling adapted from Computer."""

import asyncio
import contextlib
import json
from uuid import uuid4


async def run(transport, output, prompt, images, options):
    async def send(message):
        await transport.write(json.dumps(message) + '\n')

    initialize_id = uuid4().hex
    await send({'type': 'control_request', 'request_id': initialize_id, 'request': {'subtype': 'initialize'}})
    messages = transport.read_messages()
    async with asyncio.timeout(60):
        async for message in messages:
            if (
                message.get('type') == 'control_response'
                and message.get('response', {}).get('request_id') == initialize_id
            ):
                if message['response'].get('subtype') == 'error':
                    raise ValueError(message['response'].get('error', 'Claude initialization failed'))
                break
    content = [{'type': 'text', 'text': prompt}]
    for image in images:
        prefix, data = image.split(',', 1)
        content.append(
            {'type': 'image', 'source': {'type': 'base64', 'media_type': prefix[5:].split(';')[0], 'data': data}}
        )
    await send(
        {
            'type': 'user',
            'message': {'role': 'user', 'content': content},
            'parent_tool_use_id': None,
            'session_id': options.get('resume') or 'default',
        }
    )
    streamed_text = streamed_thinking = False
    try:
        async for message in messages:
            kind = message.get('type')
            if kind == 'system' and message.get('subtype') == 'init':
                output.state['session_id'] = message['session_id']
                await output.flush(force=True)
            elif kind == 'control_request':
                request = message['request']
                if request.get('subtype') != 'can_use_tool':
                    await send(
                        {
                            'type': 'control_response',
                            'response': {
                                'subtype': 'error',
                                'request_id': message['request_id'],
                                'error': 'Unsupported control request',
                            },
                        }
                    )
                    continue
                name, arguments = request['tool_name'], request['input']
                question = name == 'AskUserQuestion'
                presented = arguments
                if question:
                    presented = {
                        'questions': [
                            {**q, 'id': q.get('question', str(i))} for i, q in enumerate(arguments.get('questions', []))
                        ]
                    }
                resolution = await output.approve('ask_user' if question else name, presented, message)
                if resolution['action'] == 'reject' or resolution.get('timed_out'):
                    response = {'behavior': 'deny', 'message': 'Rejected by the user'}
                else:
                    answers = {
                        key: (value.get('text', '') if value.get('type') == 'other' else value.get('label', ''))
                        if isinstance(value, dict)
                        else value
                        for key, value in (resolution.get('answers') or {}).items()
                    }
                    updated = {**arguments, 'answers': answers} if question else arguments
                    response = {'behavior': 'allow', 'updatedInput': updated}
                await send(
                    {
                        'type': 'control_response',
                        'response': {'subtype': 'success', 'request_id': message['request_id'], 'response': response},
                    }
                )
            elif kind == 'stream_event':
                event = message.get('event') or {}
                if event.get('type') == 'message_start':
                    streamed_text = streamed_thinking = False
                if event.get('type') == 'content_block_delta':
                    delta = event.get('delta') or {}
                    if delta.get('type') == 'text_delta':
                        streamed_text = True
                        await output.text(delta.get('text', ''))
                    elif delta.get('type') == 'thinking_delta':
                        streamed_thinking = True
                        await output.text(delta.get('thinking', ''), reasoning=True)
            elif kind == 'assistant':
                for block in message.get('message', {}).get('content', []):
                    if block['type'] == 'text' and not streamed_text:
                        await output.text(block['text'])
                    elif block['type'] == 'thinking' and not streamed_thinking:
                        await output.text(block['thinking'], reasoning=True)
                    elif block['type'] == 'tool_use':
                        await output.tool(block['id'], block['name'], block['input'], native=block)
            elif kind == 'user':
                blocks = message.get('message', {}).get('content', [])
                for block in blocks if isinstance(blocks, list) else []:
                    if block.get('type') == 'tool_result':
                        previous = next((i for i in output.items if i.get('call_id') == block['tool_use_id']), {})
                        await output.tool(
                            block['tool_use_id'],
                            previous.get('name', 'agent_tool'),
                            json.loads(previous.get('arguments', '{}')),
                            native=block,
                            result=block.get('content'),
                            done=True,
                        )
            elif kind == 'result':
                output.state['session_id'] = message['session_id']
                output.usage = message.get('usage')
                if message.get('is_error'):
                    raise ValueError(
                        message.get('result') or '; '.join(message.get('errors') or []) or 'Claude Code turn failed'
                    )
                return
        raise ValueError('Claude Code ended without a turn result')
    except asyncio.CancelledError:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(
                send({'type': 'control_request', 'request_id': uuid4().hex, 'request': {'subtype': 'interrupt'}}), 5
            )
        raise

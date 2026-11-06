"""Pi RPC turns; agent_settled, rather than agent_end, marks completion."""

import asyncio
import contextlib
import json
from uuid import uuid4


async def run(transport, output, prompt, images, options):
    messages = transport.read_messages()
    settled = False
    last_error = None
    streamed_text = streamed_thinking = False
    tools = {}

    async def send(message):
        await transport.write(json.dumps(message) + '\n')

    async def dialog(message):
        method = message['method']
        if method not in {'confirm', 'select', 'input', 'editor'}:
            return
        timeout = message.get('timeout')
        timeout = max(0, timeout / 1000) if isinstance(timeout, (int, float)) else None
        if method == 'confirm':
            resolution = await output.approve(
                'agent_tool',
                {'title': message.get('title'), 'message': message.get('message')},
                message,
                timeout=timeout,
            )
            response = {'confirmed': resolution['action'] == 'approve' and not resolution.get('timed_out')}
        else:
            question = {
                'id': 'value',
                'header': message.get('title', 'Pi'),
                'question': message.get('title', 'Enter a response'),
                'options': [{'label': label, 'description': ''} for label in message.get('options', [])],
            }
            if method == 'editor' and message.get('prefill'):
                question['question'] += '\n' + message['prefill']
            resolution = await output.approve('ask_user', {'questions': [question]}, message, timeout=timeout)
            value = (resolution.get('answers') or {}).get('value')
            if isinstance(value, dict):
                value = value.get('text') if value.get('type') == 'other' else value.get('label')
            response = (
                {'value': value}
                if resolution['action'] == 'answer' and value is not None and not resolution.get('timed_out')
                else {'cancelled': True}
            )
        await send({'type': 'extension_ui_response', 'id': message['id'], **response})

    async def event(message):
        nonlocal settled, last_error, streamed_text, streamed_thinking
        kind = message.get('type')
        if kind == 'extension_ui_request':
            await dialog(message)
        elif kind == 'message_start':
            streamed_text = streamed_thinking = False
        elif kind == 'message_update':
            delta = message.get('assistantMessageEvent') or {}
            if delta.get('type') == 'text_delta':
                streamed_text = True
                await output.text(delta.get('delta', ''))
            elif delta.get('type') == 'thinking_delta':
                streamed_thinking = True
                await output.text(delta.get('delta', ''), reasoning=True)
        elif kind == 'message_end':
            completed = message.get('message') or {}
            if completed.get('role') == 'assistant':
                for block in completed.get('content', []):
                    if block.get('type') == 'text' and not streamed_text:
                        await output.text(block.get('text', ''))
                    elif block.get('type') == 'thinking' and not streamed_thinking:
                        await output.text(block.get('thinking', ''), reasoning=True)
                last_error = (
                    completed.get('errorMessage') or 'Pi turn failed'
                    if completed.get('stopReason') == 'error'
                    else None
                )
                usage = completed.get('usage') or {}
                total = output.usage or {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
                total['input_tokens'] += usage.get('input', 0) + usage.get('cacheRead', 0)
                total['output_tokens'] += usage.get('output', 0)
                total['total_tokens'] += usage.get('totalTokens', 0)
                output.usage = total
        elif kind in {'tool_execution_start', 'tool_execution_update', 'tool_execution_end'}:
            call_id = message['toolCallId']
            tool = tools.setdefault(call_id, {})
            tool.update(message)
            await output.tool(
                call_id,
                tool.get('toolName', 'agent_tool'),
                tool.get('args', {}),
                native=tool.copy(),
                result=tool.get('result', tool.get('partialResult')),
                done=kind == 'tool_execution_end',
            )
        elif kind == 'agent_settled':
            settled = True
            if message.get('aborted'):
                last_error = 'Pi aborted the turn'

    async def request(command, params=None):
        request_id = uuid4().hex
        await send({'type': command, 'id': request_id, **(params or {})})
        async with asyncio.timeout(60):
            async for message in messages:
                if message.get('type') == 'response' and message.get('id') == request_id:
                    if not message.get('success'):
                        raise ValueError(message.get('error', 'Pi request failed'))
                    return message.get('data') or {}
                await event(message)
        raise ValueError('Pi ended before replying')

    try:
        provider, separator, model = options['model'].partition('/')
        if not separator or not model:
            raise ValueError('Pi models must include their provider')
        await request('set_model', {'provider': provider, 'modelId': model})
        state = await request('get_state')
        output.state['session_id'] = state['sessionId']
        if options.get('resume') and state['sessionId'] != options['resume']:
            raise ValueError('Pi resumed a different conversation')
        await output.flush(force=True)
        content = []
        for image in images:
            prefix, data = image.split(',', 1)
            content.append({'type': 'image', 'mimeType': prefix[5:].split(';')[0], 'data': data})
        accepted = await request('prompt', {'message': prompt, 'images': content})
        if accepted.get('disposition') == 'handled':
            state = await request('get_state')
            settled = not (state.get('isStreaming') or state.get('isCompacting') or state.get('pendingMessageCount'))
        while not settled:
            await event(await anext(messages))
        if last_error:
            raise ValueError(last_error)
    except asyncio.CancelledError:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(send({'type': 'abort', 'id': uuid4().hex}), 5)
        raise

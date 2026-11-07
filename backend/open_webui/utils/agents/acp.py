"""ACP v1 over the terminal's native JSONL carrier."""

import asyncio
import contextlib
import json


class Client:
    def __init__(self, transport, handle):
        self.transport, self.handle = transport, handle
        self.messages = transport.read_messages()
        self.sequence = 0

    async def send(self, message):
        await self.transport.write(json.dumps({'jsonrpc': '2.0', **message}) + '\n')

    async def request(self, method, params, timeout=60):
        self.sequence += 1
        request_id = self.sequence
        async with asyncio.timeout(timeout):
            await self.send({'id': request_id, 'method': method, 'params': params})
            async for message in self.messages:
                if message.get('id') == request_id and 'method' not in message:
                    if 'error' in message:
                        raise ValueError(message['error'].get('message', 'Agent request failed'))
                    return message.get('result', {})
                await self.handle(message)
        raise ValueError('Agent ended before replying')


def answer_value(value):
    if isinstance(value, dict):
        return value.get('text', '') if value.get('type') == 'other' else value.get('label', '')
    return value


async def elicit(output, params, native):
    """Present ACP's flat form schema through the existing ask-user card."""
    if params.get('mode') != 'form':
        return {'action': 'decline'}
    properties = params.get('requestedSchema', {}).get('properties', {})
    required = params.get('requestedSchema', {}).get('required', [])
    questions, choices = [], {}
    for key, spec in properties.items():
        if key.endswith('_custom') and key[:-7] in properties:
            continue
        options = spec.get('oneOf') or [{'const': v, 'title': str(v)} for v in spec.get('enum', [])]
        if spec.get('type') == 'boolean':
            options = [{'const': True, 'title': 'Yes'}, {'const': False, 'title': 'No'}]
        choices[key] = {str(o.get('title', o.get('const'))): o.get('const') for o in options}
        if key not in required:
            choices[key]['(Skip)'] = None
        description = spec.get('description') or spec.get('title') or key
        if spec.get('type') == 'array':
            description += ' (enter a JSON array)'
        questions.append(
            {
                'id': key,
                'header': spec.get('title') or key,
                'question': f'{params.get("message", "")}\n{description}'.strip(),
                'options': [{'label': label, 'description': ''} for label in choices[key]],
            }
        )
    if not questions:
        return {'action': 'decline'}
    resolution = await output.approve('ask_user', {'questions': questions}, native)
    if resolution['action'] != 'answer' or resolution.get('timed_out'):
        return {'action': 'decline'}
    content = {}
    for key, value in (resolution.get('answers') or {}).items():
        if key not in properties:
            continue
        text = answer_value(value)
        if text == '(Skip)' and key not in required:
            continue
        if text in choices.get(key, {}):
            content[key] = choices[key][text]
        elif key + '_custom' in properties:
            content[key + '_custom'] = text
            content[key] = next((v for v in choices[key].values() if v is not None), '')
        elif properties[key].get('type') in {'integer', 'number', 'boolean', 'array'}:
            try:
                content[key] = json.loads(text)
            except (ValueError, TypeError):
                return {'action': 'decline'}
        else:
            content[key] = text
    return {'action': 'accept', 'content': content}


async def run(transport, output, prompt, images, options, *, auth_method=None):
    session_id = None
    streaming = False
    tools = {}

    async def handle(message):
        method, params = message.get('method'), message.get('params') or {}
        if params.get('sessionId') and session_id and params['sessionId'] != session_id:
            if 'id' in message:
                await client.send({'id': message['id'], 'error': {'code': -32602, 'message': 'Wrong agent session'}})
            return
        if 'id' in message and method:
            if method == 'session/request_permission':
                resolution = await output.approve('agent_tool', params.get('toolCall') or {}, message)
                accepted = resolution['action'] == 'approve' and not resolution.get('timed_out')
                kind = 'allow_once' if accepted else 'reject_once'
                choice = next((o for o in params.get('options', []) if o.get('kind') == kind), None)
                result = {
                    'outcome': {'outcome': 'selected', 'optionId': choice['optionId']}
                    if choice
                    else {'outcome': 'cancelled'}
                }
            elif method == 'elicitation/create':
                result = await elicit(output, params, message)
            else:
                await client.send(
                    {'id': message['id'], 'error': {'code': -32601, 'message': f'Unsupported client method: {method}'}}
                )
                return
            await client.send({'id': message['id'], 'result': result})
        elif method == 'session/update' and streaming:
            update = params.get('update') or {}
            kind = update.get('sessionUpdate')
            if kind in {'agent_message_chunk', 'agent_thought_chunk'}:
                content = update.get('content') or {}
                if content.get('type') == 'text':
                    await output.text(content.get('text', ''), reasoning=kind == 'agent_thought_chunk')
            elif kind in {'tool_call', 'tool_call_update'}:
                call_id = update['toolCallId']
                tool = tools.setdefault(call_id, {})
                tool.update(update)
                await output.tool(
                    call_id,
                    tool.get('title') or tool.get('kind', 'agent_tool'),
                    tool.get('rawInput') or {},
                    native=tool.copy(),
                    result=tool.get('rawOutput', tool.get('content', [])),
                    done=tool.get('status') in {'completed', 'failed'},
                )
            elif kind == 'plan':
                await output.tool(
                    'agent_plan',
                    'Plan',
                    {'entries': update.get('entries', [])},
                    native=update,
                    result=update.get('entries', []),
                    done=True,
                )

    client = Client(transport, handle)
    try:
        initialized = await client.request(
            'initialize',
            {
                'protocolVersion': 1,
                'clientInfo': {'name': 'open_webui', 'version': '1'},
                'clientCapabilities': {
                    'fs': {'readTextFile': False, 'writeTextFile': False},
                    'terminal': False,
                    'elicitation': {'form': {}},
                },
            },
        )
        if initialized.get('protocolVersion') != 1:
            raise ValueError('Agent requires an unsupported ACP version')
        if auth_method:
            await client.request('authenticate', {'methodId': auth_method})
        capabilities = initialized.get('agentCapabilities') or {}
        params = {'cwd': options['cwd'], 'mcpServers': []}
        if options.get('resume'):
            session_id = options['resume']
            params['sessionId'] = session_id
            if 'resume' in capabilities.get('sessionCapabilities', {}):
                session = await client.request('session/resume', params)
            elif capabilities.get('loadSession'):
                session = await client.request('session/load', params)
            else:
                raise ValueError('This agent no longer supports resuming this conversation')
        else:
            session = await client.request('session/new', params)
            session_id = session['sessionId']
        if capabilities.get('loadSession') or 'resume' in capabilities.get('sessionCapabilities', {}):
            output.state['session_id'] = session_id
        await output.flush(force=True)
        config = next(
            (c for c in session.get('configOptions', []) if c.get('category') == 'model' or c.get('id') == 'model'),
            None,
        )
        if not config and not session.get('models') and options.get('resume_state', {}).get('model_config'):
            config = {'id': options['resume_state']['model_config']}
        if config:
            output.state['model_config'] = config['id']
            await client.request(
                'session/set_config_option',
                {'sessionId': session_id, 'configId': config['id'], 'value': options['model']},
            )
        elif session.get('models') or options.get('resume'):
            await client.request('session/set_model', {'sessionId': session_id, 'modelId': options['model']})
        else:
            raise ValueError('Agent did not advertise model selection for this session')
        await output.flush(force=True)
        if images and not capabilities.get('promptCapabilities', {}).get('image'):
            raise ValueError('This agent does not support image prompts')
        content = []
        if options.get('instructions'):
            content.append(
                {'type': 'text', 'text': options['instructions'], 'annotations': {'audience': ['assistant']}}
            )
        content.append({'type': 'text', 'text': prompt})
        for image in images:
            prefix, data = image.split(',', 1)
            content.append({'type': 'image', 'mimeType': prefix[5:].split(';')[0], 'data': data})
        streaming = True
        result = await client.request('session/prompt', {'sessionId': session_id, 'prompt': content}, timeout=None)
        if result.get('usage'):
            usage = result['usage']
            output.usage = {
                'input_tokens': usage.get('inputTokens', 0),
                'output_tokens': usage.get('outputTokens', 0),
                'total_tokens': usage.get('totalTokens', 0),
            }
        if result.get('stopReason') == 'cancelled':
            raise ValueError('Agent cancelled the turn')
    except asyncio.CancelledError:
        if session_id:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(
                    client.send({'method': 'session/cancel', 'params': {'sessionId': session_id}}), 5
                )
        raise

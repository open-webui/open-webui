"""Run native agent turns with terminal attachments and saved conversation state."""

import copy

from open_webui.models.chats import Chats
from open_webui.utils.auth import decode_token
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.terminals import get_terminal_json, upload_files_to_terminal

from .output import Output
from .transport import TerminalTransport
from . import acp, codex, claude_code, pi

PROVIDERS = {
    'codex': codex.run,
    'claude-code': claude_code.run,
    'cursor': acp.run,
    'grok': acp.run,
    'opencode': acp.run,
    'cline': acp.run,
    'gemini': acp.run,
    'pi': pi.run,
}


async def run(request, form_data, user, metadata, model):
    if not is_saved_chat_id(metadata.get('chat_id')):
        raise ValueError('Agent conversations require a saved chat')
    if metadata.get('regeneration_message_id') or metadata.get('assistant_message_id'):
        raise ValueError('Continue an agent conversation with a new message')
    agent = model['agent']
    if agent['provider'] not in PROVIDERS:
        raise ValueError('Unsupported terminal agent')
    metadata['terminal_id'] = agent['terminal_id']
    transport = await TerminalTransport.resolve(request, user, metadata)
    output = Output(metadata, user, transport.raise_if_failed, form_data)
    output.state = {**agent}
    previous = None
    parent = (metadata.get('user_message') or {}).get('parentId')
    if parent:
        previous_message = await Chats.get_message_by_id_and_message_id(metadata['chat_id'], parent)
        token = ((previous_message or {}).get('meta') or {}).get('agent')
        previous = decode_token(token) if isinstance(token, str) else None
        if previous and not (
            previous.get('purpose') == 'terminal-agent'
            and previous.get('user') == user.id
            and previous.get('chat') == metadata['chat_id']
            and all(previous.get(k) == v for k, v in agent.items())
        ):
            previous = None
        if previous and any(
            child != metadata.get('user_message_id') for child in (previous_message or {}).get('childrenIds', [])
        ):
            raise ValueError('Agent history cannot be branched in place. Start a new chat instead.')
    # Browsing files must not move an existing agent conversation's workspace.
    cwd = (previous or {}).get('cwd') or metadata.get('initial_terminal_cwd')
    if not cwd:
        directory = await get_terminal_json(request, user, metadata, '/files/cwd')
        cwd = (directory or {}).get('cwd')
    if not cwd:
        raise ValueError('Agent working directory is unavailable')
    output.state['cwd'] = cwd
    files = copy.deepcopy(form_data.get('files') or [])
    uploads = [f for f in files if f.get('type') != 'filesystem' and f.get('id')]
    await upload_files_to_terminal(request, user, uploads, metadata, {})
    if any(f.get('terminal_error') for f in uploads):
        raise ValueError('An attachment could not be uploaded to the agent environment')
    paths = [f['terminal_path'] for f in uploads]
    for file in files:
        if file.get('type') == 'filesystem':
            if file.get('terminal_id') != agent['terminal_id']:
                raise ValueError('Attachment belongs to another terminal')
            paths.append(file['path'])
    messages = form_data.get('messages') or []
    user_message = metadata.get('user_message') or next((m for m in reversed(messages) if m.get('role') == 'user'), {})

    def text(content):
        return (
            content
            if isinstance(content, str)
            else '\n'.join(p.get('text', '') for p in content or [] if p.get('type') == 'text')
        )

    prompt = text(user_message.get('content', ''))
    if not previous or not previous.get('session_id'):
        history = [m for m in messages if m.get('role') in {'user', 'assistant'}]
        if len(history) > 1:
            prompt = '\n\n'.join(f'{m["role"]}: {text(m.get("content", ""))}' for m in history)
    if paths:
        prompt += '\n\nAttached files in this environment:\n' + '\n'.join(paths)
    images = [
        p['image_url']['url']
        for m in [user_message, *messages[-1:]]
        for p in (m.get('content') if isinstance(m.get('content'), list) else [])
        if p.get('type') == 'image_url' and p.get('image_url', {}).get('url', '').startswith('data:image/')
    ]
    images = list(dict.fromkeys(images))
    instructions = '\n\n'.join(text(m.get('content')) for m in messages if m.get('role') == 'system')
    options = {
        'request_id': metadata['message_id'],
        'cwd': cwd,
        'model': agent['model'],
        'resume': (previous or {}).get('session_id'),
        'instructions': instructions,
    }
    succeeded = False
    try:
        await transport.start(agent['provider'], options)
        extra = {'auth_method': 'cursor_login'} if agent['provider'] == 'cursor' else {}
        await PROVIDERS[agent['provider']](
            transport,
            output,
            prompt,
            images,
            {**options, 'resume_state': previous or {}, 'params': form_data.get('params') or {}},
            **extra,
        )
        succeeded = True
    finally:
        await transport.close()
        for item in output.items:
            if item.get('status') in {'pending', 'in_progress'}:
                item['status'] = 'completed' if succeeded else 'incomplete'
        await output.flush(done=True, force=True)
    return {'status': True, 'chat_id': metadata['chat_id']}

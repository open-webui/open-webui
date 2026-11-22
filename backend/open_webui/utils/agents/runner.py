"""Run native agent turns with terminal attachments and saved conversation state."""

import copy

from open_webui.utils.machines import machine_id_of
from open_webui.models.chats import Chats
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.middleware import convert_url_images_to_base64
from open_webui.utils.misc import get_message_list
from open_webui.utils.machines import get_machine_json, upload_files_to_machine

from .session import get_resume_point
from .output import Output
from .transport import MachineTransport
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
    'hermes': acp.run,
    'antigravity': acp.run,
    'copilot': acp.run,
    'goose': acp.run,
    'qwen': acp.run,
}


# Providers that can continue their native conversation from an earlier turn.
RESUMABLE_AT = {'codex', 'claude-code'}


def provider_runner(provider):
    # Agents configured in Open Terminal's OPEN_TERMINAL_ACP_AGENTS arrive as `acp-<id>`.
    return PROVIDERS.get(provider) or (acp.run if provider.startswith('acp-') else None)


async def run(request, form_data, user, metadata, model):
    if not is_saved_chat_id(metadata.get('chat_id')):
        raise ValueError('Agent conversations require a saved chat')
    if metadata.get('assistant_message_id'):
        raise ValueError('Continue an agent conversation with a new message')
    agent = model['agent']
    run_provider = provider_runner(agent['provider'])
    if run_provider is None:
        raise ValueError('Unsupported machine agent')
    chat = await Chats.get_accessible_chat_by_id(metadata['chat_id'], user, permission='write')
    if chat is None:
        raise ValueError('Chat reply access denied')
    parent = (metadata.get('user_message') or {}).get('parentId')
    previous, branched, copied = (
        await get_resume_point(chat, parent, user.id, exclude=metadata.get('message_id'))
        if parent
        else (None, False, False)
    )
    if previous and any(previous.get(key) != agent[key] for key in ('machine_id', 'provider')):
        previous = None
    # Regenerated and edited messages branch off a reply whose native conversation went on without them;
    # a forked chat's first reply continues the conversation of the chat it was forked from.
    resume_at = None
    fork = False
    if previous and (branched or copied):
        if agent['provider'] in RESUMABLE_AT and (previous.get('turn') or not branched):
            resume_at = previous.get('turn') if branched or agent['provider'] == 'codex' else None
            # Codex copies the thread through that turn, keeping the original for the other branch. Claude
            # branches inside its own transcript, as T3 Code does, but copies it for a forked chat so the two
            # chats never write to one conversation.
            fork = agent['provider'] == 'codex' or copied
        else:
            # The agent can't continue from an earlier turn: start a new conversation from the transcript.
            previous = {key: value for key, value in previous.items() if key != 'session_id'}
    metadata['machine_id'] = agent['machine_id']
    transport = await MachineTransport.resolve(request, user, metadata)
    output = Output(metadata, user, transport.raise_if_failed, form_data)
    output.state = {
        # A fork is a new native conversation, which records its own id once the agent reports it.
        **{
            key: previous[key]
            for key in ('model_config', *(() if fork else ('session_id',)))
            if previous and key in previous
        },
        **agent,
        'instance_user_id': (previous or {}).get('instance_user_id') or (previous or {}).get('user') or user.id,
    }
    # Browsing files must not move an existing agent conversation's workspace.
    cwd = (previous or {}).get('cwd') or metadata.get('initial_machine_cwd')
    if not cwd:
        directory = await get_machine_json(request, user, metadata, '/files/cwd')
        cwd = (directory or {}).get('cwd')
    if not cwd:
        raise ValueError('Agent working directory is unavailable')
    output.state['cwd'] = cwd
    files = copy.deepcopy(form_data.get('files') or [])
    uploads = [f for f in files if f.get('type') != 'filesystem' and f.get('id')]
    await upload_files_to_machine(request, user, uploads, metadata, {})
    if any(f.get('machine_error') for f in uploads):
        raise ValueError('An attachment could not be uploaded to the agent environment')
    paths = [f['machine_path'] for f in uploads]
    for file in files:
        if file.get('type') == 'filesystem':
            if machine_id_of(file) != agent['machine_id']:
                raise ValueError('Attachment belongs to another machine')
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
        # A new native conversation starts from this branch's transcript. Saved chats send only
        # the system prompt, so the branch is read from the stored messages.
        stored = get_message_list(await Chats.get_messages_map_by_chat_id(chat.id) or {}, parent) if parent else []
        history = [m for m in stored or messages if m.get('role') in {'user', 'assistant'}]
        if stored:
            history.append(user_message)
        elif metadata.get('regeneration_message_id') and history and history[-1].get('role') == 'assistant':
            history = history[:-1]  # Guided regeneration sends the reply being revised; it's quoted below.
        if len(history) > 1:
            prompt = '\n\n'.join(f'{m["role"]}: {text(m.get("content", ""))}' for m in history)
    if metadata.get('regeneration_message_id') and form_data.get('regeneration_prompt'):
        # Guided regeneration: the agent revises a reply its branched conversation no longer holds.
        regenerated = await Chats.get_message_by_id_and_message_id(chat.id, metadata['regeneration_message_id'])
        earlier = text((regenerated or {}).get('content', ''))
        if earlier:
            prompt += f'\n\nYour previous reply to this was:\n<previous_reply>\n{earlier}\n</previous_reply>'
        prompt += f'\n\n{form_data["regeneration_prompt"]}'
    if paths:
        prompt += '\n\nAttached files in this environment:\n' + '\n'.join(paths)
    await convert_url_images_to_base64(form_data, user=user)
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
        'resume_at': resume_at,
        'fork': fork,
        'instructions': instructions,
        # The chat's tool permission mode; agents with their own auto review use it for Auto.
        'approval_mode': (metadata.get('params') or {}).get('tool_approval_mode', 'full'),
    }
    succeeded = False
    try:
        session = await transport.start(agent['provider'], options)
        if (
            agent['provider'] == 'claude-code'
            and (resume_at or fork)
            and (session.get('resume_at') != resume_at or bool(session.get('fork')) != fork)
        ):
            # An older Open Terminal would resume the latest turn of the original conversation instead.
            raise ValueError('Update Open Terminal to regenerate or edit earlier messages in this chat')
        extra = {'auth_method': 'cursor_login'} if agent['provider'] == 'cursor' else {}
        await run_provider(
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

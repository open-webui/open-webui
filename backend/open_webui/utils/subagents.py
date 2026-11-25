from __future__ import annotations

import asyncio
import copy
import time
import weakref
from datetime import timedelta
from uuid import uuid4

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from open_webui.utils.machines import machine_id_of
from open_webui.models.chat_messages import ChatMessages
from open_webui.models.chats import ChatForm, Chats
from open_webui.models.config import Config
from open_webui.models.auths import Auths
from open_webui.models.users import UserModel, Users
from open_webui.tasks import create_task, has_active_tasks, list_task_ids_by_item_id
from open_webui.utils.auth import VERIFIED_USER_ROLES, create_token
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.misc import (
    add_or_update_system_message,
    get_content_from_message,
    get_message_list,
    is_raster_image_content_type,
)
from open_webui.utils.models import get_filtered_models
from open_webui.utils.session_records import has_pending_tool_approval
from open_webui.utils.tool_calling import strip_tool_approval_prompt
from open_webui.utils.tool_search import strip_deferred_tools_manifest
from starlette.datastructures import Headers

DEFAULT_SUBAGENT_SYSTEM_PROMPT = """You are a sub-agent working on a specific task assigned by the lead agent.

You have full access to the workspace — you can read, write, edit files, and run commands.
Focus exclusively on your assigned task. Do NOT work on anything outside your scope.

When done, end with a clear summary:
- What you did
- What files you changed (if any)
- Any issues or open questions
"""

MUTATING_MEMORY_TOOLS = {
    'add_memory',
    'delete_memory',
    'replace_memory_content',
    'update_memory',
}

_background_active: set[str] = set()
_background_lock = asyncio.Lock()
_foreground_semaphore: asyncio.Semaphore | None = None
_parent_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()


async def get_subagent_models(request: Request, user: UserModel, model: dict) -> list[dict]:
    subagents = (model.get('info', {}).get('meta') or {}).get('subagents') or {}
    model_ids = subagents.get('model_ids') or []
    if not model_ids:
        return []
    candidates = [model for model_id, model in request.app.state.MODELS.items() if model_id in model_ids]
    return [
        {
            'id': model['id'],
            'name': model.get('name', model['id']),
            'description': (model.get('info', {}).get('meta') or {}).get('description') or '',
        }
        for model in await get_filtered_models(candidates, user)
    ]


async def _build_request(source: Request, user_id: str, *, internal: bool) -> Request:
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.0'},
        'method': 'POST',
        'path': '/api/v1/subagents/internal',
        'query_string': b'',
        'headers': Headers({}).raw,
        'client': ('', 0),
        'server': ('127.0.0.1', 80),
        'scheme': 'http',
        'app': source.app,
    }
    request = Request(scope)
    auth = await Auths.get_auth_by_id(user_id)
    if auth is None or not auth.active:
        raise ValueError('Subagent owner is no longer active')
    token = create_token(
        data={'id': user_id, 'typ': 'subagent', 'session_stamp': auth.session_stamp},
        expires_delta=timedelta(hours=1),
    )
    request.state.token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
    request.state.enable_api_keys = False
    if internal:
        request.state.internal = True
    return request


async def queue_user_message(
    request: Request, chat_id: str, user: UserModel, user_message: dict, parent_id: str
) -> bool:
    """Queue a message at the end of the chat, which may have moved on since the browser loaded it. It is answered
    after the running reply there, with the messages already queued."""
    if not user_message.get('id'):
        return False
    async with _parent_locks.setdefault(chat_id, asyncio.Lock()):
        async with Chats._chat_transaction(chat_id) as (session, chat):
            if not chat or chat.user_id != user.id:
                return False
            messages = await ChatMessages.get_messages_map_by_chat_id(chat_id, db=session) or {}
            last_id = Chats._last_descendant_id(messages, parent_id)
            if (messages.get(last_id) or {}).get('role') == 'assistant':
                parent_id = user_message['parentId'] = last_id
            reply = messages.get(parent_id)
            # Checked under the lock the reply's own cleanup takes, so the message can't be left unanswered.
            if not reply or not (
                await ChatMessages.has_queued_message(chat_id, parent_id)
                or (reply.get('done') is False and await has_active_tasks(request.app.state.redis, chat_id))
            ):
                return False
            message = {
                'id': user_message['id'],
                'parentId': parent_id,
                'childrenIds': [],
                'role': 'user',
                'content': user_message.get('content', ''),
                **({'files': user_message['files']} if user_message.get('files') else {}),
                'model': reply.get('model'),
                'user_id': user.id,
                'user': {'id': user.id, 'name': user.name},
                'meta': {'status': 'pending'},
                'timestamp': int(time.time()),
            }
            reply.setdefault('childrenIds', []).append(message['id'])
            chat.updated_at = int(time.time())
            await ChatMessages.upsert_message(message['id'], chat_id, user.id, message, db=session)
            await ChatMessages.upsert_message(
                parent_id, chat_id, reply.get('user_id') or chat.user_id, reply, db=session
            )
    return True


def is_read_while_working(meta: dict) -> bool:
    return meta.get('internal') is not True or meta.get('type') == 'message'


async def get_queued_messages(chat_id: str, user_id: str, reply_id: str) -> list[dict]:
    """The messages added under a running reply for it to read, oldest first."""
    if not await ChatMessages.has_queued_message(chat_id, reply_id):
        return []
    chat = await Chats.get_chat_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        return []
    messages = ((chat.chat or {}).get('history') or {}).get('messages') or {}
    queued = [
        message
        for message in messages.values()
        if message.get('role') == 'user'
        and message.get('parentId') == reply_id
        and (message.get('meta') or {}).get('status') == 'pending'
        and is_read_while_working(message['meta'])
    ]
    # What the user wrote stays apart from what another chat sent.
    return [message for message in queued if message['meta'].get('type') == queued[0]['meta'].get('type')]


async def has_upcoming_reply(request: Request, user_id: str, chat_id: str, message_id: str) -> bool:
    """Whether this reply is followed by another without the user writing: a sub-agent has yet to report, or a
    message is waiting."""
    # A sub-agent's task lasts until its report is added, so checking the tasks first can't miss one in between.
    # Replies after its report run as other tasks.
    for child in await Chats.get_children_by_parent_id(chat_id, user_id):
        meta = child.meta or {}
        if meta.get('type') == 'subagent' and meta.get('delegation_id') in await list_task_ids_by_item_id(
            request.app.state.redis, child.id
        ):
            return True
    return bool(await ChatMessages.get_pending_message_metas(chat_id, message_id))


async def insert_queued_turn(
    chat_id: str, user: UserModel, reply_id: str, queued: list[dict], assistant_meta: dict
) -> dict | None:
    """Replace queued messages the running agent has been given with one message, and start the reply after it."""
    queued_ids = {message['id'] for message in queued}
    async with _parent_locks.setdefault(chat_id, asyncio.Lock()):
        async with Chats._chat_transaction(chat_id) as (session, chat):
            messages = await ChatMessages.get_messages_map_by_chat_id(chat_id, db=session) or {}
            reply = messages.get(reply_id)
            if not reply:
                return None
            for message_id in queued_ids:
                messages.pop(message_id, None)
            now = int(time.time())
            user_message = {
                'id': str(uuid4()),
                'parentId': reply_id,
                'role': 'user',
                'content': '\n\n'.join(message.get('content', '') for message in queued),
                'model': reply.get('model'),
                'user_id': user.id,
                'user': {'id': user.id, 'name': user.name},
                'meta': {key: value for key, value in (queued[0].get('meta') or {}).items() if key != 'status'},
                'timestamp': now,
            }
            assistant_message = {
                **{key: reply[key] for key in ('model', 'modelName', 'modelIdx', 'user_id') if key in reply},
                'id': str(uuid4()),
                'parentId': user_message['id'],
                'childrenIds': [],
                'role': 'assistant',
                'content': '',
                'done': False,
                'meta': assistant_meta,
                'timestamp': now,
            }
            user_message['childrenIds'] = [assistant_message['id']]
            reply['childrenIds'] = [
                *(child_id for child_id in reply.get('childrenIds', []) if child_id not in queued_ids),
                user_message['id'],
            ]
            chat.current_message_id = assistant_message['id']
            chat.updated_at = now
            await ChatMessages.delete_message_ids_by_chat_id(chat_id, queued_ids, db=session)
            await ChatMessages.upsert_message(reply_id, chat_id, user.id, reply, db=session)
            for message in (user_message, assistant_message):
                await ChatMessages.upsert_message(message['id'], chat_id, user.id, message, db=session)
    return {
        'user_message': user_message,
        'assistant_message': assistant_message,
        'children_ids': reply['childrenIds'],
    }


def get_pending_run(metadata: dict, model_id: str | None = None) -> dict:
    """The settings a turn started for pending messages takes from the turn before it."""
    return {
        'model_id': metadata.get('model_id') or model_id,
        'session_id': metadata.get('session_id'),
        'tool_ids': metadata.get('tool_ids') or [],
        'skill_ids': metadata.get('skill_ids') or [],
        'chat_context': metadata.get('chat_context'),
        'filter_ids': metadata.get('filter_ids') or [],
        'machine_id': metadata.get('machine_id'),
        'features': metadata.get('features') or {},
        'variables': metadata.get('variables') or {},
    }


async def process_pending_internal_messages(
    source_request: Request,
    parent_chat_id: str,
    user_id: str,
    run: dict,
    reply_id: str | None = None,
) -> None:
    """Answer pending messages once the chat is idle. With reply_id, answer only the messages queued under that
    reply as soon as it is saved, without waiting for its follow-ups, title and other background work."""
    lock = _parent_locks.setdefault(parent_chat_id, asyncio.Lock())
    if reply_id is None:
        while await has_active_tasks(source_request.app.state.redis, parent_chat_id):
            await asyncio.sleep(0.25)
    else:
        # The turn started below asks whether its parent reply is still running, without taking this lock.
        reply = await Chats.get_message_by_id_and_message_id(parent_chat_id, reply_id)
        if not reply or reply.get('done') is not True:
            return

    async with lock:
        if reply_id is None and await has_active_tasks(source_request.app.state.redis, parent_chat_id):
            return

        user = await Users.get_user_by_id(user_id)
        if not user or user.role not in VERIFIED_USER_ROLES:
            return

        async with Chats._chat_transaction(parent_chat_id) as (session, chat):
            if not chat or chat.user_id != user_id:
                return

            messages = await ChatMessages.get_messages_map_by_chat_id(parent_chat_id, db=session) or {}
            pending = [
                message
                for message in messages.values()
                for meta in [message.get('meta') or {}]
                if message.get('role') == 'user'
                and not message.get('childrenIds')
                and (
                    (
                        meta.get('internal') is True
                        and meta.get('type') in ('subagent', 'message')
                        and meta.get('status') in (None, 'pending')
                    )
                    or (meta.get('internal') is True and meta.get('type') == 'timer')
                    # The user's own message, held while its reply was running.
                    or (meta.get('internal') is not True and meta.get('status') == 'pending')
                )
            ]
            if reply_id is not None:
                pending = [
                    message
                    for message in pending
                    if message.get('parentId') == reply_id and is_read_while_working(message.get('meta') or {})
                ]
            if not pending:
                return

            first = pending[0]
            first_meta = first.get('meta') or {}
            kind = first_meta['type'] if first_meta.get('internal') is True else 'queued'
            parent_id = first.get('parentId')
            if kind == 'timer' and first_meta.get('timer_id'):
                timer = await Chats.get_chat_by_id(first_meta['timer_id'])
                timer_run = ((timer.meta or {}).get('run') if timer else None) or {}
                if timer_run:
                    run = {**run, **timer_run, 'chat_context': timer_run.get('chat_context')}
            model_id = first.get('model') or run['model_id']
            if kind == 'timer':
                batch = [first]
            elif kind == 'queued':
                batch = [
                    message
                    for message in pending
                    if message.get('parentId') == parent_id and (message.get('meta') or {}).get('internal') is not True
                ]
            else:
                batch = [
                    message
                    for message in pending
                    for meta in [message.get('meta') or {}]
                    if message.get('parentId') == parent_id
                    and (message.get('model') or model_id) == model_id
                    and (
                        meta.get('internal') is True
                        and meta.get('type') == kind
                        and meta.get('status') in (None, 'pending')
                    )
                ]
            combined_content = '\n\n'.join(message.get('content', '') for message in batch if message.get('content'))
            if kind == 'timer':
                timer_ids = [
                    message['meta']['timer_id'] for message in batch if (message.get('meta') or {}).get('timer_id')
                ]
                combined_meta = {'internal': True, 'type': 'timer'}
                if len(timer_ids) == 1:
                    combined_meta['timer_id'] = timer_ids[0]
                elif timer_ids:
                    combined_meta['timer_ids'] = timer_ids
            elif kind == 'queued':
                # The user's own words, answered as an ordinary message.
                combined_meta = {}
            else:
                delegation_ids = [
                    message['meta']['delegation_id']
                    for message in batch
                    if (message.get('meta') or {}).get('delegation_id')
                ]
                subagent_chat_ids = [
                    message['meta']['subagent_chat_id']
                    for message in batch
                    if (message.get('meta') or {}).get('subagent_chat_id')
                ]
                combined_meta = {'internal': True, 'type': kind}
                if len(delegation_ids) == 1:
                    combined_meta['delegation_id'] = delegation_ids[0]
                elif delegation_ids:
                    combined_meta['delegation_ids'] = delegation_ids
                if len(subagent_chat_ids) == 1:
                    combined_meta['subagent_chat_id'] = subagent_chat_ids[0]
                elif subagent_chat_ids:
                    combined_meta['subagent_chat_ids'] = subagent_chat_ids

            reuse_message = len(batch) == 1 and (first.get('meta') or {}).get('status') != 'pending'
            user_message_id = first['id'] if reuse_message else str(uuid4())
            removed_ids = set()
            if not reuse_message:
                removed_ids = {message['id'] for message in batch}
                for message_id in removed_ids:
                    messages.pop(message_id, None)
            if parent_id and parent_id in messages:
                messages[parent_id]['childrenIds'] = [
                    child_id
                    for child_id in messages[parent_id].get('childrenIds', [])
                    if child_id != user_message_id and child_id not in removed_ids
                ]
            # The chat may have gone on since the message was added.
            current = messages.get(chat.current_message_id) or {}
            if current.get('role') == 'assistant' and any(
                message.get('id') == parent_id for message in get_message_list(messages, current['id'])
            ):
                parent_id = current['id']

            assistant_message_id = str(uuid4())
            message_list = get_message_list(messages, parent_id)
            user_message = {
                'id': user_message_id,
                'parentId': parent_id,
                'childrenIds': [assistant_message_id],
                'role': 'user',
                'content': combined_content,
                'model': model_id,
                'meta': combined_meta,
                'timestamp': int(time.time()),
            }
            if kind == 'queued':
                user_message.update(user_id=user.id, user={'id': user.id, 'name': user.name})
                held_files = [file for message in batch for file in message.get('files') or []]
                if held_files:
                    user_message['files'] = held_files
                # The files the browser sends with a follow-up.
                branch_file_ids = {file.get('id') for message in message_list for file in message.get('files') or []}
                chat_files = [
                    file
                    for file in (chat.chat or {}).get('files') or []
                    if file.get('id') in branch_file_ids and file not in held_files
                ]
                run = {**run, 'files': chat_files}
            assistant_message = {
                'id': assistant_message_id,
                'parentId': user_message_id,
                'childrenIds': [],
                'role': 'assistant',
                'content': '',
                'done': False,
                'model': model_id,
                'timestamp': int(time.time()),
            }

            if parent_id and parent_id in messages:
                parent_children = [
                    child_id for child_id in messages[parent_id].get('childrenIds', []) if child_id != user_message_id
                ]
                parent_children.append(user_message_id)
                messages[parent_id]['childrenIds'] = parent_children
            messages[user_message_id] = {**messages.get(user_message_id, {}), **user_message}
            messages[assistant_message_id] = assistant_message
            chat.current_message_id = assistant_message_id
            chat.updated_at = int(time.time())

            if removed_ids:
                await ChatMessages.delete_message_ids_by_chat_id(parent_chat_id, removed_ids, db=session)
            for message_id in dict.fromkeys((first.get('parentId'), parent_id, user_message_id, assistant_message_id)):
                if message_id in messages:
                    await ChatMessages.upsert_message(
                        message_id, parent_chat_id, user_id, messages[message_id], db=session
                    )

        from open_webui.socket.main import sio

        await sio.emit(
            'events',
            {
                'chat_id': parent_chat_id,
                'message_id': assistant_message_id,
                'data': {'type': 'chat:reload'},
            },
            room=f'user:{user.id}',
        )

        chat_context = copy.deepcopy(run.get('chat_context') or {})
        # Runs saved before chat_context was introduced only have the assembled prompt.
        if run.get('chat_context') is None and run.get('system_prompt'):
            chat_context['messages'] = [
                {
                    'role': 'system',
                    'content': strip_tool_approval_prompt(strip_deferred_tools_manifest(run['system_prompt'])),
                }
            ]
        form_data = {
            'model': model_id,
            'params': chat_context.get('params') or {},
            'messages': [
                *chat_context.get('messages', []),
                *message_list,
                {'role': 'user', 'content': combined_content},
            ],
            'stream': True,
            'chat_id': parent_chat_id,
            'id': assistant_message_id,
            'parent_id': parent_id,
            'user_message': user_message,
            'session_id': run.get('session_id') or f'{kind}-result:{parent_chat_id}',
            'background_tasks': {},
            'tool_ids': run.get('tool_ids') or [],
            'skill_ids': run.get('skill_ids') or [],
            'filter_ids': run.get('filter_ids') or [],
            'features': run.get('features') or {},
            'files': [
                *(run.get('files') or []),
                # Documents attached to held messages; their images reach the model with the message itself.
                *[
                    file
                    for file in user_message.get('files') or []
                    if file.get('type') in ('doc', 'text', 'note', 'chat', 'collection', 'folder')
                    or (file.get('type') == 'file' and not is_raster_image_content_type(file.get('content_type')))
                ],
            ],
            'variables': run.get('variables') or {},
            'chat_variables': chat_context.get('chat_variables'),
        }
        if machine_id_of(run):
            form_data['machine_id'] = machine_id_of(run)

        request = await _build_request(source_request, user.id, internal=False)
        request.state.chat_context = chat_context
        await source_request.app.state.CHAT_COMPLETION_HANDLER(request, form_data, user=user)


async def insert_internal_message(
    request: Request, user: UserModel, chat_id: str, parent_id: str | None, content: str, meta: dict, run: dict
) -> None:
    """Add a message the user did not write after the chat's latest reply, and answer it once the chat is idle."""
    message = {
        'id': str(uuid4()),
        'parentId': parent_id,
        'childrenIds': [],
        'role': 'user',
        'content': content,
        'model': run['model_id'],
        'meta': {'internal': True, **meta},
        'timestamp': int(time.time()),
    }
    async with _parent_locks.setdefault(chat_id, asyncio.Lock()):
        async with Chats._chat_transaction(chat_id) as (session, chat):
            if not chat or chat.user_id != user.id:
                return
            messages = await ChatMessages.get_messages_map_by_chat_id(chat_id, db=session) or {}
            parent = messages.get(parent_id)
            is_active = await has_active_tasks(request.app.state.redis, chat_id)
            replies = [
                reply
                for reply_id, reply in messages.items()
                if reply.get('role') == 'assistant'
                and (is_active or reply.get('done') is not False)
                and (parent is None or any(entry is parent for entry in get_message_list(messages, reply_id)))
            ]
            if replies:
                message['parentId'] = max(replies, key=lambda reply: reply.get('timestamp', 0))['id']
            if is_active:
                message['meta']['status'] = 'pending'
            if message['parentId'] in messages:
                messages[message['parentId']].setdefault('childrenIds', []).append(message['id'])
                await ChatMessages.upsert_message(
                    message['parentId'], chat_id, user.id, messages[message['parentId']], db=session
                )
            chat.updated_at = int(time.time())
            await ChatMessages.upsert_message(message['id'], chat_id, user.id, message, db=session)

    if is_active:
        from open_webui.socket.main import sio

        await sio.emit(
            'events',
            {'chat_id': chat_id, 'message_id': message['id'], 'data': {'type': 'chat:reload'}},
            room=f'user:{user.id}',
        )
    if not await has_active_tasks(request.app.state.redis, chat_id):
        await process_pending_internal_messages(request, chat_id, user.id, run)


async def delegate(
    task: str,
    context: str,
    *,
    title: str = '',
    file_ids: list[str] | None = None,
    model_id: str | None = None,
    request: Request,
    user_data: dict,
    metadata: dict,
    parent_chat_id: str,
    parent_message_id: str | None,
) -> str:
    global _foreground_semaphore

    task = task.strip()
    if not task:
        return 'Error: task must not be empty.'
    title = ' '.join((title or '').split() or task.split())[:60]
    if not parent_chat_id or not user_data.get('id'):
        return 'Error: chat and user context are required.'

    config = await Config.get_many(
        'subagents.max_concurrent',
        'subagents.max_async',
        'subagents.max_iterations',
        'subagents.max_output',
        'subagents.system_prompt',
    )
    max_concurrent = config.get('subagents.max_concurrent')
    max_concurrent = int(max_concurrent) if max_concurrent else None
    max_async = config.get('subagents.max_async')
    max_async = int(max_async) if max_async else None
    max_iterations = config.get('subagents.max_iterations')
    max_iterations = int(max_iterations) if max_iterations else None
    max_output = config.get('subagents.max_output')
    max_output = int(max_output) if max_output else None
    if max_concurrent == -1:
        max_concurrent = None
    elif max_concurrent is not None:
        max_concurrent = max(1, max_concurrent)
    if max_async == -1:
        max_async = None
    elif max_async is not None:
        max_async = max(1, max_async)

    # A channel can't be continued later, and an automation's run ends with its reply.
    background = is_saved_chat_id(parent_chat_id) and not metadata.get('automation_id')

    features = copy.deepcopy(metadata.get('features') or {})
    if (
        background
        and features.get('code_interpreter')
        and await Config.get('code_interpreter.engine', 'pyodide') != 'jupyter'
    ):
        features.pop('code_interpreter')
    folder_id = await Chats.get_chat_folder_id(parent_chat_id, user_data['id']) or metadata.get('folder_id')
    run = {
        'model_id': metadata.get('model_id') or (metadata.get('model') or {}).get('id'),
        'session_id': metadata.get('session_id'),
        'tool_ids': copy.deepcopy(metadata.get('tool_ids') or []),
        'skill_ids': copy.deepcopy(metadata.get('skill_ids') or []),
        'chat_context': copy.deepcopy(metadata.get('chat_context') or {}),
        'filter_ids': copy.deepcopy(metadata.get('filter_ids') or []),
        'machine_id': metadata.get('machine_id'),
        'features': features,
        'files': copy.deepcopy(metadata.get('files') or []),
        'variables': copy.deepcopy(metadata.get('variables') or {}),
        'folder_id': folder_id,
    }
    if not run.get('model_id'):
        return 'Error: model context is required.'
    if model_id:
        available_models = await get_subagent_models(request, UserModel(**user_data), metadata.get('model') or {})
        available_ids = [model['id'] for model in available_models]
        if model_id not in available_ids:
            return (
                f'Error: model {model_id} is not available for sub-agents. '
                f'Available models: {", ".join(available_ids) or "none"}. '
                'Omit model_id to use the current model.'
            )
    model_id = model_id or run['model_id']
    delegated_files = []
    if file_ids:
        requested_file_ids = {str(file_id) for file_id in file_ids if file_id}
        chat_messages = await Chats.get_messages_map_by_chat_id(parent_chat_id) or {}
        # Photos are left out of the request's files, so also look on the chat's messages.
        attached_files = [
            *(metadata.get('files') or []),
            *(
                file
                for message in chat_messages.values()
                if message.get('role') == 'user'
                for file in message.get('files') or []
                if file.get('type') == 'image' or is_raster_image_content_type(file.get('content_type'))
            ),
        ]
        found_file_ids = set()
        for file in attached_files:
            nested_file = file.get('file') if isinstance(file.get('file'), dict) else {}
            keys = {str(value) for value in (file.get('id'), file.get('url'), nested_file.get('id')) if value}
            if keys & requested_file_ids and not keys & found_file_ids:
                delegated_files.append(copy.deepcopy(file))
                found_file_ids |= keys
        missing_file_ids = sorted(requested_file_ids - found_file_ids)
        if missing_file_ids:
            return f'Error: file_ids not attached or unavailable: {", ".join(missing_file_ids)}'
    run['files'] = [
        file
        for file in delegated_files
        if file.get('type') != 'image' and not is_raster_image_content_type(file.get('content_type'))
    ]

    delegation_id = f'deleg_{uuid4().hex[:8]}'
    foreground_semaphore = None
    if background:
        async with _background_lock:
            if max_async is not None and len(_background_active) >= max_async:
                return (
                    f'Error: Async subagent capacity reached ({max_async} running). '
                    'Wait for one to finish or increase subagents.max_async.'
                )
            _background_active.add(delegation_id)
    elif max_concurrent is not None:
        if _foreground_semaphore is None:
            _foreground_semaphore = asyncio.Semaphore(max_concurrent)
        foreground_semaphore = _foreground_semaphore
        await foreground_semaphore.acquire()

    mode = 'background' if background else 'foreground'
    try:
        user = UserModel(**user_data)
        chat_id = str(uuid4())
        user_message_id = str(uuid4())
        assistant_message_id = str(uuid4())
        prompt = f'{task}\n\n## Context\n{context}' if context else task
        prompt_files = delegated_files
        chat_context = copy.deepcopy(run.get('chat_context') or {})
        system_messages = add_or_update_system_message(
            f'{str(config.get("subagents.system_prompt") or "").strip() or DEFAULT_SUBAGENT_SYSTEM_PROMPT}\n\n'
            f'The lead agent is chat {parent_chat_id}. The lead gets your final reply, so put all findings there. '
            'Message it only if you are blocked.',
            [*chat_context.get('messages', [])],
            append=True,
        )
        user_message = {
            'id': user_message_id,
            'parentId': None,
            'childrenIds': [assistant_message_id],
            'role': 'user',
            'content': prompt,
            'timestamp': int(time.time()),
            'models': [model_id],
            **({'files': prompt_files} if prompt_files else {}),
        }
        chat = await Chats.insert_new_chat(
            chat_id,
            user.id,
            ChatForm(
                chat={
                    'id': chat_id,
                    'title': title,
                    'models': [model_id],
                    'machine_id': machine_id_of(run),
                    # Read when the user's answer or message continues this chat.
                    'params': {
                        **(chat_context.get('params') or {}),
                        'system': '\n\n'.join(get_content_from_message(message) or '' for message in system_messages),
                    },
                    'history': {
                        'currentId': assistant_message_id,
                        'messages': {
                            user_message_id: user_message,
                            assistant_message_id: {
                                'id': assistant_message_id,
                                'parentId': user_message_id,
                                'childrenIds': [],
                                'role': 'assistant',
                                'content': '',
                                'done': False,
                                'model': model_id,
                                'timestamp': int(time.time()),
                            },
                        },
                    },
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt,
                            **({'files': prompt_files} if prompt_files else {}),
                        }
                    ],
                    'files': prompt_files,
                }
            ),
            internal_meta={
                'internal': True,
                'type': 'subagent',
                'parent_chat_id': parent_chat_id,
                'parent_message_id': parent_message_id,
                'delegation_id': delegation_id,
                'mode': mode,
            },
        )
        if not chat:
            raise RuntimeError('Failed to create sub-agent chat')
    except Exception as exc:
        if background:
            async with _background_lock:
                _background_active.discard(delegation_id)
        elif foreground_semaphore:
            foreground_semaphore.release()
        prefix = 'background ' if background else ''
        return f'Error: failed to create {prefix}sub-agent: {exc}'

    async def run_reserved() -> dict:
        from open_webui.socket.main import sio

        reply_id = assistant_message_id
        try:
            await sio.emit(
                'events', {'chat_id': parent_chat_id, 'data': {'type': 'chat:children'}}, room=f'user:{user.id}'
            )
            child_request = await _build_request(request, user.id, internal=True)
            child_request.state.max_tool_call_iterations = max_iterations
            child_request.state.chat_context = chat_context
            form_data = {
                'model': model_id,
                'params': chat_context.get('params') or {},
                'messages': [*system_messages, {'role': 'user', 'content': prompt}],
                'stream': True,
                'chat_id': chat_id,
                'id': assistant_message_id,
                'parent_id': None,
                'user_message': user_message,
                'session_id': run.get('session_id') or f'subagent:{chat_id}',
                'background_tasks': {},
                'tool_ids': run.get('tool_ids') or [],
                'skill_ids': run.get('skill_ids') or [],
                'filter_ids': run.get('filter_ids') or [],
                'features': run.get('features') or {},
                'files': run.get('files') or [],
                'variables': run.get('variables') or {},
                'chat_variables': chat_context.get('chat_variables'),
                'folder_id': run.get('folder_id'),
            }
            if machine_id_of(run):
                form_data['machine_id'] = machine_id_of(run)
            await request.app.state.CHAT_COMPLETION_HANDLER(child_request, form_data, user=user)
            # Messages sent to it meanwhile are answered in a later reply, and the user's decision on a tool approval
            # continues a paused one.
            while True:
                child = await Chats.get_chat_by_id(chat_id)
                reply_id = child.current_message_id if child else reply_id
                message = await Chats.get_message_by_id_and_message_id(chat_id, reply_id)
                if not message or message.get('done') is not False:
                    break
                if metadata.get('automation_id') and has_pending_tool_approval(message.get('output')):
                    break
                await asyncio.sleep(1)
            if not message:
                return {
                    'status': 'error',
                    'summary': '',
                    'error': 'Sub-agent chat or completion message no longer exists.',
                }

            summary = message.get('content') or ''
            if isinstance(summary, list):
                summary = ''.join(
                    str(item.get('text', ''))
                    for item in summary
                    if isinstance(item, dict) and item.get('type') == 'text'
                )
            if not summary:
                summary = ''.join(
                    str(part.get('text', ''))
                    for item in message.get('output') or []
                    if item.get('type') == 'message'
                    for part in item.get('content') or []
                    if part.get('type') == 'output_text'
                )
            if max_output is not None and len(summary) > max_output:
                summary = f'{summary[:max_output]}\n\n[output truncated]'
            error = message.get('error')
            if isinstance(error, dict):
                error = error.get('content') or 'Sub-agent failed.'
            # Still paused: an automation has no one to approve it.
            pending = next(
                (item for item in message.get('output') or [] if item.get('status') == 'pending'),
                None,
            )
            if not error and pending and message.get('done') is False:
                return {
                    'status': 'waiting',
                    'summary': summary,
                    'error': f'Sub-agent has not finished. It is waiting for the user to approve {pending.get("name")}',
                }
            return {
                'status': 'error' if error else 'completed',
                'summary': summary or ('Sub-agent produced no output.' if not error else ''),
                'error': error,
            }
        except asyncio.CancelledError:
            await Chats.upsert_message_to_chat_by_id_and_message_id(
                chat_id,
                reply_id,
                {'done': True, 'error': {'content': 'Sub-agent cancelled.'}},
            )
            raise
        except Exception as exc:
            await Chats.upsert_message_to_chat_by_id_and_message_id(
                chat_id,
                reply_id,
                {'done': True, 'error': {'content': str(exc)}},
            )
            raise
        finally:
            if background:
                async with _background_lock:
                    _background_active.discard(delegation_id)
            elif foreground_semaphore:
                foreground_semaphore.release()
            # The reply ends while this task still counts as active, so it doesn't tell the chat itself.
            await sio.emit(
                'events',
                {
                    'chat_id': chat_id,
                    'message_id': assistant_message_id,
                    'data': {'type': 'chat:active', 'data': {'active': False}},
                },
                room=f'user:{user.id}',
            )

    async def run_background() -> dict:
        started_at = time.time()
        cancelled = False
        try:
            result = await run_reserved()
        except asyncio.CancelledError:
            result = {'status': 'interrupted', 'summary': '', 'error': 'cancelled'}
            cancelled = True
        except Exception as exc:
            result = {'status': 'error', 'summary': '', 'error': str(exc)}

        duration = f'{time.time() - started_at:.1f}s'
        lines = [
            f'[ASYNC SUBAGENT COMPLETE - {delegation_id}]',
            (
                'A background subagent you dispatched earlier has finished. '
                'If other sub-agents are still running, reply with one line. '
                'Otherwise answer in full using every report.'
            ),
            '',
            f'Title: {title}',
            f'Original task: {task}',
        ]
        if context:
            lines.append(f'Context provided: {context}')
        lines.extend(
            [
                f'Subagent chat: {chat_id}',
                f'Status: {result.get("status", "completed")}   Duration: {duration}',
                '--- RESULT ---',
            ]
        )
        if result.get('status') == 'completed':
            lines.append(result.get('summary') or 'Subagent completed without a final summary.')
        elif result.get('status') == 'interrupted':
            lines.append('The subagent was interrupted before completing.')
            if result.get('summary'):
                lines.extend(['Partial output:', result['summary']])
        else:
            detail = f' {result.get("error")}' if result.get('error') else ''
            lines.append(f'The subagent did not complete successfully.{detail}')
            if result.get('summary'):
                lines.extend(['Partial output:', result['summary']])

        await insert_internal_message(
            request,
            user,
            parent_chat_id,
            parent_message_id,
            '\n'.join(lines),
            {'type': 'subagent', 'delegation_id': delegation_id, 'subagent_chat_id': chat_id},
            run,
        )
        if cancelled:
            raise asyncio.CancelledError
        return result

    try:
        _, child_task = await create_task(
            request.app.state.redis,
            run_background() if background else run_reserved(),
            id=chat_id,
            task_id=delegation_id,
        )
    except Exception as exc:
        if background:
            async with _background_lock:
                _background_active.discard(delegation_id)
        elif foreground_semaphore:
            foreground_semaphore.release()
        return f'Error: {exc}'

    if background:
        return JSONCodec.dumps(
            {
                'status': 'dispatched',
                'delegation_id': delegation_id,
                'subagent_chat_id': chat_id,
                'mode': 'background',
                'task': task,
                'note': 'Its report starts your next reply. Do only work you did not delegate, then end this reply '
                'with one line on what is running. Answer in full once every report is in. '
                'Do not check on it, ask for it or set a timer.',
            },
            ensure_ascii=False,
        )

    try:
        result = await child_task
    except asyncio.CancelledError:
        if asyncio.current_task() and asyncio.current_task().cancelling():
            raise
        return 'Error: sub-agent was cancelled.'
    except Exception as exc:
        return f'Error: {exc}'

    if result.get('status') != 'completed':
        error_text = f'Error: {result.get("error") or "sub-agent failed."}\nSubagent chat: {chat_id}'
        if result.get('summary'):
            return f'{error_text}\nPartial output:\n{result["summary"]}'
        return error_text
    return f'Subagent chat: {chat_id}\n\n{result.get("summary") or "Sub-agent produced no output."}'

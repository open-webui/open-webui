from __future__ import annotations

import asyncio
import copy
import json
import time
from datetime import timedelta
from uuid import uuid4

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from open_webui.internal.db import get_async_db
from open_webui.models.chat_messages import ChatMessages
from open_webui.models.chats import Chat, ChatForm, Chats
from open_webui.models.config import Config
from open_webui.models.users import UserModel, Users
from open_webui.tasks import create_task, has_active_tasks
from open_webui.utils.auth import create_token
from sqlalchemy import select
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
_parent_locks: dict[str, asyncio.Lock] = {}


def _build_request(source: Request, user_id: str, *, internal: bool) -> Request:
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.0'},
        'method': 'POST',
        'path': '/api/v1/subagents/internal',
        'query_string': b'',
        'headers': Headers({}).raw,
        'client': ('127.0.0.1', 0),
        'server': ('127.0.0.1', 80),
        'scheme': 'http',
        'app': source.app,
    }
    request = Request(scope)
    token = create_token(
        data={'id': user_id, 'typ': 'subagent'},
        expires_delta=timedelta(hours=1),
    )
    request.state.token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
    request.state.enable_api_keys = False
    if internal:
        request.state.internal = True
    return request


async def process_pending_internal_messages(
    source_request: Request,
    parent_chat_id: str,
    user_id: str,
    run: dict,
) -> None:
    lock = _parent_locks.setdefault(parent_chat_id, asyncio.Lock())
    while await has_active_tasks(source_request.app.state.redis, parent_chat_id):
        await asyncio.sleep(0.25)

    async with lock:
        if await has_active_tasks(source_request.app.state.redis, parent_chat_id):
            return

        user = await Users.get_user_by_id(user_id)
        if not user:
            return

        async with get_async_db() as db:
            try:
                stmt = select(Chat).where(Chat.id == parent_chat_id, Chat.user_id == user_id)
                if db.bind.dialect.name == 'postgresql':
                    stmt = stmt.with_for_update()
                result = await db.execute(stmt)
                chat = result.scalar_one_or_none()
                if not chat:
                    return

                compact_chat = await ChatMessages.compact_legacy_chat_in_session(
                    db,
                    parent_chat_id,
                    user_id,
                    chat.chat,
                )
                normalized_legacy = compact_chat != (chat.chat or {})

                pending = await ChatMessages.get_pending_internal_leaf_messages_in_session(db, parent_chat_id)
                if not pending:
                    if normalized_legacy:
                        chat.chat = compact_chat
                        await db.commit()
                    return

                first = pending[0]
                first_meta = first.get('meta') or {}
                kind = (
                    'timer' if first_meta.get('internal') is True and first_meta.get('type') == 'timer' else 'subagent'
                )
                parent_id = first.get('parentId')
                if kind == 'timer' and first_meta.get('timer_id'):
                    timer = await db.get(Chat, first_meta['timer_id'])
                    run = {**run, **(((timer.meta or {}).get('run') if timer else None) or {})}
                model_id = first.get('model') or run['model_id']
                if kind == 'timer':
                    batch = [first]
                else:
                    batch = [
                        message
                        for message in pending
                        for meta in [message.get('meta') or {}]
                        if message.get('parentId') == parent_id
                        and (message.get('model') or model_id) == model_id
                        and meta.get('internal') is True
                        and meta.get('type') == 'subagent'
                        and meta.get('status') in (None, 'pending')
                    ]
                combined_content = '\n\n'.join(
                    message.get('content', '') for message in batch if message.get('content')
                )
                if kind == 'timer':
                    timer_ids = [
                        message['meta']['timer_id'] for message in batch if (message.get('meta') or {}).get('timer_id')
                    ]
                    combined_meta = {'internal': True, 'type': 'timer'}
                    if len(timer_ids) == 1:
                        combined_meta['timer_id'] = timer_ids[0]
                    elif timer_ids:
                        combined_meta['timer_ids'] = timer_ids
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
                    combined_meta = {'internal': True, 'type': 'subagent'}
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
                removed_ids = set() if reuse_message else {message['id'] for message in batch}
                assistant_message_id = str(uuid4())
                message_list = (
                    await ChatMessages.get_message_branch_in_session(db, parent_chat_id, parent_id) if parent_id else []
                )
                system_prompt = run.get('system_prompt')
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

                await ChatMessages.delete_message_ids_in_session(db, parent_chat_id, removed_ids)
                await ChatMessages.bulk_upsert_messages_in_session(
                    db,
                    parent_chat_id,
                    user_id,
                    {
                        user_message_id: user_message,
                        assistant_message_id: assistant_message,
                    },
                )
                updated_chat = copy.deepcopy(compact_chat)
                updated_chat['history'] = {
                    **(updated_chat.get('history') or {}),
                    'currentId': assistant_message_id,
                }
                chat.chat = updated_chat
                chat.updated_at = int(time.time())
                await db.commit()
            except Exception:
                await db.rollback()
                raise

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

        form_data = {
            'model': model_id,
            'messages': [
                *([{'role': 'system', 'content': system_prompt}] if system_prompt else []),
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
            'files': run.get('files') or [],
            'variables': run.get('variables') or {},
        }
        if run.get('terminal_id'):
            form_data['terminal_id'] = run['terminal_id']

        request = _build_request(source_request, user.id, internal=False)
        await source_request.app.state.CHAT_COMPLETION_HANDLER(request, form_data, user=user)


async def delegate(
    task: str,
    context: str,
    background: bool,
    *,
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
    if not parent_chat_id or not user_data.get('id'):
        return 'Error: chat and user context are required.'

    config = await Config.get_many(
        'subagents.background_enabled',
        'subagents.max_concurrent',
        'subagents.max_async',
        'subagents.max_iterations',
        'subagents.max_output',
        'subagents.system_prompt',
    )
    max_concurrent = int(config.get('subagents.max_concurrent') or 20)
    max_async = int(config.get('subagents.max_async') or 20)
    max_iterations = int(config.get('subagents.max_iterations') or 30)
    max_output = int(config.get('subagents.max_output') or 30_000)
    if max_concurrent != -1:
        max_concurrent = max(1, max_concurrent)
    if max_async != -1:
        max_async = max(1, max_async)

    if background and not config.get('subagents.background_enabled'):
        return 'Error: background sub-agents are disabled in settings.'

    features = copy.deepcopy(metadata.get('features') or {})
    if (
        background
        and features.get('code_interpreter')
        and await Config.get('code_interpreter.engine', 'pyodide') != 'jupyter'
    ):
        features.pop('code_interpreter')
    run = {
        'model_id': metadata.get('model_id') or (metadata.get('model') or {}).get('id'),
        'session_id': metadata.get('session_id'),
        'tool_ids': copy.deepcopy(metadata.get('tool_ids') or []),
        'skill_ids': copy.deepcopy(metadata.get('skill_ids') or []),
        'system_prompt': metadata.get('system_prompt'),
        'tool_servers': [] if background else copy.deepcopy(metadata.get('tool_servers') or []),
        'filter_ids': copy.deepcopy(metadata.get('filter_ids') or []),
        'terminal_id': metadata.get('terminal_id'),
        'features': features,
        'files': copy.deepcopy(metadata.get('files') or []),
        'variables': copy.deepcopy(metadata.get('variables') or {}),
        'direct': bool(metadata.get('direct')),
    }
    if not run.get('model_id'):
        return 'Error: model context is required.'
    if run.get('direct'):
        return 'Error: sub-agents are unavailable for direct connections.'

    delegation_id = f'deleg_{uuid4().hex[:8]}'
    foreground_semaphore = None
    if background:
        async with _background_lock:
            if max_async != -1 and len(_background_active) >= max_async:
                return (
                    f'Error: Async subagent capacity reached ({max_async} running). '
                    'Wait for one to finish or increase subagents.max_async.'
                )
            _background_active.add(delegation_id)
    elif max_concurrent != -1:
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
        chat = await Chats.insert_new_chat(
            chat_id,
            user.id,
            ChatForm(
                chat={
                    'id': chat_id,
                    'title': f'Sub-agent: {task[:60]}',
                    'models': [run['model_id']],
                    'history': {
                        'currentId': assistant_message_id,
                        'messages': {
                            user_message_id: {
                                'id': user_message_id,
                                'parentId': None,
                                'childrenIds': [assistant_message_id],
                                'role': 'user',
                                'content': prompt,
                                'timestamp': int(time.time()),
                                'models': [run['model_id']],
                            },
                            assistant_message_id: {
                                'id': assistant_message_id,
                                'parentId': user_message_id,
                                'childrenIds': [],
                                'role': 'assistant',
                                'content': '',
                                'done': False,
                                'model': run['model_id'],
                                'timestamp': int(time.time()),
                            },
                        },
                    },
                    'messages': [{'role': 'user', 'content': prompt}],
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
        try:
            child_request = _build_request(request, user.id, internal=True)
            child_request.state.max_tool_call_iterations = max_iterations
            parent_system_prompt = run.get('system_prompt') or ''
            subagent_system_prompt = (
                str(config.get('subagents.system_prompt') or '').strip() or DEFAULT_SUBAGENT_SYSTEM_PROMPT
            )
            form_data = {
                'model': run['model_id'],
                'messages': [
                    {
                        'role': 'system',
                        'content': (
                            f'{parent_system_prompt}\n\n{subagent_system_prompt}'
                            if parent_system_prompt
                            else subagent_system_prompt
                        ),
                    },
                    {'role': 'user', 'content': prompt},
                ],
                'stream': True,
                'chat_id': chat_id,
                'id': assistant_message_id,
                'parent_id': None,
                'user_message': {
                    'id': user_message_id,
                    'parentId': None,
                    'role': 'user',
                    'content': prompt,
                },
                'session_id': run.get('session_id') or f'subagent:{chat_id}',
                'background_tasks': {},
                'tool_ids': run.get('tool_ids') or [],
                'skill_ids': run.get('skill_ids') or [],
                'filter_ids': run.get('filter_ids') or [],
                'features': run.get('features') or {},
                'files': run.get('files') or [],
                'variables': run.get('variables') or {},
            }
            if run.get('terminal_id'):
                form_data['terminal_id'] = run['terminal_id']
            if run.get('tool_servers'):
                form_data['tool_servers'] = run['tool_servers']
            await request.app.state.CHAT_COMPLETION_HANDLER(child_request, form_data, user=user)
            message = await Chats.get_message_by_id_and_message_id(chat_id, assistant_message_id)
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
            if len(summary) > max_output:
                summary = f'{summary[:max_output]}\n\n[output truncated]'
            error = message.get('error')
            return {
                'status': 'error' if error else 'completed',
                'summary': summary or ('Sub-agent produced no output.' if not error else ''),
                'error': error,
            }
        except asyncio.CancelledError:
            await Chats.upsert_message_to_chat_by_id_and_message_id(
                chat_id,
                assistant_message_id,
                {'done': True, 'error': {'content': 'Sub-agent cancelled.'}},
            )
            raise
        except Exception as exc:
            await Chats.upsert_message_to_chat_by_id_and_message_id(
                chat_id,
                assistant_message_id,
                {'done': True, 'error': {'content': str(exc)}},
            )
            raise
        finally:
            if background:
                async with _background_lock:
                    _background_active.discard(delegation_id)
            elif foreground_semaphore:
                foreground_semaphore.release()

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
                'The original task source is included so you can decide whether '
                'to use the result or continue without it.'
            ),
            '',
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

        pending_message_id = str(uuid4())
        pending_meta = {
            'internal': True,
            'type': 'subagent',
            'delegation_id': delegation_id,
            'subagent_chat_id': chat_id,
        }
        pending_message = {
            'id': pending_message_id,
            'parentId': None,
            'childrenIds': [],
            'role': 'user',
            'content': '\n'.join(lines),
            'model': run['model_id'],
            'meta': pending_meta,
            'timestamp': int(time.time()),
        }

        lock = _parent_locks.setdefault(parent_chat_id, asyncio.Lock())
        async with lock:
            async with get_async_db() as db:
                try:
                    stmt = select(Chat).where(Chat.id == parent_chat_id, Chat.user_id == user.id)
                    if db.bind.dialect.name == 'postgresql':
                        stmt = stmt.with_for_update()
                    result_row = await db.execute(stmt)
                    parent = result_row.scalar_one_or_none()
                    if not parent:
                        if cancelled:
                            raise asyncio.CancelledError
                        return result

                    compact_chat = await ChatMessages.compact_legacy_chat_in_session(
                        db,
                        parent_chat_id,
                        user.id,
                        parent.chat,
                    )
                    result_parent_id = await ChatMessages.get_latest_eligible_assistant_id_in_session(
                        db,
                        parent_chat_id,
                    )
                    result_parent_id = result_parent_id or parent_message_id
                    pending_message['parentId'] = result_parent_id
                    if await has_active_tasks(request.app.state.redis, parent_chat_id):
                        pending_message['meta']['status'] = 'pending'

                    await ChatMessages.upsert_message_in_session(
                        db,
                        pending_message_id,
                        parent_chat_id,
                        user.id,
                        pending_message,
                    )
                    parent.chat = compact_chat
                    parent.updated_at = int(time.time())
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise

        if pending_message['meta'].get('status') == 'pending':
            from open_webui.socket.main import sio

            await sio.emit(
                'events',
                {
                    'chat_id': parent_chat_id,
                    'message_id': pending_message_id,
                    'data': {'type': 'chat:reload'},
                },
                room=f'user:{user.id}',
            )
        if not await has_active_tasks(request.app.state.redis, parent_chat_id):
            await process_pending_internal_messages(request, parent_chat_id, user.id, run)
        if cancelled:
            raise asyncio.CancelledError
        return result

    try:
        _, child_task = await create_task(
            request.app.state.redis,
            run_background() if background else run_reserved(),
            id=chat_id,
        )
    except Exception as exc:
        if background:
            async with _background_lock:
                _background_active.discard(delegation_id)
        elif foreground_semaphore:
            foreground_semaphore.release()
        return f'Error: {exc}'

    if background:
        return json.dumps(
            {
                'status': 'dispatched',
                'delegation_id': delegation_id,
                'subagent_chat_id': chat_id,
                'mode': 'background',
                'task': task,
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
        return f'Error: {result.get("error") or "sub-agent failed."}'
    return result.get('summary') or 'Sub-agent produced no output.'

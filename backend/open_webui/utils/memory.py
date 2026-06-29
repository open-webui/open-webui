from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from fastapi import HTTPException

from open_webui.models.config import Config
from open_webui.models.memories import Memories
from open_webui.utils.misc import add_or_update_system_message, get_content_from_message

log = logging.getLogger(__name__)

MEMORY_CONTEXT_OPEN = '<memory_context>'
MEMORY_CONTEXT_CLOSE = '</memory_context>'


def clean_memory_content(content: str | None) -> str:
    value = (content or '').strip()
    if not value:
        raise HTTPException(status_code=400, detail='Memory content cannot be empty')
    return value


def clean_memory_path(path: str | None) -> str | None:
    value = re.sub(r'/+', '/', (path or '').strip().strip('/'))
    if not value:
        return None
    parts = value.split('/')
    if any(part in {'', '.', '..'} for part in parts) or any(ord(char) < 32 for char in value):
        raise HTTPException(status_code=400, detail='Invalid memory path')
    return value


def memory_vector_text(content: str, path: str | None = None) -> str:
    path = clean_memory_path(path)
    return f'{path}\n{content}' if path else content


def memory_label(memory) -> str:
    return f'{memory.path}: {memory.content}' if memory.path else memory.content


def _path_parts(path: str | None) -> list[str]:
    return [part for part in (path or '').split('/') if part]


def _parent_path(path: str | None) -> str | None:
    parts = _path_parts(path)
    return '/'.join(parts[:-1]) if len(parts) > 1 else None


def _path_rank(memory_path: str | None, lookup_path: str | None) -> tuple | None:
    if not lookup_path:
        return None

    memory_path = clean_memory_path(memory_path)
    lookup_path = clean_memory_path(lookup_path)
    if not memory_path or not lookup_path:
        return None

    if memory_path == lookup_path:
        return (0, 0)
    if memory_path.startswith(f'{lookup_path}/'):
        return (1, len(_path_parts(memory_path)) - len(_path_parts(lookup_path)))
    if lookup_path.startswith(f'{memory_path}/'):
        return (2, len(_path_parts(lookup_path)) - len(_path_parts(memory_path)))
    if _parent_path(memory_path) and _parent_path(memory_path) == _parent_path(lookup_path):
        return (3, 0)

    memory_parts = set(_path_parts(memory_path))
    lookup_parts = set(_path_parts(lookup_path))
    shared = len(memory_parts & lookup_parts)
    if shared:
        return (4, -shared)
    if _path_parts(memory_path)[-1:] == _path_parts(lookup_path)[-1:]:
        return (5, 0)

    return None


def _memory_matches_query(memory, query: str) -> bool:
    value = query.strip().lower()
    if not value:
        return True
    return value in (memory.content or '').lower() or value in (memory.path or '').lower()


def search_memory_rows(
    memories: list,
    *,
    query: str | None = None,
    path: str | None = None,
    memory_id: str | None = None,
    memory_type: str = 'all',
    limit: int = 20,
) -> list:
    rows = list(memories or [])
    if memory_id:
        rows = [memory for memory in rows if memory.id == memory_id]
    if memory_type != 'all':
        rows = [memory for memory in rows if memory.type == memory_type]

    query = (query or '').strip()
    lookup_path = clean_memory_path(path)
    if lookup_path:
        basename = _path_parts(lookup_path)[-1] if _path_parts(lookup_path) else lookup_path

        def related(memory) -> bool:
            rank = _path_rank(memory.path, lookup_path)
            if rank is not None:
                return True
            haystack = f'{memory.path or ""}\n{memory.content or ""}'.lower()
            return lookup_path.lower() in haystack or basename.lower() in haystack

        rows = [memory for memory in rows if related(memory)]

    if query:
        rows = [memory for memory in rows if _memory_matches_query(memory, query)]

    def sort_key(memory):
        rank = _path_rank(memory.path, lookup_path) if lookup_path else None
        return rank if rank is not None else (9, 0), -(memory.updated_at or 0)

    return sorted(rows, key=sort_key)[: max(1, min(limit or 20, 100))]


def list_memory_path_groups(
    memories: list,
    *,
    query: str = '',
    memory_type: str = 'all',
    limit: int = 100,
) -> dict:
    rows = [
        memory
        for memory in (memories or [])
        if (memory_type == 'all' or memory.type == memory_type) and _memory_matches_query(memory, query)
    ]
    grouped: dict[tuple[str | None, str], dict] = {}
    for memory in rows:
        key = (memory.path, memory.type)
        group = grouped.setdefault(
            key,
            {
                'path': memory.path,
                'type': memory.type,
                'count': 0,
                'updated_at': 0,
                'children': [],
            },
        )
        group['count'] += 1
        group['updated_at'] = max(group['updated_at'], memory.updated_at or 0)

    paths = [path for path, _ in grouped if path]
    for group in grouped.values():
        path = group['path']
        if not path:
            continue
        prefix = f'{path}/'
        children = []
        for candidate in paths:
            if not candidate.startswith(prefix):
                continue
            remainder = candidate[len(prefix) :]
            child = f'{prefix}{remainder.split("/", 1)[0]}'
            if child not in children:
                children.append(child)
        group['children'] = children[:20]

    groups = sorted(grouped.values(), key=lambda item: item['updated_at'], reverse=True)
    return {'paths': groups[: max(1, min(limit or 100, 500))], 'count': len(groups)}


def read_memory_path_rows(
    memories: list,
    *,
    path: str,
    memory_type: str = 'all',
    include_children: bool = True,
    limit: int = 50,
) -> dict:
    lookup_path = clean_memory_path(path)
    if not lookup_path:
        raise HTTPException(status_code=400, detail='Memory path is required')

    rows = [memory for memory in (memories or []) if memory_type == 'all' or memory.type == memory_type]
    path_set = {memory.path for memory in rows if memory.path}
    parents = [
        '/'.join(_path_parts(lookup_path)[:idx])
        for idx in range(1, len(_path_parts(lookup_path)))
        if '/'.join(_path_parts(lookup_path)[:idx]) in path_set
    ]
    children = sorted(
        {
            f'{lookup_path}/{memory.path[len(lookup_path) + 1 :].split("/", 1)[0]}'
            for memory in rows
            if memory.path and memory.path.startswith(f'{lookup_path}/')
        }
    )

    def selected(memory) -> bool:
        if memory.path == lookup_path:
            return True
        if memory.path in parents:
            return True
        return bool(include_children and memory.path and memory.path.startswith(f'{lookup_path}/'))

    selected_rows = [memory for memory in rows if selected(memory)]

    def sort_key(memory):
        if memory.path == lookup_path:
            return (0, 0, -(memory.updated_at or 0))
        if memory.path and memory.path.startswith(f'{lookup_path}/'):
            return (1, len(_path_parts(memory.path)), -(memory.updated_at or 0))
        return (2, -len(_path_parts(memory.path)), -(memory.updated_at or 0))

    return {
        'path': lookup_path,
        'parents': parents,
        'children': children[:50],
        'memories': sorted(selected_rows, key=sort_key)[: max(1, min(limit or 50, 100))],
    }


def memory_path_hints(query: str, memories: list, limit: int = 6) -> list[str]:
    lowered = (query or '').lower()
    if not lowered:
        return []

    hints: list[str] = []
    for memory in memories or []:
        path = memory.path
        if not path or path in hints:
            continue
        parts = _path_parts(path)
        last = parts[-1] if parts else path
        if path.lower() in lowered or last.lower() in lowered:
            hints.append(path)
        elif any(len(part) >= 3 and part.lower() in lowered for part in parts):
            hints.append(path)
        if len(hints) >= limit:
            break
    return hints


def validate_memory_operations(form_data) -> list[dict]:
    if not form_data.operations:
        raise HTTPException(status_code=400, detail='No memory operations provided')

    operations = []
    for operation in form_data.operations:
        op = operation.model_dump()
        action = op.get('action')

        if action == 'add':
            op['content'] = clean_memory_content(op.get('content'))
            op['type'] = Memories.normalize_memory_type(op.get('type'))
            op['path'] = clean_memory_path(op.get('path'))
        elif action == 'replace':
            if not op.get('id'):
                raise HTTPException(status_code=400, detail='Memory id is required for replace')
            op['content'] = clean_memory_content(op.get('content'))
            if op.get('type') is not None:
                op['type'] = Memories.normalize_memory_type(op.get('type'))
            op['path'] = clean_memory_path(op.get('path'))
        elif action == 'move':
            if not op.get('id'):
                raise HTTPException(status_code=400, detail='Memory id is required for move')
            op['path'] = clean_memory_path(op.get('path'))
        elif action == 'remove':
            if not op.get('id'):
                raise HTTPException(status_code=400, detail='Memory id is required for remove')
        else:
            raise HTTPException(status_code=400, detail=f'Unsupported memory operation: {action}')

        operations.append(op)

    return operations


def model_allows_memory(model: dict | None) -> bool:
    return (model or {}).get('info', {}).get('meta', {}).get('capabilities', {}).get('memory', True)


async def add_memory_context(request, form_data: dict, user, model: dict | None = None):
    if not model_allows_memory(model):
        return form_data

    user_messages = []
    for message in reversed(form_data.get('messages', [])):
        if message.get('role') != 'user':
            continue

        content = get_content_from_message(message)
        if isinstance(content, str) and content.strip():
            user_messages.append(content.strip())

        if len(user_messages) >= 7:
            break

    query = '\n\n'.join(reversed(user_messages))[-4000:]
    if not query:
        return form_data

    all_memories = await Memories.get_memories_by_user_id(user.id)
    results = None
    try:
        from open_webui.routers.memories import QueryMemoryForm, query_memory

        results = await query_memory(request, QueryMemoryForm(content=query, k=8), user)
    except Exception as e:
        log.debug(e)

    sections = {'user': [], 'neighborhood': [], 'context': []}
    seen_ids = set()
    for memory in sorted(
        [memory for memory in (all_memories or []) if memory.type == 'user'],
        key=lambda item: (item.path or '', item.updated_at),
    ):
        seen_ids.add(memory.id)
        sections['user'].append(memory_label(memory))

    for hint in memory_path_hints(query, all_memories):
        for memory in search_memory_rows(
            all_memories,
            path=hint,
            memory_type='context',
            limit=4,
        ):
            if memory.id in seen_ids:
                continue
            seen_ids.add(memory.id)
            sections['neighborhood'].append(memory_label(memory))

    if results and hasattr(results, 'documents') and results.documents:
        for doc_idx, doc in enumerate(results.documents[0]):
            if not doc:
                continue

            metadata = {}
            if results.metadatas and results.metadatas[0] and len(results.metadatas[0]) > doc_idx:
                metadata = results.metadatas[0][doc_idx] or {}

            memory_id = None
            if results.ids and results.ids[0] and len(results.ids[0]) > doc_idx:
                memory_id = results.ids[0][doc_idx]
            if memory_id and memory_id in seen_ids:
                continue
            if memory_id:
                seen_ids.add(memory_id)

            content = str(doc)
            if metadata.get('path') and content.startswith(f'{metadata.get("path")}\n'):
                content = content[len(metadata.get('path')) + 1 :]
            label = f'{metadata.get("path")}: {content}' if metadata.get('path') else content
            sections[Memories.normalize_memory_type(metadata.get('type'))].append(label)

    parts = []
    if sections['user']:
        parts.append('[User Memory]\n' + '\n'.join(f'- {memory}' for memory in sections['user']))
    if sections['neighborhood']:
        parts.append('[Memory Neighborhood]\n' + '\n'.join(f'- {memory}' for memory in sections['neighborhood']))
    if sections['context']:
        parts.append('[Relevant Context]\n' + '\n'.join(f'- {memory}' for memory in sections['context']))
    if not parts:
        return form_data

    config = await Config.get_many('memories.user_char_limit', 'memories.context_char_limit')
    try:
        user_limit = max(250, int(config.get('memories.user_char_limit') or 2000))
    except Exception:
        user_limit = 2000
    try:
        context_limit = max(250, int(config.get('memories.context_char_limit') or 2000))
    except Exception:
        context_limit = 2000

    messages = form_data['messages']
    if messages and messages[0].get('role') == 'system':
        content = messages[0].get('content', '')
        if isinstance(content, str) and MEMORY_CONTEXT_OPEN in content:
            start = content.find(MEMORY_CONTEXT_OPEN)
            end = content.find(MEMORY_CONTEXT_CLOSE, start)
            if end != -1:
                messages[0]['content'] = (content[:start] + content[end + len(MEMORY_CONTEXT_CLOSE) :]).strip()

    user_parts = [part for part in parts if part.startswith('[User Memory]')]
    context_parts = [part for part in parts if not part.startswith('[User Memory]')]
    rendered = '\n\n'.join(
        [
            '\n\n'.join(user_parts)[:user_limit],
            '\n\n'.join(context_parts)[:context_limit],
        ]
    ).strip()
    if not rendered:
        return form_data

    memory_context = f'{MEMORY_CONTEXT_OPEN}\n{rendered}\n{MEMORY_CONTEXT_CLOSE}'
    form_data['messages'] = add_or_update_system_message(memory_context, messages, append=True)
    return form_data


async def review_memory_after_turn(
    *,
    request,
    user,
    model: dict | None,
    metadata: dict,
    form_data: dict,
    assistant_message: dict,
    messages: list[dict],
) -> None:
    if not model_allows_memory(model):
        return

    features = metadata.get('features') or {}
    if not features.get('memory'):
        return

    assistant_content = assistant_message.get('content', '')
    if not isinstance(assistant_content, str) or not assistant_content.strip():
        return

    config = await Config.get_many(
        'memories.background_review.enable',
        'memories.review_interval_turns',
    )
    if not config.get('memories.background_review.enable'):
        return

    try:
        interval = max(1, int(config.get('memories.review_interval_turns', 10)))
    except Exception:
        interval = 10

    user_turns = len([message for message in messages if message.get('role') == 'user'])
    if user_turns == 0 or user_turns % interval != 0:
        return

    task = asyncio.create_task(
        _review_memory(
            request=request,
            user=user,
            model=model,
            metadata=metadata,
            form_data=form_data,
            assistant_message=assistant_message,
            messages=messages,
        )
    )

    def log_failure(done_task):
        try:
            done_task.result()
        except Exception as e:
            log.debug(f'Memory review failed: {e}')

    task.add_done_callback(log_failure)


async def _review_memory(
    *,
    request,
    user,
    model: dict | None,
    metadata: dict,
    form_data: dict,
    assistant_message: dict,
    messages: list[dict],
) -> None:
    existing_memories = await Memories.get_memories_by_user_id(user.id)
    existing_lines = [
        f'- id={memory.id} type={memory.type} path={memory.path or ""} content={memory.content}'
        for memory in (existing_memories or [])[:80]
    ]

    assistant_content = assistant_message.get('content', '')
    if not isinstance(assistant_content, str):
        assistant_content = get_content_from_message(assistant_message)

    transcript_lines = []
    for message in messages[-16:]:
        role = message.get('role', '')
        content = message.get('content', '')
        if not isinstance(content, str):
            content = get_content_from_message(message)
        content = content.strip()
        if role not in {'user', 'assistant'} or not content:
            continue
        if len(content) > 1600:
            content = f'{content[:1000]}\n...(truncated)...\n{content[-400:]}'
        transcript_lines.append(f'{role}: {content}')

    if assistant_content.strip():
        assistant_final = assistant_content.strip()
        if len(assistant_final) > 1600:
            assistant_final = f'{assistant_final[:1000]}\n...(truncated)...\n{assistant_final[-400:]}'
        transcript_lines.append(f'assistant_final: {assistant_final}')

    model_id = model.get('id') if isinstance(model, dict) else form_data.get('model')
    operations = await _generate_memory_operations(
        request=request,
        user=user,
        model_id=model_id,
        metadata=metadata,
        existing_text='\n'.join(existing_lines) if existing_lines else '(none)',
        transcript='\n\n'.join(transcript_lines),
    )
    if operations:
        from open_webui.routers.memories import UpdateMemoriesForm, update_memories

        await update_memories(request, UpdateMemoriesForm(operations=operations, source='background_review'), user)


async def _generate_memory_operations(
    *,
    request,
    user,
    model_id: str,
    metadata: dict,
    existing_text: str,
    transcript: str,
) -> list[dict[str, Any]]:
    from open_webui.utils.chat import generate_chat_completion

    review_prompt = f"""Review the completed conversation turn and decide whether long-term memory should change.

Memory types:
- user: durable facts, preferences, or instructions about the user.
- context: other durable context that may help future chats for this user account.

Rules:
- Save only information likely to matter in future chats.
- Do not save secrets, credentials, transient task steps, or unsupported guesses.
- Use path when there is a clear path for the memory.
- Leave path empty when there is no clear place for the memory.
- Prefer replace/move/remove over duplicate add when an existing memory should change.
- Do not invent type, status, trait, score, importance, or stability schemas.
- Return only JSON in this shape:
  {{"operations":[
    {{"action":"add","type":"user|context","path":"...","content":"..."}},
    {{"action":"replace","id":"...","type":"user|context","path":"...","content":"..."}},
    {{"action":"move","id":"...","path":"..."}},
    {{"action":"remove","id":"..."}}
  ]}}
- Use an empty operations array if nothing should be remembered.

Existing memories:
{existing_text}

Conversation:
{transcript}
"""

    response = await generate_chat_completion(
        request,
        form_data={
            'model': model_id,
            'messages': [
                {
                    'role': 'system',
                    'content': "You are Open WebUI's private memory reviewer. Return only valid JSON.",
                },
                {'role': 'user', 'content': review_prompt},
            ],
            'stream': False,
            'metadata': {
                'task': 'memory_review',
                'chat_id': metadata.get('chat_id'),
                'message_id': metadata.get('message_id'),
            },
        },
        user=user,
    )

    if not isinstance(response, dict) or not response.get('choices'):
        return []

    response_message = response.get('choices', [{}])[0].get('message', {})
    content = response_message.get('content') or response_message.get('reasoning_content') or ''
    start = content.find('{')
    end = content.rfind('}')
    if start == -1 or end == -1 or end < start:
        return []

    try:
        parsed = json.loads(content[start : end + 1])
    except Exception:
        return []

    operations = parsed.get('operations') if isinstance(parsed, dict) else None
    return operations if isinstance(operations, list) else []

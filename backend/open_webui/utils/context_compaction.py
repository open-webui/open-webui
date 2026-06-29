from __future__ import annotations

import json
import logging
from typing import Any

from fastapi.responses import JSONResponse

from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.utils.misc import get_content_from_message, get_last_user_message, get_message_list
from open_webui.utils.task import (
    get_task_model_id,
    prompt_template,
    prompt_variables_template,
    replace_messages_variable,
    replace_prompt_variable,
)

log = logging.getLogger(__name__)

DEFAULT_CONTEXT_COMPACTION_PROMPT = """### Task:
Summarize the conversation history that will be compacted out of the active chat context.

### Instructions:
- Preserve key decisions, user preferences, and constraints.
- Preserve files, artifacts, tool results, and code changes that matter going forward.
- Preserve the current task state, unresolved questions, and next steps.
- Be factual and specific. Do not invent details.
- Keep the summary concise, but complete enough for the assistant to continue without the removed messages.

### Previous Summary:
{{PREVIOUS_SUMMARY}}

### Messages Being Compacted:
{{COMPACTED_MESSAGES}}

### Recent Messages Kept In Context:
{{RECENT_MESSAGES}}"""


async def compact_messages_for_request(
    request,
    user,
    messages: list[dict],
    metadata: dict,
    model_id: str,
    models: dict,
    system_prompt: str = '',
) -> tuple[list[dict], str | None, bool]:
    config = await _load_config()
    if not config['enable']:
        return messages, None, False

    messages, previous_summary = _apply_latest_summary_checkpoint(messages)
    token_threshold = _resolve_token_threshold(config['token_threshold'], metadata)
    if not _exceeds_token_threshold(messages, system_prompt, previous_summary, token_threshold) or len(messages) <= 3:
        return messages, previous_summary, False

    boundary = _find_compaction_boundary(messages)
    compacted_messages = messages[:boundary]
    recent_messages = messages[boundary:]
    if not compacted_messages or not recent_messages:
        return messages, previous_summary, False

    event_emitter = None
    if metadata.get('chat_id') and metadata.get('message_id'):
        from open_webui.socket.main import get_event_emitter

        event_emitter = await get_event_emitter(metadata)

    if event_emitter:
        await event_emitter(
            {
                'type': 'context_compaction',
                'data': {
                    'action': 'context_compaction',
                    'description': 'Compacting context',
                    'done': False,
                },
            }
        )

    try:
        summary = await _generate_summary(
            request,
            user,
            model_id,
            models,
            compacted_messages,
            recent_messages,
            previous_summary,
            config['prompt_template'],
        )
    except Exception:
        if event_emitter:
            await event_emitter(
                {
                    'type': 'context_compaction',
                    'data': {
                        'action': 'context_compaction',
                        'description': 'Context compaction failed',
                        'done': True,
                        'error': True,
                    },
                }
            )
        raise

    chat_id = metadata.get('chat_id')
    checkpoint_message_id = metadata.get('user_message_id') or metadata.get('message_id')
    if chat_id and checkpoint_message_id and not chat_id.startswith(('local:', 'channel:')):
        await Chats.upsert_message_to_chat_by_id_and_message_id(
            chat_id,
            checkpoint_message_id,
            {'contextSummary': summary},
        )

    log.info(
        'Compacted chat context for chat=%s checkpoint=%s response=%s dropped=%d kept=%d summary_chars=%d',
        chat_id,
        checkpoint_message_id,
        metadata.get('message_id'),
        len(compacted_messages),
        len(recent_messages),
        len(summary),
    )

    if event_emitter:
        await event_emitter(
            {
                'type': 'context_compaction',
                'data': {
                    'action': 'context_compaction',
                    'description': 'Context compacted',
                    'done': True,
                },
            }
        )

    return recent_messages, summary, True


async def compact_chat_branch(request, user, chat: Any, model_id: str, models: dict) -> dict:
    config = await _load_config()
    if not config['enable']:
        return {'ok': True, 'compacted': False, 'reason': 'disabled'}

    history = (chat.chat or {}).get('history') or {}
    current_id = history.get('currentId')
    if not current_id:
        return {'ok': True, 'compacted': False, 'reason': 'empty'}

    messages_map = await Chats.get_messages_map_by_chat_id(chat.id)
    if not messages_map:
        messages_map = history.get('messages') or {}

    messages, previous_summary = _apply_latest_summary_checkpoint(get_message_list(messages_map, current_id))
    if len(messages) <= 2:
        return {'ok': True, 'compacted': False, 'reason': 'too_short'}

    compacted_messages = messages[:-1]
    recent_messages = messages[-1:]
    summary = await _generate_summary(
        request,
        user,
        model_id,
        models,
        compacted_messages,
        recent_messages,
        previous_summary,
        config['prompt_template'],
    )
    await Chats.upsert_message_to_chat_by_id_and_message_id(chat.id, current_id, {'contextSummary': summary})

    return {
        'ok': True,
        'compacted': True,
        'dropped_messages': len(compacted_messages),
        'kept_messages': len(recent_messages),
        'summary_chars': len(summary),
    }


async def _load_config() -> dict:
    values = await Config.get_many(
        'chat.context_compaction.enable',
        'chat.context_compaction.token_threshold',
        'chat.context_compaction.prompt_template',
    )
    return {
        'enable': bool(values.get('chat.context_compaction.enable', False)),
        'token_threshold': int(values.get('chat.context_compaction.token_threshold', 80000) or 80000),
        'prompt_template': values.get('chat.context_compaction.prompt_template', '') or '',
    }


def _parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _resolve_token_threshold(global_threshold: int, metadata: dict) -> int:
    configured_threshold = _parse_positive_int((metadata.get('params') or {}).get('compact_token_threshold'))
    if configured_threshold is None:
        return global_threshold
    return min(configured_threshold, global_threshold)


def _apply_latest_summary_checkpoint(messages: list[dict]) -> tuple[list[dict], str | None]:
    summary = None
    summary_idx = None

    for idx, message in enumerate(messages):
        value = message.get('contextSummary') or message.get('context_summary')
        if isinstance(value, str) and value.strip():
            summary = value
            summary_idx = idx

    if summary_idx is None:
        return messages, None
    return messages[summary_idx:], summary


def _exceeds_token_threshold(messages: list[dict], system_prompt: str, summary: str | None, threshold: int) -> bool:
    if threshold <= 0:
        return False

    for idx in range(len(messages) - 1, -1, -1):
        usage = messages[idx].get('usage') or (messages[idx].get('info') or {}).get('usage')
        if isinstance(usage, dict) and usage.get('input_tokens'):
            total = int(usage.get('input_tokens') or 0) + int(usage.get('output_tokens') or 0)
            return total + _estimate_messages_tokens(messages[idx + 1 :]) > threshold

    estimated = _estimate_tokens(system_prompt) + _estimate_tokens(summary or '') + _estimate_messages_tokens(messages)
    return estimated > threshold


def _find_compaction_boundary(messages: list[dict]) -> int:
    keep_count = max(2, len(messages) * 2 // 5)
    split = max(1, len(messages) - keep_count)

    while split < len(messages) - 1:
        previous = messages[split - 1] if split > 0 else {}
        current = messages[split]
        if current.get('role') == 'tool' or previous.get('tool_calls') or previous.get('output'):
            split += 1
            continue
        break

    return min(split, len(messages) - 2)


async def _generate_summary(
    request,
    user,
    model_id: str,
    models: dict,
    compacted_messages: list[dict],
    recent_messages: list[dict],
    previous_summary: str | None,
    summary_prompt_template: str,
) -> str:
    from open_webui.utils.chat import generate_chat_completion

    task_model_id = get_task_model_id(
        model_id,
        await Config.get('task.model.default'),
        await Config.get('task.model.external'),
        models,
    )
    if task_model_id not in models:
        task_model_id = model_id
    if task_model_id not in models:
        raise ValueError('No available model for context compaction')

    summary_prompt_template = summary_prompt_template.strip() or DEFAULT_CONTEXT_COMPACTION_PROMPT
    all_messages = [*compacted_messages, *recent_messages]
    prompt = replace_prompt_variable(summary_prompt_template, get_last_user_message(all_messages) or '')
    prompt = replace_messages_variable(prompt, all_messages)
    prompt = replace_messages_variable(prompt, compacted_messages, 'COMPACTED_MESSAGES')
    prompt = replace_messages_variable(prompt, recent_messages, 'RECENT_MESSAGES')
    prompt = prompt_variables_template(prompt, {'{{PREVIOUS_SUMMARY}}': previous_summary or ''})
    prompt = await prompt_template(prompt, user)

    max_tokens = models[task_model_id].get('info', {}).get('params', {}).get('max_tokens', 1000)
    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False,
        **(
            {'max_tokens': max_tokens}
            if models[task_model_id].get('owned_by') == 'ollama'
            else {'max_completion_tokens': max_tokens}
        ),
        'metadata': {
            **(request.state.metadata if hasattr(request.state, 'metadata') else {}),
            'task': 'context_compaction',
        },
    }

    response = await generate_chat_completion(request, form_data=payload, user=user)
    summary = _response_text(response).strip()
    if summary:
        return summary

    parts = [previous_summary] if previous_summary else []
    for message in compacted_messages:
        content = get_content_from_message(message)
        if content:
            parts.append(f'- {message.get("role", "unknown")}: {content[:500]}')
    return '\n'.join(parts)[:4000]


def _response_text(response: Any) -> str:
    if isinstance(response, list) and len(response) == 1:
        response = response[0]

    if isinstance(response, JSONResponse):
        try:
            response = json.loads(response.body.decode('utf-8', 'replace'))
        except Exception:
            return ''

    if not isinstance(response, dict):
        return ''

    choices = response.get('choices') or []
    if choices:
        message = choices[0].get('message') or {}
        return message.get('content') or message.get('reasoning_content') or ''

    parts = []
    for item in response.get('output') or []:
        for content in item.get('content') or []:
            if isinstance(content, dict):
                parts.append(content.get('text') or content.get('content') or '')
    return '\n'.join(part for part in parts if part)


def _estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for message in messages:
        total += 4
        content = message.get('content')
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    total += _estimate_tokens(item)
                elif item.get('type') in {'image', 'image_url'}:
                    total += 1000
                else:
                    total += _estimate_tokens(item.get('text') or item.get('content') or item)
        else:
            total += _estimate_tokens(content)

        total += _estimate_tokens(message.get('output'))
        total += _estimate_tokens(message.get('tool_calls'))
        total += _estimate_tokens(message.get('files'))
    return total


def _estimate_tokens(value: Any) -> int:
    if value is None:
        return 0

    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except Exception:
            value = str(value)

    if not value:
        return 0

    return max(1, len(value) // 4)

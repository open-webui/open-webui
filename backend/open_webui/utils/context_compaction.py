from __future__ import annotations

import logging
from typing import Any

from fastapi.responses import JSONResponse
from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.misc import (
    get_content_from_message,
    get_last_user_message,
    get_last_user_message_item,
    get_message_list,
)
from open_webui.utils.payload import apply_params_to_form_data
from open_webui.utils.task import (
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

    system_messages = [messages[0]] if messages and messages[0].get('role') == 'system' else []
    messages = messages[1:] if system_messages else messages

    messages, previous_summary = _apply_latest_summary_checkpoint(messages)
    token_threshold = _resolve_token_threshold(config['token_threshold'], config['token_cap'], metadata)
    if not _exceeds_token_threshold(messages, system_prompt, previous_summary, token_threshold) or len(messages) <= 3:
        return [*system_messages, *messages], previous_summary, False

    boundary = _find_compaction_boundary(messages, config['retention_percentage'])
    compacted_messages = messages[:boundary]
    recent_messages = messages[boundary:]
    if not compacted_messages or not recent_messages:
        return [*system_messages, *messages], previous_summary, False

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
    checkpoint_message_id = (
        recent_messages[0].get('id') or metadata.get('user_message_id') or metadata.get('message_id')
    )
    if is_saved_chat_id(chat_id) and checkpoint_message_id:
        await Chats.upsert_message_to_chat_by_id_and_message_id(
            chat_id,
            checkpoint_message_id,
            {'contextSummary': summary},
            touch=False,
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

    return [*system_messages, *recent_messages], summary, True


class ToolLoopCompactor:
    """Compacts the native tool call loop's own history when it crosses the token threshold."""

    def __init__(self, request, user, metadata: dict, messages: list[dict]) -> None:
        self._request = request
        self._user = user
        self._metadata = metadata
        self._summary: str | None = None
        self._config: dict | None = None
        self._stopped = False
        self._dropped_count = 0
        self._sent_count = len(messages) - (1 if messages and messages[0].get('role') == 'system' else 0)
        self._user_message = get_last_user_message_item(messages)
        self._preserved_user: list[dict] = []

    async def apply(self, messages: list[dict], usage: dict | None, model_id: str) -> list[dict]:
        if self._config is None:
            self._config = await _load_config()
        if not self._config['enable']:
            return messages

        system_messages = [messages[0]] if messages and messages[0].get('role') == 'system' else []
        system_prompt = (get_content_from_message(system_messages[0]) or '') if system_messages else ''
        history = messages[len(system_messages) :]

        # An outside insert can shift the cut, so walk it back onto a whole call/result block.
        while self._dropped_count < len(history) and history[self._dropped_count].get('role') == 'tool':
            self._dropped_count += 1
        history = history[self._dropped_count :]

        if not self._stopped and self._exceeds_threshold(history, system_prompt, usage):
            try:
                history = await self._summarize(history, model_id)
            except Exception:
                self._stopped = True
                log.exception('Tool loop context compaction failed; keeping the history trimmed so far')

        self._sent_count = len(history)
        summary_messages = (
            [{'role': 'system', 'content': f'[CONVERSATION SUMMARY]\n{self._summary}'}] if self._summary else []
        )
        return [*system_messages, *summary_messages, *self._preserved_user, *history]

    def _exceeds_threshold(self, history: list[dict], system_prompt: str, usage: dict | None) -> bool:
        if len(history) <= 3:
            return False

        threshold = _resolve_token_threshold(self._config['token_threshold'], self._config['token_cap'], self._metadata)

        reported_tokens = _usage_token_count(usage or {})
        if reported_tokens:
            # The assistant turn that follows what was sent is already inside completion_tokens.
            return reported_tokens + _estimate_messages_tokens(history[self._sent_count + 1 :]) > threshold

        estimated = (
            _estimate_tokens(system_prompt)
            + _estimate_tokens(self._summary or '')
            + _estimate_messages_tokens(self._preserved_user)
            + _estimate_messages_tokens(history)
        )
        return estimated > threshold

    async def _summarize(self, history: list[dict], model_id: str) -> list[dict]:
        boundary = _find_tool_loop_boundary(history, self._config['retention_percentage'])
        compacted_messages, recent_messages = history[:boundary], history[boundary:]
        drops_only_the_user_message = all(message is self._user_message for message in compacted_messages)
        if drops_only_the_user_message:
            return history

        await _emit_compaction_status(self._metadata, 'Compacting context', done=False)
        try:
            self._summary = await _generate_summary(
                self._request,
                self._user,
                model_id,
                _get_compaction_models(self._request),
                _describe_tool_calls(compacted_messages),
                _describe_tool_calls(recent_messages),
                self._summary,
                self._config['prompt_template'],
            )
        except Exception:
            await _emit_compaction_status(self._metadata, 'Context compaction failed', done=True, error=True)
            raise

        self._dropped_count += boundary
        keeps_user_message = any(message is self._user_message for message in recent_messages)
        if self._user_message and not self._preserved_user and not keeps_user_message:
            self._preserved_user = [self._user_message]

        log.info(
            'Compacted tool loop context for chat=%s response=%s dropped=%d kept=%d summary_chars=%d',
            self._metadata.get('chat_id'),
            self._metadata.get('message_id'),
            len(compacted_messages),
            len(recent_messages),
            len(self._summary or ''),
        )
        await _emit_compaction_status(self._metadata, 'Context compacted', done=True)
        return recent_messages


async def compact_chat_branch(request, user, chat: Any, model_id: str, models: dict) -> dict:
    config = await _load_config()
    if not config['enable']:
        return {'ok': True, 'compacted': False, 'reason': 'disabled'}

    chat_data = chat.chat or {}
    history = chat_data.get('history') or {}
    current_id = getattr(chat, 'current_message_id', None) or history.get('currentId')
    if not current_id:
        current_id = chat_data.get('currentId') or chat_data.get('branchPointMessageId')
    if not current_id and isinstance(chat_data.get('messages'), list) and chat_data['messages']:
        current_id = chat_data['messages'][-1].get('id')
    if not current_id:
        return {'ok': True, 'compacted': False, 'reason': 'empty'}

    messages_map = await Chats.get_messages_map_by_chat_id(chat.id)
    if not messages_map:
        messages_map = history.get('messages') or {}

    messages, previous_summary = _apply_latest_summary_checkpoint(get_message_list(messages_map, current_id))
    compacted_messages = messages[:-1]
    recent_messages = messages[-1:]
    if not compacted_messages or not recent_messages:
        return {'ok': True, 'compacted': False, 'reason': 'too_short'}

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
    await Chats.upsert_message_to_chat_by_id_and_message_id(
        chat.id, current_id, {'contextSummary': summary}, touch=False
    )

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
        'chat.context_compaction.token_cap',
        'chat.context_compaction.retention_percentage',
        'chat.context_compaction.prompt_template',
    )
    token_threshold = _parse_positive_int(values.get('chat.context_compaction.token_threshold')) or 80000
    return {
        'enable': bool(values.get('chat.context_compaction.enable', False)),
        'token_threshold': token_threshold,
        'token_cap': _parse_positive_int(values.get('chat.context_compaction.token_cap')) or token_threshold,
        'retention_percentage': _clamp_retention_percentage(values.get('chat.context_compaction.retention_percentage')),
        'prompt_template': values.get('chat.context_compaction.prompt_template', '') or '',
    }


def _parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _clamp_retention_percentage(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 40
    return min(50, max(10, parsed))


def _resolve_token_threshold(global_threshold: int, global_cap: int, metadata: dict) -> int:
    configured_threshold = _parse_positive_int((metadata.get('params') or {}).get('compact_token_threshold'))
    return min(configured_threshold or global_threshold, global_cap)


def _usage_token_count(usage: dict) -> int:
    prompt_tokens = int(usage.get('prompt_tokens') or usage.get('prompt_eval_count') or 0)
    if not prompt_tokens and (usage.get('prompt_n') is not None or usage.get('cache_n') is not None):
        prompt_tokens = int(usage.get('prompt_n') or 0) + int(usage.get('cache_n') or 0)
    if not prompt_tokens:
        prompt_tokens = int(usage.get('input_tokens') or 0)

    completion_tokens = int(
        usage.get('completion_tokens')
        or usage.get('output_tokens')
        or usage.get('eval_count')
        or usage.get('predicted_n')
        or 0
    )
    return prompt_tokens + completion_tokens


async def get_chat_context_usage(chat: Any, model_id: str | None = None) -> dict | None:
    chat_data = chat.chat or {}
    history = chat_data.get('history') or {}
    current_id = getattr(chat, 'current_message_id', None) or history.get('currentId')
    if not current_id:
        current_id = chat_data.get('currentId') or chat_data.get('branchPointMessageId')
    if not current_id and isinstance(chat_data.get('messages'), list) and chat_data['messages']:
        current_id = chat_data['messages'][-1].get('id')
    if not current_id:
        return None

    messages_map = await Chats.get_messages_map_by_chat_id(chat.id)
    messages = get_message_list(messages_map or history.get('messages') or {}, current_id)
    if not messages:
        return None

    config = await _load_config()
    if not config['enable']:
        return None

    params = ((chat.chat or {}).get('params') or {}).copy()
    if model_id:
        params['model'] = model_id
    threshold = _resolve_token_threshold(config['token_threshold'], config['token_cap'], {'params': params})
    messages, previous_summary = _apply_latest_summary_checkpoint(messages)

    for idx in range(len(messages) - 1, -1, -1):
        usage = messages[idx].get('usage') or (messages[idx].get('info') or {}).get('usage')
        if isinstance(usage, dict) and (tokens := _usage_token_count(usage)):
            tokens += _estimate_messages_tokens(messages[idx + 1 :])
            return _build_context_usage(tokens, threshold)

    tokens = _estimate_tokens(previous_summary or '') + _estimate_messages_tokens(messages)
    return _build_context_usage(tokens, threshold)


def _build_context_usage(tokens: int, threshold: int) -> dict:
    return {
        'tokens': tokens,
        'estimated_tokens': tokens,
        'threshold': threshold,
        'percent': round((tokens / threshold) * 100) if threshold > 0 else 0,
        'source': 'estimated',
    }


def _get_compaction_models(request) -> dict:
    """Return the model registry with any direct-connection model from request.state merged in."""
    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        return {**dict(request.app.state.MODELS.items()), request.state.model['id']: request.state.model}
    return request.app.state.MODELS


async def _emit_compaction_status(metadata: dict, description: str, done: bool, error: bool = False) -> None:
    if not (metadata.get('chat_id') and metadata.get('message_id')):
        return

    from open_webui.socket.main import get_event_emitter

    data = {'action': 'context_compaction', 'description': description, 'done': done}
    if error:
        data['error'] = True

    try:
        event_emitter = await get_event_emitter(metadata)
        if event_emitter:
            await event_emitter({'type': 'context_compaction', 'data': data})
    except Exception:
        log.debug('Could not emit context compaction status')


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
        if isinstance(usage, dict) and (tokens := _usage_token_count(usage)):
            return tokens + _estimate_messages_tokens(messages[idx + 1 :]) > threshold

    estimated = _estimate_tokens(system_prompt) + _estimate_tokens(summary or '') + _estimate_messages_tokens(messages)
    return estimated > threshold


def _find_compaction_boundary(messages: list[dict], retention_percentage: int = 40) -> int:
    retention_percentage = _clamp_retention_percentage(retention_percentage)
    keep_count = max(2, len(messages) * retention_percentage // 100)
    target = max(1, len(messages) - keep_count)
    boundaries = [idx for idx, message in enumerate(messages) if message.get('role') == 'user'][1:]
    return next((idx for idx in reversed(boundaries) if idx <= target), 0)


def _find_tool_loop_boundary(messages: list[dict], retention_percentage: int) -> int:
    keep_count = max(2, len(messages) * retention_percentage // 100)
    target = max(1, len(messages) - keep_count)
    # Cutting on a tool result orphans it from its call and the provider rejects the request.
    boundaries = [idx for idx, message in enumerate(messages) if idx and message.get('role') != 'tool']
    return next((idx for idx in reversed(boundaries) if idx <= target), 0)


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

    task_config = await Config.get_many(
        'task.model.params',
        'chat.context_compaction.model',
    )
    context_compaction_model = task_config.get('chat.context_compaction.model')
    task_model_id = context_compaction_model if context_compaction_model in models else model_id
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

    task_model_params = task_config.get('task.model.params') or {}
    if not isinstance(task_model_params, dict):
        task_model_params = {}
    task_model_params = {key: value for key, value in task_model_params.items() if value is not None and value != ''}
    task_model_params = task_model_params or {
        'max_tokens': models[task_model_id].get('info', {}).get('params', {}).get('max_tokens', 1000)
    }

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False,
        'metadata': {
            **(request.state.metadata if hasattr(request.state, 'metadata') else {}),
            'task': 'context_compaction',
        },
    }

    payload = apply_params_to_form_data(payload, models[task_model_id], task_model_params)
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


def _describe_tool_calls(messages: list[dict]) -> list[dict]:
    """Fold each tool call's name and arguments into its message content."""
    described = []
    for message in messages:
        tool_calls = message.get('tool_calls') or []
        if not tool_calls:
            described.append(message)
            continue

        calls = ', '.join(
            f'{(call.get("function") or {}).get("name", "")}({(call.get("function") or {}).get("arguments", "")})'
            for call in tool_calls
        )
        content = get_content_from_message(message) or ''
        described.append({**message, 'content': f'{content}\n[TOOL CALLS] {calls}'.strip()})
    return described


def _response_text(response: Any) -> str:
    if isinstance(response, list) and len(response) == 1:
        response = response[0]

    if isinstance(response, JSONResponse):
        try:
            response = JSONCodec.loads(response.body.decode('utf-8', 'replace'))
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
            value = JSONCodec.dumps(value, ensure_ascii=False)
        except Exception:
            value = str(value)

    if not value:
        return 0

    return max(1, len(value) // 4)

from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.constants import ERROR_MESSAGES
from open_webui.models.chats import Chats
from open_webui.socket.main import get_event_emitter
from open_webui.utils.json_codec import JSONCodec


class ResolveToolCallForm(BaseModel):
    call_id: str
    action: Literal['approve', 'reject', 'answer']
    answers: Any | None = None
    timed_out: bool = False


APPROVAL_PENDING_STATUSES = frozenset({'pending', 'queued', 'requires_approval'})
APPROVAL_TERMINAL_STATUSES = frozenset({'rejected', 'failed', 'incomplete'})


def get_tool_call_id(item: dict) -> str | None:
    return item.get('call_id') or item.get('id') or None


def get_resolved_call_ids(output: list[dict]) -> set:
    """Return call IDs that already have a function-call result."""
    return {
        item.get('call_id') for item in output if item.get('type') == 'function_call_output' and item.get('call_id')
    }


def is_paused_for_tool_approval(output: list[dict]) -> bool:
    """Return whether any unresolved call is waiting for approval or execution."""
    resolved_call_ids = get_resolved_call_ids(output)
    return any(
        item.get('type') == 'function_call'
        and item.get('call_id')
        and item.get('status') in APPROVAL_PENDING_STATUSES
        and item.get('call_id') not in resolved_call_ids
        for item in output
    )


def has_unapproved_tool_call(output: list[dict]) -> bool:
    """Return whether a non-ask_user call still needs user approval."""
    resolved_call_ids = get_resolved_call_ids(output)
    return any(
        item.get('type') == 'function_call'
        and item.get('name') != 'ask_user'
        and get_tool_call_id(item)
        and item.get('status') not in APPROVAL_TERMINAL_STATUSES
        and item.get('approved') is not True
        and get_tool_call_id(item) not in resolved_call_ids
        for item in output
    )


def assign_tool_approval_statuses(output: list[dict]) -> None:
    """Arm every unresolved call in a batch using its own call ID.

    Streaming finalization marks calls `completed` once their arguments are
    complete, before approval and execution. A call is only resolved when it
    has a matching `function_call_output`, so unresolved `completed` calls must
    be re-armed as well. Exactly one call remains `pending`; the rest queue.
    """
    resolved_call_ids = get_resolved_call_ids(output)
    candidates = []
    has_pending_approval = False

    for item in output:
        if item.get('type') != 'function_call':
            continue
        if not item.get('call_id') and item.get('id'):
            item['call_id'] = item['id']

        call_id = item.get('call_id')
        if not call_id or call_id in resolved_call_ids:
            continue

        status_value = item.get('status')
        if status_value in APPROVAL_TERMINAL_STATUSES:
            continue
        if status_value in {'pending', 'requires_approval'}:
            has_pending_approval = True
            continue
        if status_value == 'queued' and item.get('approved') is True:
            continue

        candidates.append(item)

    for item in candidates:
        if has_pending_approval:
            item['status'] = 'queued'
        else:
            item['status'] = 'pending'
            has_pending_approval = True


async def resolve_tool_call_output(
    chat_id: str,
    message_id: str,
    form_data: ResolveToolCallForm,
    user,
    db: AsyncSession | None = None,
) -> dict:
    chat = await Chats.get_chat_by_id(chat_id, db=db)
    if not chat or (chat.user_id != user.id and user.role != 'admin'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    message = await Chats.get_message_by_id_and_message_id(chat_id, message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    output = message.get('output') or []
    if not isinstance(output, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Message has no resolvable output.')

    function_call = next(
        (
            item
            for item in output
            if item.get('type') == 'function_call' and (item.get('call_id') or item.get('id')) == form_data.call_id
        ),
        None,
    )
    if not function_call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Tool call not found.')
    function_call.setdefault('call_id', form_data.call_id)
    tool_name = function_call.get('name')

    if (
        form_data.call_id in get_resolved_call_ids(output)
        or function_call.get('status') not in APPROVAL_PENDING_STATUSES
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Tool call has already been resolved.')

    if form_data.action == 'approve':
        if tool_name == 'ask_user':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='ask_user requires an answer or deny.')
        function_call['status'] = 'queued'
        function_call['approved'] = True
    elif form_data.action == 'reject':
        function_call['status'] = 'rejected'
        output.append(
            {
                'type': 'function_call_output',
                'id': f'fco_{form_data.call_id}',
                'call_id': form_data.call_id,
                'output': [{'type': 'input_text', 'text': 'Error: tool call rejected by user.'}],
                'status': 'rejected',
            }
        )
    else:
        if tool_name != 'ask_user':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Tool call does not accept answers.')
        if form_data.answers is None and not form_data.timed_out:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Answers are required for ask_user.')
        function_call['status'] = 'completed'
        answer_payload = (
            {'status': 'cancelled', 'answers': {}, 'timed_out': True}
            if form_data.timed_out
            else {'status': 'answered', 'answers': form_data.answers or {}}
        )
        output.append(
            {
                'type': 'function_call_output',
                'id': f'fco_{form_data.call_id}',
                'call_id': form_data.call_id,
                'output': [{'type': 'input_text', 'text': JSONCodec.dumps(answer_payload)}],
                'status': 'completed',
            }
        )

    await Chats.upsert_message_to_chat_by_id_and_message_id(
        chat_id,
        message_id,
        {
            'done': False,
            'output': output,
        },
        touch=False,
    )

    event_emitter = await get_event_emitter(
        {
            'user_id': chat.user_id,
            'chat_id': chat_id,
            'message_id': message_id,
        },
        update_db=False,
    )
    if event_emitter:
        await event_emitter({'type': 'chat:completion', 'data': {'output': output}})

    return {
        'chat': chat,
        'message': message,
        'output': output,
        'paused': is_paused_for_tool_approval(output),
    }


async def build_tool_approval_resume_payload(chat_id: str, message_id: str, chat=None) -> dict:
    chat = chat or await Chats.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    assistant_message = await Chats.get_message_by_id_and_message_id(chat_id, message_id)
    if not assistant_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    user_message_id = assistant_message.get('parentId')
    user_message = await Chats.get_message_by_id_and_message_id(chat_id, user_message_id) if user_message_id else None
    if not user_message:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Tool call parent message is missing.')

    chat_data = chat.chat or {}
    message_meta = assistant_message.get('meta') if isinstance(assistant_message.get('meta'), dict) else {}
    chat_params = chat_data.get('params') if isinstance(chat_data.get('params'), dict) else {}
    params = {
        **chat_params,
        **(message_meta.get('params') if isinstance(message_meta.get('params'), dict) else {}),
    }
    current_approval_mode = chat_params.get('tool_approval_mode')
    if current_approval_mode in {'ask', 'full'}:
        params['tool_approval_mode'] = current_approval_mode
    if 'tool_approval_mode' not in params:
        params['tool_approval_mode'] = 'ask'

    model_id = assistant_message.get('model') or next(iter(chat_data.get('models') or []), None)
    if not model_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Tool call message model is missing.')

    messages = []
    if params.get('system'):
        messages.append({'role': 'system', 'content': params.get('system')})

    return {
        'stream': params.get('stream_response', True),
        'model': model_id,
        'messages': messages,
        'params': params,
        'files': message_meta.get('files') or chat_data.get('files') or None,
        'filter_ids': message_meta.get('filter_ids') or None,
        'tool_ids': message_meta.get('tool_ids') or None,
        'skill_ids': message_meta.get('skill_ids') or None,
        'terminal_id': message_meta.get('terminal_id') or None,
        'tool_servers': message_meta.get('tool_servers') or None,
        'features': message_meta.get('features') or {},
        'variables': message_meta.get('variables') or {},
        'chat_variables': chat.variables,
        'session_id': message_meta.get('session_id'),
        'chat_id': chat_id,
        'id': message_id,
        'parent_id': user_message.get('parentId'),
        'user_message': user_message,
        'assistant_message_id': message_id,
    }

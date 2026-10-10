from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.constants import ERROR_MESSAGES
from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.socket.main import get_event_emitter
from open_webui.utils.json_codec import JSONCodec


class ResolveToolCallForm(BaseModel):
    call_id: str
    action: Literal['approve', 'reject', 'answer']
    answers: Any | None = None
    timed_out: bool = False


def pending_tool_calls(output):
    result_ids = {item.get('call_id') for item in output if item.get('type') == 'function_call_output'}
    return [
        item
        for item in output
        if item.get('type') == 'function_call'
        and (item.get('call_id') or item.get('id')) not in result_ids
        and item.get('status') in {'pending', 'queued', 'requires_approval', 'in_progress'}
    ]


def tool_continuation():
    return {
        'type': 'message',
        'id': f'msg_{uuid4().hex}',
        'status': 'in_progress',
        'role': 'assistant',
        'content': [{'type': 'output_text', 'text': ''}],
    }


async def complete_tool_call(chat_id, message_id, call, result):
    async with Chats.edit_message_output(chat_id, message_id) as message:
        if not message:
            raise HTTPException(status_code=404, detail=ERROR_MESSAGES.NOT_FOUND)
        output = message.get('output') or []
        saved = next((item for item in pending_tool_calls(output) if item.get('call_id') == call['call_id']), None)
        if saved is None or saved.get('status') != 'in_progress':
            raise HTTPException(status_code=409, detail='Tool call is no longer running.')
        saved.update(call)
        output.append(result)
        pending = pending_tool_calls(output)
        if result.get('status') == 'incomplete':
            message['done'] = True
        elif not pending:
            # Only the transaction completing the last call may start the model again.
            output.append(tool_continuation())
        else:
            next_approval = next((item for item in pending if not item.get('approved')), None)
            if next_approval is not None:
                next_approval['status'] = 'pending'
        return output


async def resolve_tool_call_output(
    chat_id: str,
    message_id: str,
    form_data: ResolveToolCallForm,
    user,
    db: AsyncSession | None = None,
) -> dict:
    chat = await Chats.get_accessible_chat_by_id(chat_id, user, db=db, permission='write')
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    async with Chats.edit_message_output(chat_id, message_id) as message:
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

        if (message.get('user_id') or chat.user_id) != user.id:
            raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

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
            any(
                item.get('type') == 'function_call_output' and item.get('call_id') == form_data.call_id
                for item in output
            )
            or function_call.get('status') not in {'pending', 'queued', 'requires_approval'}
            or function_call.get('approved') is True
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Tool call has already been resolved.')

        active = any(
            item.get('approved') is True or item.get('status') == 'in_progress' for item in pending_tool_calls(output)
        )

        if form_data.action == 'approve':
            if tool_name == 'ask_user':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail='ask_user requires an answer or deny.'
                )
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail='Tool call does not accept answers.'
                )
            if form_data.answers is None and not form_data.timed_out:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail='Answers are required for ask_user.'
                )
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

        message['done'] = False
        pending = pending_tool_calls(output)
        resume = None
        if not active:
            if form_data.action == 'approve':
                resume = 'tools'
            elif not pending:
                output.append(tool_continuation())
                resume = 'model'
            else:
                pending[0]['status'] = 'pending'

    event_emitter = await get_event_emitter(
        {
            'user_id': user.id,
            'chat_id': chat_id,
            'message_id': message_id,
        },
        update_db=False,
    )
    if event_emitter:
        await event_emitter({'type': 'chat:completion', 'data': {'output': output}})

    return {'chat': chat, 'output': output, 'resume': resume}


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
    if (assistant_message.get('user_id') or chat.user_id) != chat.user_id:
        chat_params = {}
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
    system_prompt = params.get('system')
    if not system_prompt:
        # Mirror the chat UI's system prompt fallback
        user = await Users.get_user_by_id(assistant_message.get('user_id') or chat.user_id)
        ui_settings = (user.settings.ui if user and user.settings else None) or {}
        system_prompt = ui_settings.get('system')
        if system_prompt is None:
            default_interface_settings = await Config.get('ui.default_interface_settings') or {}
            system_prompt = default_interface_settings.get('system')
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})

    return {
        'stream': params.get('stream_response', True),
        'model': model_id,
        'messages': messages,
        'params': params,
        'files': message_meta.get('files') if 'files' in message_meta else chat_data.get('files'),
        'filter_ids': message_meta.get('filter_ids') or None,
        'tool_ids': message_meta.get('tool_ids') or None,
        'skill_ids': message_meta.get('skill_ids') or None,
        'terminal_id': message_meta.get('terminal_id') or None,
        'tool_servers': message_meta.get('tool_servers') or None,
        'features': message_meta.get('features') or {},
        'variables': message_meta.get('variables') or {},
        'chat_variables': chat.variables
        if (assistant_message.get('user_id') or chat.user_id) == chat.user_id
        else {},
        'session_id': message_meta.get('session_id'),
        'chat_id': chat_id,
        'id': message_id,
        'parent_id': user_message.get('parentId'),
        'user_message': user_message,
        'assistant_message_id': message_id,
    }

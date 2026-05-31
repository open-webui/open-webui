from types import SimpleNamespace

import pytest
from open_webui.utils.middleware import background_tasks_handler


@pytest.mark.asyncio
@pytest.mark.parametrize('chat_id', [None, 123])
async def test_background_tasks_handler_allows_direct_api_context_without_string_chat_id(chat_id):
    ctx = {
        'request': SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace())),
        'form_data': {'messages': [{'role': 'user', 'content': 'hello'}]},
        'user': SimpleNamespace(id='user-1'),
        'metadata': {
            'user_id': 'user-1',
            'chat_id': chat_id,
            'message_id': 'message-1',
        },
        'tasks': {},
        'event_emitter': None,
    }

    await background_tasks_handler(ctx)

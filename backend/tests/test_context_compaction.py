import os
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault('WEBUI_SECRET_KEY', 'context-compaction-tests-only-secret-key')
os.environ.setdefault('STATIC_DIR', os.path.join(tempfile.gettempdir(), 'open-webui-test-static'))

import pytest

import open_webui.utils.context_compaction as context_compaction


@pytest.mark.asyncio
async def test_compaction_preserves_original_system_messages(monkeypatch):
    generate_summary = AsyncMock(return_value='summary')
    monkeypatch.setattr(
        context_compaction,
        '_load_config',
        AsyncMock(
            return_value={
                'enable': True,
                'token_threshold': 1,
                'token_cap': 1,
                'prompt_template': '',
            }
        ),
    )
    monkeypatch.setattr(context_compaction, '_generate_summary', generate_summary)

    messages = [
        {'role': 'system', 'content': 'Never lose this persona.'},
        {'id': 'u1', 'role': 'user', 'content': 'one'},
        {'id': 'a1', 'role': 'assistant', 'content': 'two'},
        {'id': 'u2', 'role': 'user', 'content': 'three'},
        {'id': 'a2', 'role': 'assistant', 'content': 'four'},
    ]

    compacted, summary, changed = await context_compaction.compact_messages_for_request(
        request=object(),
        user=object(),
        messages=messages,
        metadata={'params': {}},
        model_id='model',
        models={'model': {}},
        system_prompt='Never lose this persona.',
    )

    assert changed is True
    assert summary == 'summary'
    assert compacted[0] == messages[0]
    assert [message['id'] for message in compacted[1:]] == ['u2', 'a2']
    summary_args = generate_summary.await_args.args
    assert all(message.get('role') != 'system' for message in summary_args[4])


@pytest.mark.asyncio
async def test_window_context_usage_does_not_reload_full_branch(monkeypatch):
    monkeypatch.setattr(
        context_compaction,
        '_load_config',
        AsyncMock(
            return_value={
                'enable': True,
                'token_threshold': 1000,
                'token_cap': 1000,
                'prompt_template': '',
            }
        ),
    )
    branch_loader = AsyncMock(side_effect=AssertionError('full branch should not load'))
    monkeypatch.setattr(
        context_compaction.ChatMessages,
        'get_message_branch_by_chat_id',
        branch_loader,
    )
    chat = SimpleNamespace(
        id='chat',
        chat={
            'history': {
                'currentId': 'assistant',
                'messageWindow': {'hasMore': True},
                'messages': {
                    'root': {
                        'id': 'root',
                        'parentId': None,
                        'childrenIds': ['assistant'],
                        'role': 'user',
                        '__loaded': False,
                    },
                    'assistant': {
                        'id': 'assistant',
                        'parentId': 'root',
                        'childrenIds': [],
                        'role': 'assistant',
                        '__loaded': True,
                        'lastRequestUsage': {'input_tokens': 120, 'output_tokens': 30},
                    },
                },
            }
        },
    )

    usage = await context_compaction.get_chat_context_usage(chat)

    assert usage['tokens'] == 150
    branch_loader.assert_not_awaited()

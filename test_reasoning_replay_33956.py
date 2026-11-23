"""Regression tests for open-webui/open-webui#33956.

Responses API connections never sent the model's reasoning back, although the
docs say they do: reasoning items saved with a reply were dropped when the
history was rebuilt for a follow-up request, so neither the in-turn tool
follow-up nor later messages carried them.

Run against a checkout of the repo (or an installed open-webui with the
patched files overlaid) with:

    WEBUI_SECRET_KEY=<long random value> \
    FRONTEND_BUILD_DIR=<repo or site-packages>/open_webui \
    python -m pytest test_reasoning_replay_33956.py -v

The imports pull in the backend app modules (config runs migrations on
import), so a plain ``python -m pytest`` without those variables fails at
collection time, not in the tests.
"""

import copy

import pytest

from open_webui.routers.openai import (
    RESPONSES_ALLOWED_FIELDS,
    convert_to_responses_payload,
)
from open_webui.utils.middleware import strip_reasoning_details
from open_webui.utils.misc import convert_output_to_messages

REASONING_ITEM = {
    'type': 'reasoning',
    'id': 'rs_abc123',
    'summary': [{'type': 'summary_text', 'text': 'Thinking about tools.'}],
    'encrypted_content': 'enc_abc',
    'status': 'completed',
}

AZURE_REASONING_ITEM = {
    'type': 'reasoning',
    'id': 'rs_azure1',
    'summary': [{'type': 'summary_text', 'text': 'Azure reasoning.'}],
    'encrypted_reasoning': 'enc_azure',
    'status': 'completed',
}

TOOL_TURN_OUTPUT = [
    REASONING_ITEM,
    {
        'type': 'message',
        'id': 'msg_1',
        'content': [{'type': 'output_text', 'text': 'I will calculate that.'}],
        'status': 'completed',
    },
    {
        'type': 'function_call',
        'id': 'fc_1',
        'call_id': 'call_1',
        'name': 'calculator',
        'arguments': '{"x": 2, "y": 2}',
        'status': 'completed',
    },
    {
        'type': 'function_call_output',
        'id': 'fco_1',
        'call_id': 'call_1',
        'output': [{'type': 'input_text', 'text': '4'}],
        'status': 'completed',
    },
]


def _assistant_with_reasoning(**extra):
    message = {
        'role': 'assistant',
        'content': 'I will calculate that.',
        'tool_calls': [
            {
                'id': 'call_1',
                'type': 'function',
                'function': {'name': 'calculator', 'arguments': '{"x": 2, "y": 2}'},
            }
        ],
        'reasoning_items': [copy.deepcopy(REASONING_ITEM)],
    }
    message.update(extra)
    return message


# ---------------------------------------------------------------------------
# misc.convert_output_to_messages: preserve reasoning when raw=True
# ---------------------------------------------------------------------------


def test_reasoning_preserved_as_reasoning_items_when_raw():
    """The reported bug: with reasoning_format=None (the OpenAI default) the
    reasoning item was dropped. With raw=True it must survive on the message."""
    messages = convert_output_to_messages(copy.deepcopy(TOOL_TURN_OUTPUT), raw=True, reasoning_format=None)
    assistant = next(m for m in messages if m.get('role') == 'assistant')
    assert assistant.get('reasoning_items') == [REASONING_ITEM]
    assert assistant.get('tool_calls'), 'tool calls must survive alongside the reasoning'


def test_reasoning_dropped_when_not_raw():
    """Existing behaviour for non-raw callers (strict providers) is unchanged."""
    messages = convert_output_to_messages(copy.deepcopy(TOOL_TURN_OUTPUT), raw=False, reasoning_format=None)
    assert all('reasoning_items' not in m for m in messages)


def test_reasoning_format_thinking_still_works():
    """Ollama-style replay keeps working: reasoning text lands in `thinking`."""
    messages = convert_output_to_messages(copy.deepcopy(TOOL_TURN_OUTPUT), raw=True, reasoning_format='thinking')
    assistant = next(m for m in messages if m.get('role') == 'assistant')
    assert 'Thinking about tools.' in assistant.get('thinking', '')
    assert assistant.get('reasoning_items') == [REASONING_ITEM]


def test_reasoning_details_still_attached_when_present():
    """A reasoning item carrying reasoning_details keeps that behaviour."""
    output = copy.deepcopy(TOOL_TURN_OUTPUT)
    output[0]['reasoning_details'] = [{'format': 'openai', 'text': 'detail'}]
    messages = convert_output_to_messages(output, raw=True, reasoning_format=None)
    assistant = next(m for m in messages if m.get('role') == 'assistant')
    assert assistant.get('reasoning_details') == [{'format': 'openai', 'text': 'detail'}]


# ---------------------------------------------------------------------------
# routers.openai.convert_to_responses_payload: replay reasoning into input
# ---------------------------------------------------------------------------


def test_reasoning_replayed_before_function_call():
    payload = {
        'model': 'gpt-5',
        'messages': [
            {'role': 'user', 'content': 'What is 2+2? Use the calculator.'},
            _assistant_with_reasoning(),
            {'role': 'tool', 'tool_call_id': 'call_1', 'content': '4'},
            {'role': 'user', 'content': 'Thanks!'},
        ],
    }
    result = convert_to_responses_payload(copy.deepcopy(payload))
    items = result['input']
    kinds = [item.get('type') for item in items]
    assert kinds.index('reasoning') < kinds.index('function_call')
    reasoning = next(item for item in items if item.get('type') == 'reasoning')
    assert reasoning['id'] == 'rs_abc123'
    assert reasoning['encrypted_content'] == 'enc_abc'
    assert 'status' not in reasoning, 'output-only metadata must not be replayed'


def test_reasoning_replayed_before_text_message():
    payload = {
        'model': 'gpt-5',
        'messages': [
            {'role': 'user', 'content': 'Hi'},
            {
                'role': 'assistant',
                'content': 'Hello there.',
                'reasoning_items': [copy.deepcopy(REASONING_ITEM)],
            },
        ],
    }
    result = convert_to_responses_payload(copy.deepcopy(payload))
    items = result['input']
    assert items[1].get('type') == 'reasoning'
    assert items[2].get('type') == 'message'


def test_reasoning_only_turn_emits_no_empty_message():
    """A turn that only carried reasoning must not send an empty message."""
    payload = {
        'model': 'gpt-5',
        'messages': [
            {'role': 'user', 'content': 'Hi'},
            {'role': 'assistant', 'content': '', 'reasoning_items': [copy.deepcopy(REASONING_ITEM)]},
        ],
    }
    result = convert_to_responses_payload(copy.deepcopy(payload))
    items = result['input']
    assert [item.get('type') for item in items] == ['message', 'reasoning']


def test_azure_encrypted_reasoning_field_kept():
    """Azure OpenAI's preview field must survive normalisation (and status must not)."""
    assert 'encrypted_reasoning' in RESPONSES_ALLOWED_FIELDS['reasoning']
    payload = {
        'model': 'gpt-5',
        'messages': [
            {'role': 'user', 'content': 'Hi'},
            {'role': 'assistant', 'output': [copy.deepcopy(AZURE_REASONING_ITEM)]},
        ],
    }
    result = convert_to_responses_payload(copy.deepcopy(payload))
    reasoning = next(item for item in result['input'] if item.get('type') == 'reasoning')
    assert reasoning['encrypted_reasoning'] == 'enc_azure'
    assert 'status' not in reasoning


def test_stored_output_reasoning_replayed():
    """Messages that still carry raw `output` replay their reasoning items."""
    payload = {
        'model': 'gpt-5',
        'messages': [
            {'role': 'user', 'content': 'Hi'},
            {'role': 'assistant', 'output': copy.deepcopy(TOOL_TURN_OUTPUT)},
        ],
    }
    result = convert_to_responses_payload(copy.deepcopy(payload))
    items = result['input']
    kinds = [item.get('type') for item in items]
    assert kinds.index('reasoning') < kinds.index('function_call')


def test_strip_reasoning_items_for_chat_completions():
    """Responses-only replay data must not leak into Chat Completions payloads."""
    # Imported here (not at module level) so the suite still collects
    # against unpatched code, where this helper does not exist yet.
    from open_webui.routers.openai import _strip_reasoning_items

    messages = [
        _assistant_with_reasoning(),
        {'role': 'user', 'content': 'Hi'},
    ]
    _strip_reasoning_items(messages)
    assert all('reasoning_items' not in m for m in messages)
    assert messages[0]['tool_calls'], 'other keys are untouched'


# ---------------------------------------------------------------------------
# utils.middleware.strip_reasoning_details: model switch drops reasoning
# ---------------------------------------------------------------------------


def test_strip_reasoning_details_drops_reasoning_items():
    """Encrypted reasoning is bound to the model that produced it; switching
    models must drop it (and the reasoning_details key) instead of replaying
    it to a different model, which the provider rejects."""
    output = [
        copy.deepcopy(REASONING_ITEM),
        {'type': 'message', 'content': [{'type': 'output_text', 'text': 'hi'}]},
        {'type': 'message', 'content': [], 'reasoning_details': [{'format': 'openai'}]},
    ]
    stripped = strip_reasoning_details(copy.deepcopy(output))
    assert all(item.get('type') != 'reasoning' for item in stripped if isinstance(item, dict))
    assert all('reasoning_details' not in item for item in stripped if isinstance(item, dict))
    assert len(stripped) == 2


# ---------------------------------------------------------------------------
# End to end: stored output -> messages -> Responses payload
# ---------------------------------------------------------------------------


def test_end_to_end_follow_up_keeps_reasoning():
    """The issue's exact scenario: a later user message's follow-up request
    must carry the reasoning from the earlier tool-call turn."""
    messages = convert_output_to_messages(copy.deepcopy(TOOL_TURN_OUTPUT), raw=True, reasoning_format=None)
    payload = {
        'model': 'gpt-5',
        'messages': [
            {'role': 'user', 'content': 'What is 2+2? Use the calculator.'},
            *messages,
            {'role': 'user', 'content': 'Thanks!'},
        ],
    }
    result = convert_to_responses_payload(copy.deepcopy(payload))
    items = result['input']
    kinds = [item.get('type') for item in items]
    assert kinds.index('reasoning') < kinds.index('function_call')
    assert kinds[-1] == 'message'  # the follow-up user message is last
    reasoning = next(item for item in items if item.get('type') == 'reasoning')
    assert reasoning['id'] == 'rs_abc123'

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture()
def payload(monkeypatch):
    root = Path(__file__).resolve().parents[1]

    open_webui = types.ModuleType('open_webui')
    open_webui_utils = types.ModuleType('open_webui.utils')

    misc = types.ModuleType('open_webui.utils.misc')
    misc.add_or_update_system_message = lambda system, messages: messages
    misc.replace_system_message_content = lambda system, messages: messages

    def deep_update(target, update):
        for key, value in update.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                deep_update(target[key], value)
            else:
                target[key] = value
        return target

    misc.deep_update = deep_update

    task = types.ModuleType('open_webui.utils.task')

    async def prompt_template(system, user=None):
        return system

    task.prompt_template = prompt_template
    task.prompt_variables_template = lambda system, variables: system

    monkeypatch.setitem(sys.modules, 'open_webui', open_webui)
    monkeypatch.setitem(sys.modules, 'open_webui.utils', open_webui_utils)
    monkeypatch.setitem(sys.modules, 'open_webui.utils.misc', misc)
    monkeypatch.setitem(sys.modules, 'open_webui.utils.task', task)

    spec = importlib.util.spec_from_file_location(
        'payload_under_test',
        root / 'backend/open_webui/utils/payload.py',
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openai_default_model_params_fill_outbound_payload(payload):
    form_data = {
        'model': 'gpt-test',
        'messages': [{'role': 'user', 'content': 'hello'}],
    }

    result = payload.apply_model_params_to_body_openai(
        {'max_tokens': '256', 'temperature': '0.7'},
        form_data,
        overwrite=False,
    )

    assert result['max_tokens'] == 256
    assert result['temperature'] == 0.7


def test_openai_explicit_payload_params_override_defaults(payload):
    form_data = {
        'model': 'gpt-test',
        'messages': [{'role': 'user', 'content': 'hello'}],
        'max_tokens': 64,
        'temperature': 0.2,
    }

    result = payload.apply_model_params_to_body_openai(
        {'max_tokens': 256, 'temperature': 0.7},
        form_data,
        overwrite=False,
    )

    assert result['max_tokens'] == 64
    assert result['temperature'] == 0.2


def test_openai_explicit_max_tokens_overrides_default_max_completion_tokens(payload):
    form_data = {
        'model': 'gpt-test',
        'messages': [{'role': 'user', 'content': 'hello'}],
        'max_tokens': 64,
    }

    result = payload.apply_model_params_to_body_openai(
        {'max_completion_tokens': 256},
        form_data,
        overwrite=False,
    )

    assert result['max_tokens'] == 64
    assert 'max_completion_tokens' not in result


def test_openai_explicit_max_completion_tokens_overrides_default_max_tokens(payload):
    form_data = {
        'model': 'gpt-test',
        'messages': [{'role': 'user', 'content': 'hello'}],
        'max_completion_tokens': 64,
    }

    result = payload.apply_model_params_to_body_openai(
        {'max_tokens': 256},
        form_data,
        overwrite=False,
    )

    assert result['max_completion_tokens'] == 64
    assert 'max_tokens' not in result


def test_model_params_can_override_pre_applied_defaults(payload):
    form_data = {'model': 'gpt-test', 'messages': []}

    result = payload.apply_model_params_to_body_openai(
        {'max_tokens': 256, 'temperature': 0.7},
        form_data,
        overwrite=False,
    )
    result = payload.apply_model_params_to_body_openai(
        {'max_tokens': 128, 'temperature': 0.4},
        result,
    )

    assert result['max_tokens'] == 128
    assert result['temperature'] == 0.4


def test_ollama_default_model_params_fill_options_without_overriding_explicit_options(payload):
    form_data = {
        'model': 'llama-test',
        'messages': [{'role': 'user', 'content': 'hello'}],
        'options': {'temperature': 0.2},
    }

    result = payload.apply_model_params_to_body_ollama(
        {'max_tokens': '256', 'temperature': '0.7'},
        form_data,
        overwrite=False,
    )

    assert result['options']['num_predict'] == 256
    assert result['options']['temperature'] == 0.2

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))

from open_webui.routers.openai import convert_to_responses_payload


def _convert_tool(function: dict) -> dict:
    payload = convert_to_responses_payload(
        {
            'messages': [],
            'tools': [{'type': 'function', 'function': function}],
        }
    )
    return payload['tools'][0]


def test_convert_to_responses_payload_preserves_explicit_strict_values():
    assert _convert_tool({'name': 'strict', 'parameters': {}, 'strict': True})['strict'] is True
    assert _convert_tool({'name': 'loose', 'parameters': {}, 'strict': False})['strict'] is False


def test_convert_to_responses_payload_defaults_schema_tools_to_loose():
    assert _convert_tool({'name': 'default', 'parameters': {}})['strict'] is False


def test_convert_to_responses_payload_omits_strict_for_tools_without_parameters():
    assert 'strict' not in _convert_tool({'name': 'no-schema'})

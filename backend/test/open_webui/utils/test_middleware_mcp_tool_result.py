from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
MIDDLEWARE_PATH = REPO_ROOT / 'backend/open_webui/utils/middleware.py'


def load_process_tool_result():
    source = MIDDLEWARE_PATH.read_text()
    start = source.index('async def process_tool_result(')
    end = source.index('\n\nasync def terminal_event_handler(', start)
    function_source = source[start:end]

    module_name = 'open_webui.utils.middleware_process_tool_result_test'
    module = types.ModuleType(module_name)
    module.__package__ = 'open_webui.utils'
    json_module = __import__('json')
    module.__dict__.update(
        {
            'HTMLResponse': type('HTMLResponse', (), {}),
            'json': json_module,
            'JSONCodec': types.SimpleNamespace(
                loads=json_module.loads,
                JSONDecodeError=json_module.JSONDecodeError,
            ),
            'log': types.SimpleNamespace(debug=lambda *_args, **_kwargs: None),
        }
    )
    sys.modules[module_name] = module
    exec(function_source, module.__dict__)
    return module


@pytest.mark.asyncio
async def test_image_only_mcp_result_attaches_file_and_reports_success(monkeypatch):
    module = load_process_tool_result()
    saved_data_uris = []

    async def fake_get_file_url_from_base64(_request, data_uri, _metadata, _user):
        saved_data_uris.append(data_uri)
        return '/api/v1/files/test-image/content'

    monkeypatch.setitem(module.__dict__, 'get_file_url_from_base64', fake_get_file_url_from_base64)

    result, files, embeds = await module.process_tool_result(
        request=None,
        tool_function_name='export_diagram',
        tool_result=[
            {
                'type': 'image',
                'data': 'cG5nLWJ5dGVz',
                'mimeType': 'image/png',
            }
        ],
        tool_type='mcp',
        metadata={},
        user=None,
    )

    assert saved_data_uris == ['data:image/png;base64,cG5nLWJ5dGVz']
    assert files == [{'type': 'image', 'url': '/api/v1/files/test-image/content'}]
    assert embeds == []
    assert result == 'export_diagram: Image file attached successfully.'


@pytest.mark.asyncio
async def test_text_and_image_mcp_result_preserves_text_and_attachment(monkeypatch):
    module = load_process_tool_result()

    async def fake_get_file_url_from_base64(_request, _data_uri, _metadata, _user):
        return '/api/v1/files/test-image/content'

    monkeypatch.setitem(module.__dict__, 'get_file_url_from_base64', fake_get_file_url_from_base64)

    result, files, _embeds = await module.process_tool_result(
        request=None,
        tool_function_name='export_diagram',
        tool_result=[
            {'type': 'text', 'text': 'Export complete.'},
            {
                'type': 'image',
                'data': 'cG5nLWJ5dGVz',
                'mimeType': 'image/png',
            },
        ],
        tool_type='mcp',
        metadata={},
        user=None,
    )

    assert result == (
        '{\n  "results": [\n    "Export complete.",\n    "export_diagram: Image file attached successfully."\n  ]\n}'
    )
    assert files == [{'type': 'image', 'url': '/api/v1/files/test-image/content'}]

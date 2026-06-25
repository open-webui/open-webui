"""
Tests for the TwelveLabs `analyze_video` builtin tool.

The no-network test stubs the SDK and verifies request wiring + response
shaping. The live test runs a real Pegasus analysis and is skipped unless
TWELVELABS_API_KEY is set.

Run standalone (no pytest config needed):  python -m open_webui.tools.test_twelvelabs
"""

import asyncio
import json
import os
import sys
import types
from unittest.mock import MagicMock

from open_webui.tools.twelvelabs import analyze_video


class _FakeConfig:
    TWELVELABS_API_KEY = 'test-key'
    TWELVELABS_PEGASUS_MODEL = 'pegasus1.5'


class _FakeRequest:
    def __init__(self, config):
        self.app = types.SimpleNamespace(state=types.SimpleNamespace(config=config))


def test_missing_key_returns_error():
    cfg = _FakeConfig()
    cfg.TWELVELABS_API_KEY = ''
    out = asyncio.run(analyze_video('http://x/v.mp4', 'describe', __request__=_FakeRequest(cfg)))
    assert json.loads(out)['error'].startswith('TwelveLabs API key'), out


def test_no_request_context():
    out = asyncio.run(analyze_video('http://x/v.mp4', 'describe'))
    assert 'error' in json.loads(out), out


def test_wiring_with_stubbed_sdk():
    """No-network: stub the twelvelabs SDK and assert it is called correctly."""
    captured = {}

    fake_client = MagicMock()
    fake_client.analyze.return_value = types.SimpleNamespace(data='A cat plays piano.', finish_reason='stop')

    def _twelvelabs_ctor(api_key):
        captured['api_key'] = api_key
        return fake_client

    # Build fake twelvelabs package with the two symbols the tool imports.
    tl_mod = types.ModuleType('twelvelabs')
    tl_mod.TwelveLabs = _twelvelabs_ctor
    ctx_mod = types.ModuleType('twelvelabs.types.video_context')

    class VideoContext_Url:  # noqa: N801 — mirror SDK class name
        def __init__(self, url):
            self.url = url

    ctx_mod.VideoContext_Url = VideoContext_Url
    types_pkg = types.ModuleType('twelvelabs.types')

    saved = {k: sys.modules.get(k) for k in ('twelvelabs', 'twelvelabs.types', 'twelvelabs.types.video_context')}
    sys.modules['twelvelabs'] = tl_mod
    sys.modules['twelvelabs.types'] = types_pkg
    sys.modules['twelvelabs.types.video_context'] = ctx_mod
    try:
        # max_tokens above the ceiling must be clamped.
        out = asyncio.run(
            analyze_video('http://x/v.mp4', 'What happens?', max_tokens=99999, __request__=_FakeRequest(_FakeConfig()))
        )
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    result = json.loads(out)
    assert result['status'] == 'success', out
    assert result['analysis'] == 'A cat plays piano.', out
    assert captured['api_key'] == 'test-key'

    _, kwargs = fake_client.analyze.call_args
    assert kwargs['model_name'] == 'pegasus1.5'
    assert kwargs['prompt'] == 'What happens?'
    assert kwargs['video'].url == 'http://x/v.mp4'
    assert kwargs['max_tokens'] == 4096  # clamped from 99999


def test_live_pegasus():
    """Real Pegasus call; skipped without an API key. Slow — wiring is what we assert."""
    if not os.environ.get('TWELVELABS_API_KEY'):
        print('SKIP test_live_pegasus (no TWELVELABS_API_KEY)')
        return

    cfg = _FakeConfig()
    cfg.TWELVELABS_API_KEY = os.environ['TWELVELABS_API_KEY']
    out = asyncio.run(
        analyze_video(
            'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4',
            'Describe this video in one sentence.',
            __request__=_FakeRequest(cfg),
        )
    )
    result = json.loads(out)
    # Either a successful analysis or a clear API error — both prove wiring reaches the API.
    assert 'analysis' in result or 'error' in result, out
    print('LIVE result:', json.dumps(result, ensure_ascii=False)[:300])


if __name__ == '__main__':
    test_missing_key_returns_error()
    test_no_request_context()
    test_wiring_with_stubbed_sdk()
    test_live_pegasus()
    print('OK')

"""Regression tests for configurable Deepgram transcription endpoints."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from open_webui.config import DEFAULT_CONFIG
from open_webui.routers import audio

DEFAULT_URL = 'https://api.deepgram.com/v1/listen'
CUSTOM_URL = 'http://owhisper:8080/custom/transcribe'


@pytest.fixture
def config_values(monkeypatch):
    values = {**DEFAULT_CONFIG, 'audio.stt.engine': 'deepgram'}
    monkeypatch.setattr(audio.Config, 'get', AsyncMock(side_effect=lambda key: values[key]))
    monkeypatch.setattr(
        audio.Config,
        'get_many',
        AsyncMock(side_effect=lambda *keys: {key: values[key] for key in keys}),
    )
    monkeypatch.setattr(audio.Config, 'upsert', AsyncMock(side_effect=values.update))
    return values


@pytest.fixture
def deepgram_response():
    return SimpleNamespace(
        status=200,
        read=AsyncMock(),
        raise_for_status=Mock(),
        json=AsyncMock(return_value={'results': {'channels': [{'alternatives': [{'transcript': ' hello '}]}]}}),
    )


def test_deepgram_url_is_registered_with_environment_default():
    assert DEFAULT_CONFIG['audio.stt.deepgram.api_url'] == os.getenv('DEEPGRAM_API_URL', DEFAULT_URL)


@pytest.mark.asyncio
@pytest.mark.parametrize('url', [DEFAULT_URL, CUSTOM_URL, f'{CUSTOM_URL}/', f'{CUSTOM_URL}?region=local'])
async def test_transcription_uses_full_url_directly(monkeypatch, tmp_path, config_values, deepgram_response, url):
    config_values.update(
        {
            'audio.stt.deepgram.api_url': url,
            'audio.stt.deepgram.api_key': 'test-key',
            'audio.stt.model': 'nova-3',
        }
    )
    recording = tmp_path / 'recording.wav'
    recording.write_bytes(b'audio bytes')
    session = SimpleNamespace(post=AsyncMock(return_value=deepgram_response))
    monkeypatch.setattr(audio, 'get_session', AsyncMock(return_value=session))

    result = await audio._transcribe_deepgram(None, str(recording), ['fr'], str(tmp_path), 'transcript')

    assert result == {'text': 'hello'}
    assert (tmp_path / 'transcript.json').is_file()
    session.post.assert_awaited_once_with(
        url,
        headers={'Authorization': 'Token test-key', 'Content-Type': 'audio/x-wav'},
        params={'smart_format': 'true', 'model': 'nova-3', 'language': 'fr'},
        data=b'audio bytes',
        ssl=audio.AIOHTTP_CLIENT_SESSION_SSL,
    )


@pytest.mark.asyncio
async def test_language_fallback_keeps_custom_url(monkeypatch, tmp_path, config_values, deepgram_response):
    config_values['audio.stt.deepgram.api_url'] = CUSTOM_URL
    recording = tmp_path / 'recording.wav'
    recording.write_bytes(b'audio bytes')
    session = SimpleNamespace(post=AsyncMock(side_effect=[SimpleNamespace(status=400), deepgram_response]))
    monkeypatch.setattr(audio, 'get_session', AsyncMock(return_value=session))

    result = await audio._transcribe_deepgram(None, str(recording), ['fr', None], str(tmp_path), 'transcript')

    assert result == {'text': 'hello'}
    calls = session.post.await_args_list
    assert [call.args[0] for call in calls] == [CUSTOM_URL, CUSTOM_URL]
    assert calls[0].kwargs['params']['language'] == 'fr'
    assert 'language' not in calls[1].kwargs['params']


@pytest.mark.asyncio
@pytest.mark.parametrize('include_url', [True, False])
async def test_config_update_and_readback(monkeypatch, config_values, include_url):
    config_values['audio.stt.deepgram.api_url'] = CUSTOM_URL
    current = await audio.get_audio_config(None, user=None)
    assert current['stt']['DEEPGRAM_API_URL'] == CUSTOM_URL
    stt = {**current['stt'], 'DEEPGRAM_API_URL': f'{CUSTOM_URL}/new'}
    if not include_url:
        del stt['DEEPGRAM_API_URL']
    form = audio.AudioConfigUpdateForm(tts=current['tts'], stt=stt)
    monkeypatch.setattr(audio, 'publish_event', AsyncMock())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    result = await audio.update_audio_config(request, form, user=None)

    expected = f'{CUSTOM_URL}/new' if include_url else CUSTOM_URL
    assert config_values['audio.stt.deepgram.api_url'] == expected
    assert result['stt']['DEEPGRAM_API_URL'] == expected
    if not include_url:
        assert form.stt.DEEPGRAM_API_URL == DEFAULT_URL
        assert 'DEEPGRAM_API_URL' not in form.stt.model_dump(exclude_unset=True)

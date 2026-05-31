from open_webui.utils.audio import apply_openai_tts_config


def test_apply_openai_tts_config_injects_configured_voice():
    payload = apply_openai_tts_config(
        {'input': 'hello'},
        model='tts-1-hd',
        voice='nova',
        params=None,
    )

    assert payload == {
        'input': 'hello',
        'model': 'tts-1-hd',
        'voice': 'nova',
    }


def test_apply_openai_tts_config_keeps_client_voice():
    payload = apply_openai_tts_config(
        {'input': 'hello', 'voice': 'alloy'},
        model='tts-1-hd',
        voice='nova',
        params=None,
    )

    assert payload['voice'] == 'alloy'


def test_apply_openai_tts_config_replaces_empty_client_voice():
    payload = apply_openai_tts_config(
        {'input': 'hello', 'voice': ''},
        model='tts-1-hd',
        voice='nova',
        params=None,
    )

    assert payload['voice'] == 'nova'


def test_apply_openai_tts_config_allows_params_to_override_payload():
    payload = apply_openai_tts_config(
        {'input': 'hello', 'voice': 'alloy'},
        model='tts-1-hd',
        voice='nova',
        params={'voice': 'echo', 'response_format': 'mp3'},
    )

    assert payload['model'] == 'tts-1-hd'
    assert payload['voice'] == 'echo'
    assert payload['response_format'] == 'mp3'

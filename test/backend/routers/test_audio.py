import ast
from pathlib import Path


def test_openai_stt_transcription_uses_configured_ssl_verification():
    audio_router = Path(__file__).parents[3] / 'backend' / 'open_webui' / 'routers' / 'audio.py'
    tree = ast.parse(audio_router.read_text())

    matching_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'post'
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'requests'
        and any(
            keyword.arg == 'url'
            and isinstance(keyword.value, ast.JoinedStr)
            and any(
                isinstance(value, ast.Constant) and value.value == '/audio/transcriptions'
                for value in keyword.value.values
            )
            for keyword in node.keywords
        )
    ]

    assert matching_calls, 'Expected OpenAI STT transcription request to be present'

    verify_keywords = [keyword.value for call in matching_calls for keyword in call.keywords if keyword.arg == 'verify']

    assert len(verify_keywords) == len(matching_calls)
    assert all(isinstance(value, ast.Name) and value.id == 'AIOHTTP_CLIENT_SESSION_SSL' for value in verify_keywords)

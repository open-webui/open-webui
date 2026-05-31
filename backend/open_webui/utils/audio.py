from typing import Any


def apply_openai_tts_config(
    payload: dict[str, Any],
    model: str,
    voice: str,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply OpenAI TTS config defaults to a request payload."""
    payload = {**payload, 'model': model}
    if not payload.get('voice'):
        payload['voice'] = voice
    return {**payload, **(params or {})}

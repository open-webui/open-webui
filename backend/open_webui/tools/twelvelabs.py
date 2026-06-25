"""
TwelveLabs video analysis tool for Open WebUI.

Provides a built-in `analyze_video` tool that runs TwelveLabs Pegasus video
understanding directly from chat: given a public video URL and a prompt, it
returns a natural-language analysis of what happens in the video.

This is opt-in. The tool is only offered to the model when an admin has
configured a TwelveLabs API key (config `video_analysis.twelvelabs.api_key` /
env `TWELVELABS_API_KEY`). The `twelvelabs` Python SDK is imported lazily so
the dependency is only required when the feature is actually used.

Get a free API key at https://twelvelabs.io.

Re-exported through builtin.py for consistent imports.
"""

import asyncio
import json
import logging

from fastapi import Request

log = logging.getLogger(__name__)

# Pegasus has a 2048-token output ceiling; keep the default well within it.
DEFAULT_MAX_TOKENS = 2048
MAX_MAX_TOKENS = 4096


async def analyze_video(
    video_url: str,
    prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Analyze a video with TwelveLabs Pegasus and return a text answer.

    Use this to understand the contents of a video the user has linked: describe
    what happens, summarize it, answer questions about scenes, actions, objects,
    spoken words, or on-screen text. Works on a publicly reachable video URL.

    :param video_url: A publicly accessible URL to the video to analyze (e.g. an mp4 link).
    :param prompt: What to ask about the video (e.g. "Summarize this video" or "What objects appear?").
    :param max_tokens: Maximum length of the generated analysis (default 2048).
    :return: JSON with the analysis text, or an error message.
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    api_key = getattr(__request__.app.state.config, 'TWELVELABS_API_KEY', None)
    api_key = str(api_key) if api_key else ''
    if not api_key:
        return json.dumps(
            {'error': 'TwelveLabs API key is not configured. Set TWELVELABS_API_KEY to enable video analysis.'}
        )

    model_name = str(getattr(__request__.app.state.config, 'TWELVELABS_PEGASUS_MODEL', None) or 'pegasus1.5')

    # Clamp to Pegasus' supported range.
    try:
        max_tokens = int(max_tokens)
    except (TypeError, ValueError):
        max_tokens = DEFAULT_MAX_TOKENS
    max_tokens = max(1, min(max_tokens, MAX_MAX_TOKENS))

    try:
        from twelvelabs import TwelveLabs
        from twelvelabs.types.video_context import VideoContext_Url
    except ImportError:
        return json.dumps({'error': 'The twelvelabs package is not installed. Install it with: pip install twelvelabs'})

    if __event_emitter__:
        await __event_emitter__(
            {
                'type': 'status',
                'data': {'description': 'Analyzing video with TwelveLabs Pegasus...', 'done': False},
            }
        )

    def _analyze() -> dict:
        client = TwelveLabs(api_key=api_key)
        result = client.analyze(
            model_name=model_name,
            video=VideoContext_Url(url=video_url),
            prompt=prompt,
            max_tokens=max_tokens,
        )
        return {
            'analysis': result.data or '',
            'finish_reason': result.finish_reason,
            'model': model_name,
        }

    try:
        # The SDK call is blocking and can be slow for long videos; run it off the event loop.
        payload = await asyncio.to_thread(_analyze)
    except Exception as e:
        log.exception(f'analyze_video error: {e}')
        if __event_emitter__:
            await __event_emitter__({'type': 'status', 'data': {'description': 'Video analysis failed.', 'done': True}})
        return json.dumps({'error': str(e)})

    if __event_emitter__:
        await __event_emitter__({'type': 'status', 'data': {'description': 'Video analysis complete.', 'done': True}})

    return json.dumps({'status': 'success', **payload}, ensure_ascii=False)

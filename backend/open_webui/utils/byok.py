"""BYOK (Bring Your Own Key) / Direct Connections helper utility.

Extracts user direct connection keys and endpoints to power:
- Audio STT (speech-to-text / whisper)
- Audio TTS (text-to-speech)
- Image generation & editing
- Title generation & tag generation
- Embeddings / RAG
"""

import logging
from typing import Optional, Tuple

log = logging.getLogger(__name__)


def get_user_direct_connections(user) -> dict:
    if not user:
        return {}
    settings = getattr(user, 'settings', None) or {}
    if not isinstance(settings, dict):
        return {}

    # Check top-level directConnections or inside ui.directConnections
    dc = settings.get('directConnections')
    if not dc:
        dc = settings.get('ui', {}).get('directConnections')
    if isinstance(dc, dict):
        return dc
    return {}


def get_user_openai_credentials(user, preferred_model: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (api_url, api_key) from the user's direct connections.
    If multiple connections exist, finds one with a valid key and URL.
    """
    dc = get_user_direct_connections(user)
    urls = dc.get('OPENAI_API_BASE_URLS', []) or []
    keys = dc.get('OPENAI_API_KEYS', []) or []
    configs = dc.get('OPENAI_API_CONFIGS', []) or []

    for idx, (url, key) in enumerate(zip(urls, keys)):
        if url and key:
            # Check if this connection matches prefix or preferred_model if specified
            if preferred_model and idx < len(configs) and configs[idx]:
                prefix = configs[idx].get('prefix_id')
                if prefix and preferred_model.startswith(f'{prefix}.'):
                    return url.rstrip('/'), key
            # Otherwise return first valid pair
            return url.rstrip('/'), key

    return None, None

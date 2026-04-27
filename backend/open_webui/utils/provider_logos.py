"""Map a model id to a default provider logo via regex.

Open WebUI serves model profile images from `GET /api/v1/models/model/profile/image`.
When no admin has set `meta.profile_image_url` for a given model id, the route
falls back to a generic favicon. For models supplied by an upstream connection
(OpenAI, OpenRouter, Ollama, …) that means the UI shows a grey placeholder
unless someone manually creates a model overlay.

This module collapses that step into a regex pass on the model id, so adding
e.g. ``gpt-5``, ``anthropic/claude-opus-4``, or ``gemini-2.5-pro`` to a
connection's allowlist shows the right brand logo immediately. The actual
SVGs are vendored under ``static/providers/`` (sourced from lobehub/lobe-icons,
MIT-licensed) — no runtime CDN dependency.

Resolution order in the route:

    DB has profile_image_url    -> serve it (admin/overlay always wins)
    no profile_image_url        -> regex match -> /static/providers/<slug>.svg
    regex doesn't match         -> /static/favicon.png (unchanged behaviour)

Matching philosophy
-------------------
Patterns are checked in order, first match wins. Each pattern is anchored to
a slash boundary (or the start of the string) so a substring buried mid-id
doesn't accidentally match. In ``host/model`` form (``groq/llama3-70b``,
``openrouter/anthropic/claude-...``) we want the *model* brand, not the
hosting provider — Llama under Groq is still a Llama model. To get that the
inference-provider rules (``groq``) live below the model-family rules
(``meta``/Llama, ``mistral``, …), so they only fire when no model brand is
present in the id (e.g. the bare id ``groq``).

Adding a provider
-----------------
1. Drop the SVG into ``backend/open_webui/static/providers/<slug>.svg``.
2. Append a ``(pattern, slug)`` row to ``_RULES`` below — keep model-brand
   rules above inference-provider rules.
3. Add a row to the test matrix in
   ``backend/open_webui/test/util/test_provider_logos.py``.
"""

from __future__ import annotations

import re

LOGO_PATH = '/static/providers'

# (pattern, asset_slug). The slug is the filename (without extension) of the
# vendored SVG under static/providers/. Order matters — first match wins, and
# specific model-brand rules must come before generic inference-host rules.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'(?:^|/)(?:claude|anthropic)', re.IGNORECASE), 'claude-color'),
    (
        re.compile(
            r'(?:^|/)(?:gpt[-_]?\d|chatgpt|o\d(?:[-_]|$)|openai)',
            re.IGNORECASE,
        ),
        'openai',
    ),
    (re.compile(r'(?:^|/)(?:gemini|google|gemma|palm|bard)', re.IGNORECASE), 'gemini-color'),
    (re.compile(r'(?:^|/)deepseek', re.IGNORECASE), 'deepseek-color'),
    (re.compile(r'(?:^|/)(?:qwen|qwq)', re.IGNORECASE), 'qwen-color'),
    # GLM/ChatGLM are published by Zhipu/Z-AI; they share the zhipu mark.
    (re.compile(r'(?:^|/)(?:z-ai|zhipu|glm|chatglm)', re.IGNORECASE), 'zhipu-color'),
    (
        re.compile(
            r'(?:^|/)(?:mistralai|mistral|mixtral|codestral|magistral|ministral)',
            re.IGNORECASE,
        ),
        'mistral-color',
    ),
    (re.compile(r'(?:^|/)(?:xai|x-ai|grok)', re.IGNORECASE), 'xai'),
    (re.compile(r'(?:^|/)(?:meta-llama|meta|llama)', re.IGNORECASE), 'meta-color'),
    (re.compile(r'(?:^|/)(?:cohere|command[-_]?[arnpl]?)', re.IGNORECASE), 'cohere-color'),
    (re.compile(r'(?:^|/)(?:perplexity|pplx|sonar)', re.IGNORECASE), 'perplexity-color'),
    (re.compile(r'(?:^|/)(?:moonshot|moonshotai|kimi)', re.IGNORECASE), 'moonshot'),
    # Inference-provider rules (below model-family rules so groq/llama3 picks
    # the Llama logo, not the Groq logo).
    (re.compile(r'(?:^|/)groq', re.IGNORECASE), 'groq'),
    (re.compile(r'(?:^|/)ollama', re.IGNORECASE), 'ollama'),
]


def match_provider_slug(model_id: str | None) -> str | None:
    """Return the asset slug for ``model_id``, or None if no rule matches.

    The slug is the bare filename (without extension) of the SVG to serve;
    callers should prefer :func:`provider_logo_url` to get a fully-formed URL.

    >>> match_provider_slug('gpt-5.4')
    'openai'
    >>> match_provider_slug('anthropic/claude-opus-4')
    'claude-color'
    >>> match_provider_slug('something-totally-unknown') is None
    True
    """
    if not isinstance(model_id, str) or not model_id:
        return None
    for pattern, slug in _RULES:
        if pattern.search(model_id):
            return slug
    return None


def provider_logo_url(model_id: str | None) -> str | None:
    """Return the static URL for ``model_id``'s default provider logo, or None.

    >>> provider_logo_url('gpt-5')
    '/static/providers/openai.svg'
    >>> provider_logo_url('anthropic/claude-opus-4')
    '/static/providers/claude-color.svg'
    >>> provider_logo_url('not-a-real-model') is None
    True
    """
    slug = match_provider_slug(model_id)
    if slug is None:
        return None
    return f'{LOGO_PATH}/{slug}.svg'

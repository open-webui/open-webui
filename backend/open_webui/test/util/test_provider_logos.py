"""Behavioural tests for the model-id -> provider-logo regex matcher.

The matcher is the fallback Open WebUI uses to pick a default profile image
for a model when the database has no admin-supplied ``profile_image_url``.
These tests pin down the public contract:

- recognised model ids resolve to a brand slug,
- unrecognised / empty ids resolve to ``None`` (so the route falls through
  to the favicon),
- ``host/model`` ids resolve to the *model* brand, not the host.

Tests use slugs (not full URLs) wherever possible so the suite survives a
change to where the SVGs are served from.
"""

from __future__ import annotations

import os

import pytest
from open_webui.utils.provider_logos import (
    LOGO_PATH,
    match_provider_slug,
    provider_logo_url,
)

# --- per-provider whitelist ------------------------------------------------

# (model_id, expected_slug). The matrix covers every brand the matcher
# ships with, plus a couple of common spelling variations per brand. Adding
# a new rule? Add at least one row here.
PROVIDER_CASES: list[tuple[str, str]] = [
    # OpenAI
    ('gpt-5', 'openai'),
    ('gpt-4o', 'openai'),
    ('GPT-4-turbo', 'openai'),
    ('openai/gpt-4o', 'openai'),
    ('o3-mini', 'openai'),
    ('chatgpt-4o-latest', 'openai'),
    # Anthropic / Claude
    ('claude-3-opus', 'claude-color'),
    ('anthropic/claude-haiku', 'claude-color'),
    ('CLAUDE-OPUS-4', 'claude-color'),
    # Google / Gemini
    ('gemini-2.5-pro', 'gemini-color'),
    ('google/gemma-2-9b', 'gemini-color'),
    # DeepSeek
    ('deepseek/deepseek-v3', 'deepseek-color'),
    ('deepseek-r1', 'deepseek-color'),
    # Qwen
    ('qwen/qwen3-max', 'qwen-color'),
    ('qwq-32b-preview', 'qwen-color'),
    # Zhipu / GLM
    ('z-ai/glm-4.6', 'zhipu-color'),
    ('chatglm3-6b', 'zhipu-color'),
    # Mistral
    ('mistralai/mistral-large', 'mistral-color'),
    ('mixtral-8x7b', 'mistral-color'),
    ('codestral-latest', 'mistral-color'),
    # xAI / Grok
    ('xai/grok-2', 'xai'),
    ('grok-3', 'xai'),
    # Meta / Llama
    ('meta-llama/llama-3-70b', 'meta-color'),
    ('llama-3.1-8b-instruct', 'meta-color'),
    # Cohere
    ('cohere/command-r-plus', 'cohere-color'),
    # Perplexity
    ('perplexity/sonar-large', 'perplexity-color'),
    # Moonshot / Kimi
    ('moonshotai/kimi-k2', 'moonshot'),
    ('kimi-latest', 'moonshot'),
    # Inference hosts (only when no model brand is in the id)
    ('groq', 'groq'),
    ('ollama/local-only', 'ollama'),
]


@pytest.mark.parametrize('model_id, expected_slug', PROVIDER_CASES)
def test_match_provider_slug(model_id: str, expected_slug: str) -> None:
    assert match_provider_slug(model_id) == expected_slug


# --- host/model precedence -------------------------------------------------

# In ids of the form ``host/model``, the model brand should win over the
# inference host. ``groq/llama3`` is a Llama model served by Groq, not a
# generic "Groq" model.
HOST_MODEL_CASES: list[tuple[str, str]] = [
    ('groq/llama3-70b', 'meta-color'),
    ('groq/mixtral-8x7b', 'mistral-color'),
    ('groq/qwen2-72b', 'qwen-color'),
    ('ollama/llama3', 'meta-color'),
    ('ollama/mistral', 'mistral-color'),
]


@pytest.mark.parametrize('model_id, expected_slug', HOST_MODEL_CASES)
def test_model_brand_beats_inference_host(model_id: str, expected_slug: str) -> None:
    assert match_provider_slug(model_id) == expected_slug


# --- negative space --------------------------------------------------------


@pytest.mark.parametrize('bad', ['', None, 'totally-made-up-model-name', '???', '   '])
def test_unknown_returns_none(bad) -> None:
    assert match_provider_slug(bad) is None
    assert provider_logo_url(bad) is None


# --- shape of the URL helper ----------------------------------------------


def test_provider_logo_url_is_under_static_path() -> None:
    url = provider_logo_url('claude-3-opus')
    assert url is not None
    assert url.startswith(LOGO_PATH + '/')
    assert url.endswith('.svg')


def test_every_rule_has_a_vendored_svg() -> None:
    """Every slug the matcher returns must correspond to a real file under
    ``static/providers/``. Catches typos and missing assets at test time
    rather than as a 404 in the browser.
    """
    static_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'static',
            'providers',
        )
    )
    seen_slugs = {match_provider_slug(mid) for mid, _ in PROVIDER_CASES}
    seen_slugs.discard(None)
    missing = [slug for slug in seen_slugs if not os.path.isfile(os.path.join(static_dir, f'{slug}.svg'))]
    assert not missing, f'missing SVG files for slugs: {missing}'

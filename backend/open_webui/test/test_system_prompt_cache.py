import time

from open_webui.utils.system_prompt_cache import (
    SYSTEM_PROMPT_CACHE,
    get_cached_system_prompt,
    invalidate_system_prompt_cache,
    set_cached_system_prompt,
)


def setup_function():
    SYSTEM_PROMPT_CACHE.clear()


def test_cache_returns_warm_entry():
    set_cached_system_prompt(
        'model-1',
        'warm content',
        ttl_seconds=300,
        prompt_name='prompt-a',
        prompt_version='2',
    )

    cached = get_cached_system_prompt('model-1')

    assert cached is not None
    assert cached.content == 'warm content'
    assert cached.prompt_name == 'prompt-a'
    assert cached.prompt_version == '2'


def test_cache_expires_stale_entry():
    stale_at = time.time() - 400
    set_cached_system_prompt(
        'model-1',
        'stale content',
        ttl_seconds=300,
        cached_at=stale_at,
    )

    assert get_cached_system_prompt('model-1') is None


def test_invalidate_removes_entry():
    set_cached_system_prompt('model-1', 'content', ttl_seconds=300)

    invalidate_system_prompt_cache('model-1')

    assert get_cached_system_prompt('model-1') is None

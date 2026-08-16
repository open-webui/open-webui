import time

import pytest

from open_webui.utils.auth import is_valid_token, revoke_user_tokens


class _FakeRedis:
    """Minimal async stand-in: only get/set are exercised by the auth code."""

    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value


@pytest.mark.asyncio
async def test_revoke_user_tokens_invalidates_prior_sessions():
    redis = _FakeRedis()
    user_id = 'user-123'
    now = int(time.time())

    # Before any revocation, an existing session token is valid.
    assert await is_valid_token({'id': user_id, 'iat': now - 10}, redis) is True

    # A password change revokes every existing session for the user.
    assert await revoke_user_tokens(redis, user_id) is True

    # Any token issued before the revocation is now rejected on its next use.
    assert await is_valid_token({'id': user_id, 'iat': now - 10}, redis) is False

    # A token issued after the revocation (a fresh login with the new password)
    # is accepted again.
    assert await is_valid_token({'id': user_id, 'iat': now + 10}, redis) is True


@pytest.mark.asyncio
async def test_revoke_user_tokens_only_targets_the_given_user():
    redis = _FakeRedis()
    now = int(time.time())

    await revoke_user_tokens(redis, 'user-123')

    # Another user's existing sessions are untouched.
    assert await is_valid_token({'id': 'user-456', 'iat': now - 10}, redis) is True


@pytest.mark.asyncio
async def test_revoke_user_tokens_is_noop_without_redis():
    # No Redis means there is nowhere to record the revocation, so the helper
    # reports failure instead of silently pretending the sessions were revoked.
    assert await revoke_user_tokens(None, 'user-123') is False

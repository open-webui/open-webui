"""Regression test for open-webui/open-webui#27117.

Concurrent trusted-header sign-in requests for the same, not-yet-registered
email must resolve to exactly one user account. Before the fix, the
trusted-header branch of ``signin()`` performed a check-then-create with no
guard: every request that observed "no such user" independently called
``signup_handler()``, so concurrent requests each created their own
``user``/``auth`` row for the same email.

This test drives the real ``signin()`` coroutine directly (no HTTP layer)
against a throwaway SQLite database migrated with the project's own Alembic
history, so it exercises the exact schema shipped to users (including the
fact that ``user.email`` currently has no database-level uniqueness
guarantee -- see the issue for details).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid

import pytest

# ``DATABASE_URL`` / ``DATA_DIR`` / ``WEBUI_AUTH_TRUSTED_EMAIL_HEADER`` are all
# read once, at import time, by ``open_webui.env``. They must be set before
# anything under ``open_webui`` is imported, including transitively via
# pytest collection of sibling test modules.
_TMP_DIR = tempfile.mkdtemp(prefix='owui-trusted-header-race-')
os.environ.setdefault('DATA_DIR', _TMP_DIR)
os.environ.setdefault('DATABASE_URL', f'sqlite:///{_TMP_DIR}/webui-test.db')
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret-key-27117')
os.environ.setdefault('WEBUI_AUTH_TRUSTED_EMAIL_HEADER', 'X-Test-Trusted-Email')
os.environ.setdefault('ENABLE_PASSWORD_AUTH', 'True')

from fastapi import Response  # noqa: E402
from open_webui.internal.db import AsyncSessionLocal  # noqa: E402
from open_webui.models.auths import Auth, SigninForm  # noqa: E402
from open_webui.models.users import User  # noqa: E402
from open_webui.routers import auths as auths_router  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

TRUSTED_EMAIL_HEADER = 'X-Test-Trusted-Email'


class _FakeRequest:
    """The subset of ``fastapi.Request`` the trusted-header signin path touches."""

    def __init__(self, headers: dict[str, str]):
        self.headers = headers
        self.app = None
        self.client = None
        self.state = type('State', (), {})()


async def _signin_with_trusted_header(email: str):
    request = _FakeRequest({TRUSTED_EMAIL_HEADER: email})
    form_data = SigninForm(email='unused@example.test', password='unused')
    # DATABASE_ENABLE_SESSION_SHARING defaults to False, so passing ``db=None``
    # matches production behaviour: every data-access call below opens its
    # own short-lived session, same as one HTTP request would.
    return await auths_router.signin(request=request, response=Response(), form_data=form_data, db=None)


@pytest.mark.asyncio
async def test_concurrent_trusted_header_signin_creates_exactly_one_user():
    """16 concurrent trusted-header sign-ins for a new email must yield 1 user."""
    email = f'race-{uuid.uuid4().hex}@example.test'
    concurrency = 16

    results = await asyncio.gather(*(_signin_with_trusted_header(email) for _ in range(concurrency)))

    ids = {result['id'] for result in results}
    assert len(ids) == 1, f'expected {concurrency} concurrent sign-ins to resolve to one user, got {ids}'

    async with AsyncSessionLocal() as session:
        user_count = (
            await session.execute(select(func.count()).select_from(User).where(func.lower(User.email) == email))
        ).scalar_one()
        auth_count = (
            await session.execute(select(func.count()).select_from(Auth).where(func.lower(Auth.email) == email))
        ).scalar_one()

    assert user_count == 1, f'expected exactly 1 "user" row for {email}, found {user_count}'
    assert auth_count == 1, f'expected exactly 1 "auth" row for {email}, found {auth_count}'


@pytest.mark.asyncio
async def test_trusted_header_signin_get_or_create_returns_existing_user():
    """A trusted-header sign-in for an already-registered email must reuse it, not duplicate it."""
    email = f'existing-{uuid.uuid4().hex}@example.test'

    first = await _signin_with_trusted_header(email)
    second = await _signin_with_trusted_header(email)

    assert first['id'] == second['id']

    async with AsyncSessionLocal() as session:
        user_count = (
            await session.execute(select(func.count()).select_from(User).where(func.lower(User.email) == email))
        ).scalar_one()

    assert user_count == 1

"""
JWT + header injection for router integration tests.

Pairs with ``_AuthInjectingClient`` in ``abstract_integration_test`` so calls inside
``with mock_webui_user(...):`` send ``Authorization: Bearer …`` and the user row exists
for ``get_current_user`` DB resolution.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta

from open_webui.models.users import Users
from open_webui.utils.auth import create_token

_mock_auth_headers: ContextVar[dict | None] = ContextVar('_mock_auth_headers', default=None)


def get_optional_mock_headers() -> dict | None:
    return _mock_auth_headers.get()


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@contextmanager
def mock_webui_user(
    id=None,
    role=None,
    name=None,
    email=None,
    profile_image_url=None,
):
    uid = str(id) if id is not None else '1'
    if role is None:
        role = 'admin' if uid == '3' else 'user'
    if name is None:
        name = 'John Doe' if uid == '1' else f'User {uid}'
    if email is None:
        email = 'john.doe@openwebui.com' if uid == '1' else f'user{uid}@openwebui.com'
    if profile_image_url is None:
        profile_image_url = '/user.png' if uid == '1' else f'/api/v1/users/{uid}/profile/image'

    if _run(Users.get_user_by_id(uid)) is None:
        _run(
            Users.insert_new_user(
            id=uid,
            name=name,
            email=email,
            profile_image_url=profile_image_url,
            role=role,
        )
        )

    token = create_token({'id': uid}, expires_delta=timedelta(days=1))
    headers = {'Authorization': f'Bearer {token}'}

    var_token = _mock_auth_headers.set(headers)
    try:
        yield
    finally:
        _mock_auth_headers.reset(var_token)

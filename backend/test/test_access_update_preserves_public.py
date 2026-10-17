"""
Regression test for https://github.com/open-webui/open-webui/issues/32539

The Access dialog resends the resource's full grant list, including a Public
grant that the current user did not set. Filtering that whole list against the
user's sharing permissions strips the pre-existing Public grant, silently
turning the item Private. Only newly added grants may be checked; stored
grants must be preserved (same rule the model editor's Save uses since
754c4b5762).
"""

import types

from open_webui.internal.db import get_async_db
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.prompts import PromptForm, Prompts
from open_webui.models.users import Users
from open_webui.routers.prompts import PromptAccessGrantsForm, update_prompt_access_by_id

ADMIN_ID = 'admin-1'
USER_B_ID = 'user-b'
USER_C_ID = 'user-c'

PUBLIC_READ = {'principal_type': 'user', 'principal_id': '*', 'permission': 'read'}
B_WRITE = {'principal_type': 'user', 'principal_id': USER_B_ID, 'permission': 'write'}
C_WRITE = {'principal_type': 'user', 'principal_id': USER_C_ID, 'permission': 'write'}


def _fake_request():
    return types.SimpleNamespace(
        scope={}, app=types.SimpleNamespace(state=types.SimpleNamespace(redis=None))
    )


async def _setup():
    for uid, role in ((ADMIN_ID, 'admin'), (USER_B_ID, 'user'), (USER_C_ID, 'user')):
        await Users.insert_new_user(uid, f'User {uid}', f'{uid}@example.com', role=role)

    # B may share prompts, but may not make them public.
    async with get_async_db() as session:
        session.add(
            Config(
                key='user.permissions',
                value={
                    'workspace': {'prompts': True},
                    'sharing': {'prompts': True, 'public_prompts': False},
                },
                updated_at=0,
            )
        )
        await session.commit()

    admin = await Users.get_user_by_id(ADMIN_ID)
    prompt = await Prompts.insert_new_prompt(
        ADMIN_ID,
        PromptForm(
            command='/test',
            name='Test prompt',
            content='Hello {{ name }}',
            access_grants=[PUBLIC_READ, B_WRITE],
        ),
    )
    return admin, prompt


def _grant_keys(grants):
    return {(g.principal_type, g.principal_id, g.permission) for g in grants}


async def test_access_dialog_adding_user_keeps_public_sharing():
    admin, prompt = await _setup()
    user_b = await Users.get_user_by_id(USER_B_ID)

    updated = await update_prompt_access_by_id(
        _fake_request(),
        prompt.id,
        PromptAccessGrantsForm(access_grants=[PUBLIC_READ, B_WRITE, C_WRITE]),
        user=user_b,
        db=None,
    )
    assert updated is not None

    grants = _grant_keys(updated.access_grants)
    assert ('user', USER_C_ID, 'write') in grants, 'newly added user must be granted'
    assert ('user', '*', 'read') in grants, 'pre-existing public sharing must be preserved'
    assert ('user', USER_B_ID, 'write') in grants, 'resubmitted stored grant must be preserved'


async def test_access_dialog_new_public_grant_still_requires_permission():
    admin, prompt = await _setup()
    user_b = await Users.get_user_by_id(USER_B_ID)

    # B starts from a non-public prompt and tries to add Public herself.
    await AccessGrants.set_access_grants('prompt', prompt.id, [B_WRITE])

    updated = await update_prompt_access_by_id(
        _fake_request(),
        prompt.id,
        PromptAccessGrantsForm(access_grants=[B_WRITE, PUBLIC_READ]),
        user=user_b,
        db=None,
    )
    assert updated is not None

    grants = _grant_keys(updated.access_grants)
    assert ('user', '*', 'read') not in grants, 'public sharing B cannot grant must be filtered'
    assert ('user', USER_B_ID, 'write') in grants

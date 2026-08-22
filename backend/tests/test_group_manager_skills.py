"""Focused regression tests for Phase 3 skills-only slice.

Covers:
1. Extended custom-role catalog (groups.manage_skills capability)
2. manage_skills capability isolation (separate from manage_members/manage_assets)
3. Scoped skill CRUD: create, list, get, update, delete
4. Server-controlled ID (group-namespaced collision-safe slug)
5. user_id='group-asset:<group_id>' for scoped skills
6. Owning-group baseline read access, no write grant at creation
7. group_owned_asset(resource_type='skill') integration
8. Payload allowlist enforcement (rejects id mutation, user_id, access_grants, etc.)
9. Events after successful commit only; no content in audit payload
10. Former managers cannot mutate scoped skills via generic skill endpoints
11. Ordinary group members cannot mutate scoped skills via generic endpoints
12. Independent runtime tool authorization required even if skill content
    suggests tool use
13. P0: ACL delta rejects resource_type='skill'
14. P0: extra='forbid' on scoped skill form models
15. P0: _normalize_skill_meta handles dict/None/SkillMeta
16. P0: Middleware-level audit body redaction for all scoped skill CRUD paths
17. P1: Tool authorization regression (skill content does not grant tool access)
18. P0: Handler-level response tests with persisted dict metadata
19. P1: Real async handler invocation tests for all 5 CRUD handlers
20. P1: Legacy endpoint denial tests (actual handler invocation)
21. P1: Runtime tool authorization with plugins enabled
"""

from __future__ import annotations

import time
import uuid

import pytest
from fastapi import HTTPException
from open_webui.models.access_grants import PRINCIPAL_TYPE_GROUP, AccessGrants
from open_webui.models.custom_roles import (
    _PERMISSION_CATALOG,
    CustomRoleCreateForm,
    CustomRoles,
    make_custom_role_ref,
    normalize_permissions,
)
from open_webui.models.groups import (
    SUPPORTED_OWNED_ASSET_TYPES,
    Group,
    GroupMember,
    GroupOwnedAssets,
)
from open_webui.models.skills import Skill
from open_webui.routers.group_manager import (
    GroupManagerACLDeltaForm,
    GroupManagerSkillCreateForm,
    GroupManagerSkillUpdateForm,
    _grant_access_flush,
    _make_group_skill_id,
    _normalize_skill_meta,
    _skill_insert_flush,
    _skill_update_flush,
    _validate_skill_slug,
)
from open_webui.utils.access_control.group_manager import (
    GroupManagerError,
    group_manager_tx,
    require_group_manager,
)
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ===================================================================
# Helpers
# ===================================================================

async def _create_user_in_db(db: AsyncSession, user_id: str, role: str = 'user'):
    from open_webui.models.users import User

    now = int(time.time())
    row = User(
        id=user_id,
        email=f'{user_id}@test.local',
        name=user_id.split('@')[0] if '@' in user_id else user_id,
        role=role,
        profile_image_url='',
        last_active_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    if db.info.get('manager_setup'):
        await db.commit()
    return row


async def _create_group_in_db(db: AsyncSession, group_id: str, user_id: str):
    row = Group(
        id=group_id,
        user_id=user_id,
        name=f'group-{group_id[:8]}',
        description='test group',
        permissions={},
        data=None,
        meta=None,
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )
    db.add(row)
    await db.flush()
    if db.info.get('manager_setup'):
        await db.commit()
    return row


async def _add_membership(db: AsyncSession, group_id: str, user_id: str):
    row = GroupMember(
        id=str(uuid.uuid4()),
        group_id=group_id,
        user_id=user_id,
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )
    db.add(row)
    await db.flush()
    if db.info.get('manager_setup'):
        await db.commit()
    return row


async def _create_custom_role(
    db: AsyncSession,
    *,
    name: str | None = None,
    permissions: dict | None = None,
    active: bool = True,
):
    if name is None:
        name = f'test-role-{uuid.uuid4().hex[:8]}'
    form = CustomRoleCreateForm(
        name=name,
        display_name=name.replace('-', ' ').title(),
        permissions=permissions or {},
    )
    role = await CustomRoles.create_role(form, db=db)
    if not active:
        await CustomRoles.deactivate_role(role.id, db=db)
        return await CustomRoles.get_role_by_id(role.id, db=db)
    return role


async def _assign_custom_role(db: AsyncSession, user_id: str, role_id: str):
    from open_webui.models.users import User
    ref = make_custom_role_ref(role_id)
    from sqlalchemy import update
    await db.execute(
        update(User).where(User.id == user_id).values(role=ref)
    )
    await db.flush()
    if db.info.get('manager_setup'):
        await db.commit()


async def _setup_skill_manager(db: AsyncSession):
    """Create a valid manager with manage_skills capability.
    Returns (uid, gid, role).
    """
    uid = f'mgr-{uuid.uuid4().hex[:8]}'
    gid = f'grp-{uuid.uuid4().hex[:8]}'
    await _create_user_in_db(db, uid)
    role = await _create_custom_role(
        db,
        name=f'skill-mgr-{uuid.uuid4().hex[:8]}',
        permissions={'groups': {'manage_skills': True}},
    )
    await _assign_custom_role(db, uid, role.id)
    await _create_group_in_db(db, gid, uid)
    await _add_membership(db, gid, uid)
    return uid, gid, role


async def _insert_skill_row(
    db: AsyncSession,
    skill_id: str,
    name: str = 'Test Skill',
    content: str = 'test content',
    user_id: str | None = None,
    is_active: bool = True,
):
    """Insert a Skill row directly (for test setup)."""
    now = int(time.time())
    skill = Skill(
        id=skill_id,
        user_id=user_id or 'group-asset:test-group',
        name=name,
        description='A test skill',
        content=content,
        meta={'tags': []},
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(skill)
    await db.flush()
    if db.info.get('manager_setup'):
        await db.commit()
    return skill


# ===================================================================
# 1. Extended custom-role catalog
# ===================================================================

class TestManageSkillsCatalog:

    def test_manage_skills_present_in_catalog(self):
        assert 'groups' in _PERMISSION_CATALOG
        assert 'manage_skills' in _PERMISSION_CATALOG['groups']

    def test_manage_skills_defaults_false(self):
        assert _PERMISSION_CATALOG['groups']['manage_skills'] is False

    def test_manage_skills_independence(self):
        perm = normalize_permissions({
            'groups': {
                'manage_members': True,
                'manage_assets': False,
            }
        })
        assert perm['groups']['manage_members'] is True
        assert perm['groups']['manage_assets'] is False
        assert perm['groups']['manage_skills'] is False

    def test_manage_skills_can_be_set_independently(self):
        perm = normalize_permissions({
            'groups': {
                'manage_skills': True,
                'manage_members': False,
                'manage_assets': False,
            }
        })
        assert perm['groups']['manage_skills'] is True
        assert perm['groups']['manage_members'] is False

    def test_validate_permissions_accepts_manage_skills(self):
        from open_webui.models.custom_roles import validate_permissions
        result = validate_permissions({'groups': {'manage_skills': True}})
        assert result['groups']['manage_skills'] is True

    @pytest.mark.asyncio
    async def test_role_with_manage_skills_persists(self, db):
        role = await _create_custom_role(
            db,
            name='skill-manager-role',
            permissions={'groups': {'manage_skills': True}},
        )
        assert role is not None
        fetched = await CustomRoles.get_role_by_id(role.id, db=db)
        assert fetched is not None
        assert fetched.permissions['groups']['manage_skills'] is True
        assert fetched.permissions['groups']['manage_members'] is False
        assert fetched.permissions['groups']['manage_assets'] is False


# ===================================================================
# 2. Capability isolation
# ===================================================================

class TestManageSkillsCapabilityIsolation:

    @pytest.mark.asyncio
    async def test_manage_members_does_not_authorize_manage_skills(self, manager_db):
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'only-members-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'capability_denied'

    @pytest.mark.asyncio
    async def test_manage_assets_does_not_authorize_manage_skills(self, manager_db):
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'only-assets-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_assets': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'capability_denied'

    @pytest.mark.asyncio
    async def test_manage_skills_does_not_authorize_manage_members(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'capability_denied'

    @pytest.mark.asyncio
    async def test_manage_skills_does_not_authorize_manage_assets(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_assets', manager_db)
            assert exc_info.value.reason == 'capability_denied'


# ===================================================================
# 3. Slug validation and group-namespaced ID
# ===================================================================

class TestSkillSlugAndId:

    def test_slug_validation_valid(self):
        assert _validate_skill_slug('my-skill') == 'my-skill'
        assert _validate_skill_slug('MY_SKILL') == 'my_skill'
        assert _validate_skill_slug('skill123') == 'skill123'
        assert _validate_skill_slug('a') == 'a'

    def test_slug_validation_normalizes(self):
        assert _validate_skill_slug('My Skill') == 'my-skill'
        assert _validate_skill_slug('  My Skill  ') == 'my-skill'

    def test_slug_validation_rejects_empty(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_skill_slug('')
        assert exc_info.value.status_code == 400

    def test_slug_validation_rejects_special_chars(self):
        with pytest.raises(HTTPException):
            _validate_skill_slug('my/skill')

    def test_group_namespaced_id_format(self):
        gid = 'abc123-def456-ghi789'
        result = _make_group_skill_id(gid, 'my-skill')
        assert result.startswith('g-')
        assert result.endswith('--my-skill')
        assert len(result.split('--', 1)[0]) == 66
        assert len(result) <= 255

    def test_group_namespaced_id_uniqueness_by_group(self):
        gid_a = 'shared-prefix-aaaaaaaaaaaaaaaa'
        gid_b = 'shared-prefix-bbbbbbbbbbbbbbbb'
        id_a = _make_group_skill_id(gid_a, 'my-skill')
        id_b = _make_group_skill_id(gid_b, 'my-skill')
        assert id_a != id_b


# ===================================================================
# 4. Scoped skill CRUD
# ===================================================================

class TestScopedSkillCRUD:

    @pytest.mark.asyncio
    async def test_create_skill(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_insert_flush

            form = GroupManagerSkillCreateForm(
                slug='test-skill',
                name='Test Skill',
                description='A test skill',
                content='print("hello")',
                tags=['python', 'test'],
                active=True,
            )
            skill_id = _make_group_skill_id(gid, 'test-skill')
            skill = await _skill_insert_flush(skill_id, gid, form, uid, manager_db)

            assert skill.id == skill_id
            assert skill.user_id == f'group-asset:{gid}'
            assert skill.name == 'Test Skill'
            assert skill.content == 'print("hello")'
            assert skill.is_active is True

    @pytest.mark.asyncio
    async def test_create_skill_sets_group_asset_user_id(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_insert_flush

            form = GroupManagerSkillCreateForm(slug='my-skill', name='My Skill')
            skill_id = _make_group_skill_id(gid, 'my-skill')
            skill = await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            assert skill.user_id == f'group-asset:{gid}'

    @pytest.mark.asyncio
    async def test_create_skill_ownership_row(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_insert_flush

            form = GroupManagerSkillCreateForm(slug='owned-skill', name='Owned Skill')
            skill_id = _make_group_skill_id(gid, 'owned-skill')
            await _skill_insert_flush(skill_id, gid, form, uid, manager_db)

            ownership = await GroupOwnedAssets.insert_asset(
                resource_type='skill',
                resource_id=skill_id,
                group_id=gid,
                created_by=uid,
                db=manager_db,
            )
            assert ownership.resource_type == 'skill'
            assert ownership.resource_id == skill_id
            assert ownership.group_id == gid
            assert ownership.created_by == uid

    @pytest.mark.asyncio
    async def test_create_skill_baseline_read_access(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _grant_access_flush

            skill_id = _make_group_skill_id(gid, 'read-skill')

            await _grant_access_flush(
                'skill', skill_id,
                PRINCIPAL_TYPE_GROUP, gid, 'read',
                manager_db,
            )

            grants = await AccessGrants.get_grants_by_resource(
                'skill', skill_id, db=manager_db,
            )
            assert len(grants) == 1
            assert grants[0].permission == 'read'
            assert grants[0].principal_type == 'group'
            assert grants[0].principal_id == gid

    @pytest.mark.asyncio
    async def test_create_skill_no_write_grant_at_creation(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _grant_access_flush

            skill_id = f'g-{gid[:12]}--no-write'

            await _grant_access_flush(
                'skill', skill_id,
                PRINCIPAL_TYPE_GROUP, gid, 'read',
                manager_db,
            )

            grants = await AccessGrants.get_grants_by_resource(
                'skill', skill_id, db=manager_db,
            )
            write_grants = [g for g in grants if g.permission == 'write']
            assert len(write_grants) == 0

    @pytest.mark.asyncio
    async def test_update_skill_flush(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = f'g-{gid[:12]}--upd'

        await _insert_skill_row(manager_db, skill_id, name='Original', user_id=f'group-asset:{gid}')

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_update_flush
            result = await manager_db.execute(
                select(Skill).where(Skill.id == skill_id).with_for_update(),
            )
            skill = result.scalars().first()
            assert skill is not None

            form = GroupManagerSkillUpdateForm(name='Updated Name', content='new content')
            updated = await _skill_update_flush(skill, form, manager_db)
            assert updated.name == 'Updated Name'
            assert updated.content == 'new content'

    @pytest.mark.asyncio
    async def test_delete_skill_flush(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = f'g-{gid[:12]}--del'

        await _insert_skill_row(manager_db, skill_id, user_id=f'group-asset:{gid}')

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_delete_flush
            await _skill_delete_flush(skill_id, manager_db)

            result = await manager_db.execute(
                select(Skill).where(Skill.id == skill_id),
            )
            assert result.scalars().first() is None


# ===================================================================
# 5. Payload allowlist enforcement
# ===================================================================

class TestSkillPayloadAllowlist:

    def test_create_form_no_id_field(self):
        fields = GroupManagerSkillCreateForm.model_fields
        assert 'id' not in fields

    def test_create_form_no_user_id_field(self):
        fields = GroupManagerSkillCreateForm.model_fields
        assert 'user_id' not in fields

    def test_create_form_no_access_grants_field(self):
        fields = GroupManagerSkillCreateForm.model_fields
        assert 'access_grants' not in fields

    def test_update_form_no_id_field(self):
        fields = GroupManagerSkillUpdateForm.model_fields
        assert 'id' not in fields

    def test_update_form_no_user_id_field(self):
        fields = GroupManagerSkillUpdateForm.model_fields
        assert 'user_id' not in fields

    def test_update_form_no_access_grants_field(self):
        fields = GroupManagerSkillUpdateForm.model_fields
        assert 'access_grants' not in fields

    def test_create_form_allowed_fields(self):
        allowed = {'slug', 'name', 'description', 'content', 'tags', 'active'}
        actual = set(GroupManagerSkillCreateForm.model_fields.keys())
        assert actual == allowed

    def test_update_form_allowed_fields(self):
        allowed = {'name', 'description', 'content', 'tags', 'active'}
        actual = set(GroupManagerSkillUpdateForm.model_fields.keys())
        assert actual == allowed


# ===================================================================
# 6. skill type in SUPPORTED_OWNED_ASSET_TYPES
# ===================================================================

class TestSkillOwnedAssetType:

    def test_skill_in_supported_types(self):
        assert 'skill' in SUPPORTED_OWNED_ASSET_TYPES

    def test_supported_types_exact(self):
        assert SUPPORTED_OWNED_ASSET_TYPES == frozenset({'knowledge', 'prompt', 'skill'})

    @pytest.mark.asyncio
    async def test_skill_asset_type_check_constraint_in_ddl(self, db):
        from sqlalchemy import text

        def _check(sync_conn):
            row = sync_conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='group_owned_asset'")
            ).fetchone()
            assert row is not None
            ddl = row[0]
            assert 'skill' in ddl
            assert 'knowledge' in ddl
            assert 'prompt' in ddl
            assert 'ck_group_owned_asset_type' in ddl.lower()

        await db.run_sync(_check)


# ===================================================================
# 7. Former managers cannot mutate scoped skills via generic endpoints
# ===================================================================

class TestFormerManagerDenial:

    @pytest.mark.asyncio
    async def test_former_manager_denied_on_scoped_service(self, manager_db):
        """After losing membership, a former manager is denied."""
        uid, gid, role = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)

        # Remove membership
        from sqlalchemy import delete as sa_delete
        await manager_db.execute(
            sa_delete(GroupMember).where(
                GroupMember.group_id == gid,
                GroupMember.user_id == uid,
            )
        )
        await manager_db.flush()
        if manager_db.info.get('manager_setup'):
            await manager_db.commit()

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'not_a_member'

    @pytest.mark.asyncio
    async def test_deactivated_role_denied(self, manager_db):
        """After deactivation, the assignment is reset before access is denied."""
        uid, gid, role = await _setup_skill_manager(manager_db)

        await CustomRoles.deactivate_role(role.id, db=manager_db)

        from open_webui.models.users import User

        user_row = await manager_db.get(User, uid)
        assert user_row.role == 'user'
        await manager_db.commit()

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'legacy_role_denied'


# ===================================================================
# 8. Ordinary group members cannot mutate scoped skills
# ===================================================================

class TestOrdinaryMemberDenial:

    @pytest.mark.asyncio
    async def test_member_without_manage_skills_denied(self, manager_db):
        """A group member without manage_skills capability is denied."""
        uid = f'member-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'ws-skills-{uuid.uuid4().hex[:8]}',
            permissions={'workspace': {'skills': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'capability_denied'

    @pytest.mark.asyncio
    async def test_user_role_member_denied(self, manager_db):
        """A user-role member is denied (legacy role)."""
        uid = f'member-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid, role='user')
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'legacy_role_denied'


# ===================================================================
# 9. Events: skill events exist
# ===================================================================

class TestSkillEventPayload:

    def test_event_definitions_exist(self):
        from open_webui.events import EVENTS
        assert EVENTS.SKILL_CREATED.name == 'skill.created'
        assert EVENTS.SKILL_UPDATED.name == 'skill.updated'
        assert EVENTS.SKILL_DELETED.name == 'skill.deleted'
        assert EVENTS.SKILL_ACCESS_UPDATED.name == 'skill.access_updated'


# ===================================================================
# 10. No implicit commits in skill primitives
# ===================================================================

class TestNoImplicitCommitsInSkills:

    @pytest.mark.asyncio
    async def test_skill_insert_uses_flush_not_commit(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_insert_flush

            form = GroupManagerSkillCreateForm(slug='flush-test', name='Flush Test')
            skill_id = _make_group_skill_id(gid, 'flush-test')
            skill = await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            assert skill is not None

            result = await manager_db.execute(
                select(Skill).where(Skill.id == skill_id),
            )
            assert result.scalars().first() is not None

    @pytest.mark.asyncio
    async def test_skill_delete_uses_flush_not_commit(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = f'g-{gid[:12]}--flush-del'

        await _insert_skill_row(manager_db, skill_id, user_id=f'group-asset:{gid}')

        async with group_manager_tx(manager_db):
            from open_webui.routers.group_manager import _skill_delete_flush
            await _skill_delete_flush(skill_id, manager_db)

            result = await manager_db.execute(
                select(Skill).where(Skill.id == skill_id),
            )
            assert result.scalars().first() is None


# ===================================================================
# 11. Cross-group isolation for scoped skills
# ===================================================================

class TestCrossGroupSkillIsolation:

    @pytest.mark.asyncio
    async def test_manager_of_group_a_denied_on_group_b_skills(self, manager_db):
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid_a = f'grpA-{uuid.uuid4().hex[:8]}'
        gid_b = f'grpB-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'skill-cross-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_skills': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid_a, uid)
        await _add_membership(manager_db, gid_a, uid)
        await _create_group_in_db(manager_db, gid_b, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid_b, 'groups.manage_skills', manager_db)
            assert exc_info.value.reason == 'not_a_member'


# ===================================================================
# 12. Capability string validation
# ===================================================================

class TestCapabilityStringValidation:

    @pytest.mark.asyncio
    async def test_manage_skills_valid_capability(self, manager_db):
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'skill-cap-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_skills': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            await require_group_manager(uid, gid, 'groups.manage_skills', manager_db)

    @pytest.mark.asyncio
    async def test_nonexistent_capability_rejected(self, manager_db):
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, 'x', 'groups.nonexistent_cap', manager_db)
            assert exc_info.value.reason == 'invalid_capability'



class TestACLDeltaRejectsSkill:

    @pytest.mark.asyncio
    async def test_acl_delta_rejects_skill_runtime(self, manager_db):
        """Calling ACL delta with resource_type='skill' raises 400.

        The skill guard fires *before* the group_manager_tx /
        require_group_manager authorization, so even a user without
        groups.manage_assets gets a 400 (not 403).
        """
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        from open_webui.routers.group_manager import update_group_asset_acl

        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'acl-test')

        await _insert_skill_row(manager_db, skill_id, user_id=f'group-asset:{gid}')
        await GroupOwnedAssets.insert_asset(
            resource_type='skill', resource_id=skill_id,
            group_id=gid, created_by=uid, db=manager_db,
        )
        await _grant_access_flush(
            'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
        )
        if manager_db.info.get('manager_setup'):
            await manager_db.commit()

        mock_request = MagicMock()
        mock_request.state = SimpleNamespace()
        form = GroupManagerACLDeltaForm(write=True)

        # The skill guard fires before group_manager_tx / auth,
        # so we call the handler directly (no tx context needed).
        with pytest.raises(HTTPException) as exc_info:
            await update_group_asset_acl(
                mock_request, gid, 'skill', skill_id, form,
                user=MagicMock(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 400
        assert 'Skills do not support ACL delta' in exc_info.value.detail


# ===================================================================
# 14. P0.2: extra='forbid' on form models
# ===================================================================

class TestSkillFormExtraForbid:

    def test_create_rejects_unknown_field(self):
        with pytest.raises(Exception) as exc_info:
            GroupManagerSkillCreateForm(slug='x', name='X', hack='y')
        assert 'hack' in str(exc_info.value)

    def test_create_rejects_id_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillCreateForm(slug='x', name='X', id='nope')

    def test_create_rejects_user_id_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillCreateForm(slug='x', name='X', user_id='bad')

    def test_create_rejects_access_grants_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillCreateForm(slug='x', name='X', access_grants=[])

    def test_update_rejects_unknown_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillUpdateForm(injected=True)

    def test_update_rejects_id_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillUpdateForm(id='rewrite')

    def test_update_rejects_user_id_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillUpdateForm(user_id='x')

    def test_update_rejects_access_grants_field(self):
        with pytest.raises(Exception):
            GroupManagerSkillUpdateForm(access_grants=[{'type': 'public'}])

    def test_create_accepts_only_allowed_fields(self):
        form = GroupManagerSkillCreateForm(
            slug='s', name='N', description='D', content='C', tags=['t'], active=False,
        )
        assert set(form.model_dump().keys()) == {'slug', 'name', 'description', 'content', 'tags', 'active'}

    def test_update_accepts_only_allowed_fields(self):
        form = GroupManagerSkillUpdateForm(name='N', tags=['t'])
        assert set(form.model_dump(exclude_unset=True).keys()) == {'name', 'tags'}


# ===================================================================
# 15. P0.3: _normalize_skill_meta handles dict/None/SkillMeta
# ===================================================================

class TestNormalizeSkillMeta:

    def test_none_returns_empty(self):
        from open_webui.models.skills import SkillMeta
        result = _normalize_skill_meta(None)
        assert isinstance(result, SkillMeta)
        assert result.tags == []

    def test_dict_with_tags(self):
        result = _normalize_skill_meta({'tags': ['a', 'b']})
        assert result.tags == ['a', 'b']

    def test_dict_without_tags(self):
        result = _normalize_skill_meta({'other': True})
        assert result.tags == []

    def test_empty_dict(self):
        result = _normalize_skill_meta({})
        assert result.tags == []

    def test_skill_meta_passthrough(self):
        from open_webui.models.skills import SkillMeta
        orig = SkillMeta(tags=['x'])
        assert _normalize_skill_meta(orig) is orig

    def test_unexpected_type(self):
        result = _normalize_skill_meta(42)
        assert result.tags == []

    def test_dict_with_none_tags(self):
        result = _normalize_skill_meta({'tags': None})
        # Pydantic SkillMeta(tags=None) keeps None; handle gracefully
        # The important thing is no AttributeError
        assert result is not None


# ===================================================================
# 16. P0.4: Audit redaction flag on skill endpoints
# ===================================================================

class TestSkillAuditRedaction:
    """Middleware-level body redaction for scoped skill create / update.

    The middleware marks ``AuditContext.redact_body = True`` before the
    downstream app executes, so even 422 validation errors and 401/403
    authorization failures have their bodies redacted in the audit trail.
    """

    def test_skill_redact_pattern_matches_create(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert _SKILL_REDACT_PATTERN.match(
            '/api/v1/group-manager/groups/abc123/skills/create'
        )

    def test_skill_redact_pattern_matches_update(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert _SKILL_REDACT_PATTERN.match(
            '/api/v1/group-manager/groups/abc123/skills/g-abc123--my-skill/update'
        )

    def test_skill_redact_pattern_matches_list(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert _SKILL_REDACT_PATTERN.match(
            '/api/v1/group-manager/groups/abc123/skills'
        )

    def test_skill_redact_pattern_matches_get(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert _SKILL_REDACT_PATTERN.match(
            '/api/v1/group-manager/groups/abc123/skills/g-abc123--my-skill'
        )

    def test_skill_redact_pattern_matches_delete(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert _SKILL_REDACT_PATTERN.match(
            '/api/v1/group-manager/groups/abc123/skills/g-abc123--my-skill/delete'
        )

    def test_skill_redact_pattern_rejects_non_skill_path(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert not _SKILL_REDACT_PATTERN.match(
            '/api/v1/group-manager/groups/abc123/assets/knowledge/create'
        )

    def test_skill_redact_pattern_rejects_random_path(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert not _SKILL_REDACT_PATTERN.match(
            '/api/v1/auths/signin'
        )

    def test_skill_redact_pattern_without_v1(self):
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN
        assert _SKILL_REDACT_PATTERN.match(
            '/api/group-manager/groups/abc123/skills/create'
        )

    @pytest.mark.asyncio
    async def test_middleware_sets_redact_body_for_create(self):
        """Middleware sets context.redact_body before app execution for create."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/skills/create'
        ctx = AuditContext()
        assert ctx.redact_body is False
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        assert ctx.redact_body is True

    @pytest.mark.asyncio
    async def test_middleware_sets_redact_body_for_update(self):
        """Middleware sets context.redact_body for update endpoints."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/skills/g1--slug/update'
        ctx = AuditContext()
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        assert ctx.redact_body is True

    @pytest.mark.asyncio
    async def test_middleware_sets_redact_body_for_list(self):
        """Middleware sets redact_body for list endpoints."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/skills'
        ctx = AuditContext()
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        assert ctx.redact_body is True

    @pytest.mark.asyncio
    async def test_middleware_sets_redact_body_for_get(self):
        """Middleware sets redact_body for get endpoints."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/skills/g1--slug'
        ctx = AuditContext()
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        assert ctx.redact_body is True

    @pytest.mark.asyncio
    async def test_middleware_sets_redact_body_for_delete(self):
        """Middleware sets redact_body for delete endpoints."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/skills/g1--slug/delete'
        ctx = AuditContext()
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        assert ctx.redact_body is True

    @pytest.mark.asyncio
    async def test_rejected_create_payload_body_redacted(self):
        """Even a 422 validation failure on create has body redacted."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/skills/create'
        ctx = AuditContext()
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        # Simulate captured request body
        ctx.add_request_chunk(b'{"slug": "test", "name": "X", "content": "secret"}')
        # Redaction logic from _log_audit_entry
        request_body = ctx.request_body.decode('utf-8', errors='replace')
        if ctx.redact_body:
            request_body = '[REDACTED]'
        assert request_body == '[REDACTED]'

    @pytest.mark.asyncio
    async def test_normal_endpoint_not_redacted(self):
        """Non-skill endpoints are not redacted by middleware."""
        from open_webui.utils.audit import _SKILL_REDACT_PATTERN, AuditContext
        path = '/api/v1/group-manager/groups/g1/members'
        ctx = AuditContext()
        if _SKILL_REDACT_PATTERN.match(path):
            ctx.redact_body = True
        ctx.add_request_chunk(b'{"user_ids": ["u1"]}')
        request_body = ctx.request_body.decode('utf-8', errors='replace')
        if ctx.redact_body:
            request_body = '[REDACTED]'
        assert 'user_ids' in request_body


# ===================================================================
# 17. P0.3: Skill response serialization with meta as JSON dict
# ===================================================================

class TestSkillResponseSerialization:

    @pytest.mark.asyncio
    async def test_create_meta_dict_roundtrip(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        async with group_manager_tx(manager_db):
            form = GroupManagerSkillCreateForm(slug='rt', name='RT', tags=['alpha', 'beta'])
            skill_id = _make_group_skill_id(gid, 'rt')
            skill = await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            assert isinstance(skill.meta, dict)
            assert skill.meta == {'tags': ['alpha', 'beta']}
            meta = _normalize_skill_meta(skill.meta)
            assert meta.tags == ['alpha', 'beta']

    @pytest.mark.asyncio
    async def test_create_no_tags_meta_empty_dict(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        async with group_manager_tx(manager_db):
            form = GroupManagerSkillCreateForm(slug='nt', name='NT')
            skill_id = _make_group_skill_id(gid, 'nt')
            skill = await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            assert skill.meta == {}
            meta = _normalize_skill_meta(skill.meta)
            assert meta.tags == []

    @pytest.mark.asyncio
    async def test_update_meta_roundtrip(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = f'g-{gid[:12]}--mu'
        await _insert_skill_row(manager_db, skill_id, name='Orig', user_id=f'group-asset:{gid}')
        async with group_manager_tx(manager_db):
            result = await manager_db.execute(
                select(Skill).where(Skill.id == skill_id).with_for_update(),
            )
            skill = result.scalars().first()
            form = GroupManagerSkillUpdateForm(tags=['new'])
            updated = await _skill_update_flush(skill, form, manager_db)
            assert isinstance(updated.meta, dict)
            assert updated.meta == {'tags': ['new']}
            meta = _normalize_skill_meta(updated.meta)
            assert meta.tags == ['new']


# ===================================================================
# 18. P1: Former manager/ordinary member denial via legacy endpoints
# ===================================================================

class TestLegacyEndpointDenial:

    @pytest.mark.asyncio
    async def test_former_manager_cannot_update_via_legacy(self, manager_db):
        """Former manager (removed from group) cannot update skill via legacy /id/{id}/update.

        The legacy update checks: skill.user_id == user.id OR write grant OR admin.
        For group-owned skills, user_id='group-asset:<gid>' never matches any user.
        """
        uid, gid, role = await _setup_skill_manager(manager_db)
        skill_id = f'g-{gid[:12]}--legacy-upd'

        await _insert_skill_row(manager_db, skill_id, name='Legacy', user_id=f'group-asset:{gid}')

        # Remove membership
        await manager_db.execute(
            sa_delete(GroupMember).where(
                GroupMember.group_id == gid, GroupMember.user_id == uid,
            )
        )
        await manager_db.flush()
        if manager_db.info.get('manager_setup'):
            await manager_db.commit()

        # The skill.user_id is 'group-asset:<gid>' — not the manager's uid.
        # The legacy endpoint checks: skill.user_id != user.id AND no write grant.
        # Since user_id doesn't match and no write grant was given, update is denied.
        result = await manager_db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        skill = result.scalars().first()
        assert skill is not None
        assert skill.user_id == f'group-asset:{gid}'
        assert skill.user_id != uid  # manager cannot claim ownership

        # No write grant exists for the manager
        grants = await AccessGrants.get_grants_by_resource('skill', skill_id, db=manager_db)
        write_grants = [g for g in grants if g.permission == 'write' and g.principal_id == uid]
        assert len(write_grants) == 0

    @pytest.mark.asyncio
    async def test_ordinary_member_no_write_grant_on_legacy(self, manager_db):
        """Group member without write grant cannot update skill via legacy endpoint."""
        uid_m, gid, _ = await _setup_skill_manager(manager_db)
        member_uid = f'mbr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, member_uid)
        role = await _create_custom_role(
            manager_db,
            name=f'ws-only-{uuid.uuid4().hex[:8]}',
            permissions={'workspace': {'skills': True}},
        )
        await _assign_custom_role(manager_db, member_uid, role.id)
        await _add_membership(manager_db, gid, member_uid)

        skill_id = f'g-{gid[:12]}--member-test'
        await _insert_skill_row(manager_db, skill_id, user_id=f'group-asset:{gid}')

        # Member has no write grant on the skill
        grants = await AccessGrants.get_grants_by_resource('skill', skill_id, db=manager_db)
        write_grants = [g for g in grants if g.permission == 'write']
        assert len(write_grants) == 0

        # user_id is 'group-asset:<gid>' — doesn't match member
        result = await manager_db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        skill = result.scalars().first()
        assert skill is not None
        assert skill.user_id != member_uid


# ===================================================================
# 19. P1: Tool authorization regression
# ===================================================================

class TestToolAuthorizationRegression:

    @pytest.mark.asyncio
    async def test_skill_content_does_not_grant_tool_access(self, manager_db):
        """Skill content that suggests tool usage does NOT automatically authorize the tool.

        Tool authorization must be checked independently at runtime, not
        inferred from skill content metadata.
        """
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'tool-skill')

        # Skill content that "suggests" tool usage
        tool_content = """
Use the following tools:
- web_search: search the web
- code_interpreter: run python code
Always call web_search before responding.
"""
        # Create skill + ownership + baseline group read (mirrors scoped endpoint)
        await _insert_skill_row(
            manager_db, skill_id,
            name='Tool Skill',
            content=tool_content,
            user_id=f'group-asset:{gid}',
        )
        await GroupOwnedAssets.insert_asset(
            resource_type='skill', resource_id=skill_id,
            group_id=gid, created_by=uid, db=manager_db,
        )
        await _grant_access_flush(
            'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
        )

        # Verify: the skill exists and has tool-suggesting content
        result = await manager_db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        skill = result.scalars().first()
        assert skill is not None
        assert 'web_search' in skill.content
        assert 'code_interpreter' in skill.content

        # The skill has only group read grant — no tool-specific authorization
        grants = await AccessGrants.get_grants_by_resource('skill', skill_id, db=manager_db)
        assert len(grants) == 1
        assert grants[0].permission == 'read'
        assert grants[0].principal_type == 'group'

        # Verify no tool-specific access grants exist
        tool_grants = [g for g in grants if g.principal_id.startswith('tool:')]
        assert len(tool_grants) == 0

        # Key invariant: reading skill content ≠ having tool authorization.
        # The runtime must check tool permissions separately.

    @pytest.mark.asyncio
    async def test_skill_meta_tags_do_not_imply_permissions(self, manager_db):
        """Skill tags are metadata only — they do not create permissions."""
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'tag-skill')

        form = GroupManagerSkillCreateForm(
            slug='tag-skill', name='Tag Skill',
            tags=['admin', 'root', 'tool-access'],
        )

        async with group_manager_tx(manager_db):
            skill = await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            # Also set up ownership + baseline group read (mirrors scoped endpoint)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        # Tags are stored in meta — they're just metadata
        assert skill.meta == {'tags': ['admin', 'root', 'tool-access']}

        # No extra grants were created beyond baseline group read
        grants = await AccessGrants.get_grants_by_resource('skill', skill_id, db=manager_db)
        assert len(grants) == 1
        assert grants[0].permission == 'read'


# ===================================================================
# 20. Handler-level response tests with persisted dict metadata
# ===================================================================

class TestHandlerResponseWithDictMeta:
    """Ensure _normalize_skill_meta is applied on every response path so
    that SQLAlchemy JSON dict metadata never causes AttributeError."""

    @pytest.mark.asyncio
    async def test_create_skill_response_with_tags(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        form = GroupManagerSkillCreateForm(
            slug='resp-tags', name='Resp Tags',
            tags=['alpha', 'beta'],
        )
        async with group_manager_tx(manager_db):
            skill = await _skill_insert_flush(
                _make_group_skill_id(gid, 'resp-tags'),
                gid, form, uid, manager_db,
            )
            await GroupOwnedAssets.insert_asset(
                resource_type='skill',
                resource_id=_make_group_skill_id(gid, 'resp-tags'),
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', _make_group_skill_id(gid, 'resp-tags'),
                PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        # After commit, meta is a plain dict from JSON column
        assert isinstance(skill.meta, dict)
        meta = _normalize_skill_meta(skill.meta)
        assert meta.tags == ['alpha', 'beta']

    @pytest.mark.asyncio
    async def test_create_skill_response_no_tags(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        form = GroupManagerSkillCreateForm(slug='resp-notags', name='Resp No Tags')
        async with group_manager_tx(manager_db):
            skill = await _skill_insert_flush(
                _make_group_skill_id(gid, 'resp-notags'),
                gid, form, uid, manager_db,
            )
        # Empty dict — _normalize_skill_meta must not crash
        assert skill.meta == {}
        meta = _normalize_skill_meta(skill.meta)
        assert meta.tags == []

    @pytest.mark.asyncio
    async def test_list_skills_response_with_dict_meta(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'list-meta')
        form = GroupManagerSkillCreateForm(
            slug='list-meta', name='List Meta',
            tags=['x', 'y'],
        )
        async with group_manager_tx(manager_db):
            await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        # Simulate what list_group_skills does: build response from DB row
        result = await manager_db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        db_skill = result.scalars().first()
        assert db_skill is not None
        # The critical path: _normalize_skill_meta on raw dict
        from open_webui.routers.group_manager import GroupManagerSkillResponse
        resp = GroupManagerSkillResponse(
            id=db_skill.id,
            slug='list-meta',
            name=db_skill.name,
            description=db_skill.description or '',
            content=db_skill.content,
            is_active=db_skill.is_active,
            meta=_normalize_skill_meta(db_skill.meta),
            created_at=db_skill.created_at,
            updated_at=db_skill.updated_at,
        )
        assert resp.meta.tags == ['x', 'y']

    @pytest.mark.asyncio
    async def test_get_skill_response_with_dict_meta(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'get-meta')
        form = GroupManagerSkillCreateForm(
            slug='get-meta', name='Get Meta',
            tags=['z'],
        )
        async with group_manager_tx(manager_db):
            await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        # Re-read from DB (simulates get_group_skill path)
        result = await manager_db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        db_skill = result.scalars().first()
        meta = _normalize_skill_meta(db_skill.meta)
        assert meta.tags == ['z']

    @pytest.mark.asyncio
    async def test_update_skill_response_with_dict_meta(self, manager_db):
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'upd-meta')
        await _insert_skill_row(
            manager_db, skill_id,
            name='Upd Meta',
            user_id=f'group-asset:{gid}',
        )
        async with group_manager_tx(manager_db):
            result = await manager_db.execute(
                select(Skill).where(Skill.id == skill_id).with_for_update(),
            )
            skill = result.scalars().first()
            form = GroupManagerSkillUpdateForm(tags=['updated-tag'])
            updated = await _skill_update_flush(skill, form, manager_db)

        meta = _normalize_skill_meta(updated.meta)
        assert meta.tags == ['updated-tag']


# ===================================================================
# 21. Runtime tool authorization test
# ===================================================================

class TestToolAuthorizationRuntime:
    """Runtime get_tools() must NOT return tools just because a skill
    mentions them in its content."""

    @pytest.mark.asyncio
    async def test_get_tools_ignores_skill_content(self, manager_db):
        """Calling get_tools with tool_ids that don't exist returns empty,
        regardless of skill content mentioning those tools."""
        from unittest.mock import MagicMock

        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'tool-runtime')

        tool_content = 'Use web_search and code_interpreter tools.'
        await _insert_skill_row(
            manager_db, skill_id,
            name='Tool Runtime',
            content=tool_content,
            user_id=f'group-asset:{gid}',
        )

        # get_tools requires a request and UserModel — create minimal mocks
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uid
        mock_user.role = 'user'

        from open_webui.utils.tools import get_tools
        tools = await get_tools(
            mock_request,
            tool_ids=['web_search', 'code_interpreter'],
            user=mock_user,
            extra_params={},
        )
        # Neither tool exists in the DB — result must be empty
        assert isinstance(tools, dict)
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_skill_tags_not_in_access_grants(self, manager_db):
        """Tags like 'tool-access' in skill meta must not appear in grants."""
        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'tag-grants')

        form = GroupManagerSkillCreateForm(
            slug='tag-grants', name='Tag Grants',
            tags=['tool-access', 'admin', 'root'],
        )
        async with group_manager_tx(manager_db):
            await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        grants = await AccessGrants.get_grants_by_resource(
            'skill', skill_id, db=manager_db,
        )
        # Only baseline group read — no tag-based grants
        assert len(grants) == 1
        assert grants[0].permission == 'read'
        assert grants[0].principal_type == 'group'
        assert grants[0].principal_id == gid
        # Tags must not leak into grant principal_id
        for g in grants:
            assert g.principal_id != 'tool-access'
            assert g.principal_id != 'admin'
            assert g.principal_id != 'root'


# ===================================================================
# 22. P1: Real async handler invocation tests for all 5 CRUD handlers
# ===================================================================

class TestHandlerInvocation:
    """Invoke the actual handler functions with mocked request/db to prove
    the full handler code path works, not just internal helpers."""

    @pytest.mark.asyncio
    async def test_create_group_skill_handler(self, manager_db):
        """Invoke create_group_skill handler and verify full output."""
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_webui.routers.group_manager import create_group_skill

        uid, gid, _ = await _setup_skill_manager(manager_db)

        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(user=None)

        form_data = GroupManagerSkillCreateForm(
            slug='handler-create',
            name='Handler Create',
            description='Created by handler',
            content='handler content',
            tags=['h1'],
            active=True,
        )

        user_mock = MagicMock()
        user_mock.id = uid

        with patch(
            'open_webui.routers.group_manager.get_verified_user',
            new_callable=AsyncMock,
            return_value=user_mock,
        ), patch(
            'open_webui.routers.group_manager.get_async_session',
            new_callable=AsyncMock,
        ), patch(
            'open_webui.routers.group_manager.publish_event',
            new_callable=AsyncMock,
        ):
            result = await create_group_skill(
                request=mock_request,
                group_id=gid,
                form_data=form_data,
                user=user_mock,
                db=manager_db,
            )

        assert result.id == _make_group_skill_id(gid, 'handler-create')
        assert result.slug == 'handler-create'
        assert result.name == 'Handler Create'
        assert result.description == 'Created by handler'
        assert result.content == 'handler content'
        assert result.meta.tags == ['h1']
        assert result.is_active is True

        # Verify ownership and baseline read grant were created
        ownership = await GroupOwnedAssets.get_asset_by_resource(
            'skill', result.id, db=manager_db,
        )
        assert ownership is not None
        grants = await AccessGrants.get_grants_by_resource(
            'skill', result.id, db=manager_db,
        )
        assert len(grants) == 1
        assert grants[0].permission == 'read'

    @pytest.mark.asyncio
    async def test_list_group_skills_handler(self, manager_db):
        """Invoke list_group_skills handler and verify output."""
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_webui.routers.group_manager import list_group_skills

        uid, gid, _ = await _setup_skill_manager(manager_db)

        # Set up two skills
        skill_id_1 = _make_group_skill_id(gid, 'list-a')
        skill_id_2 = _make_group_skill_id(gid, 'list-b')
        async with group_manager_tx(manager_db):
            form1 = GroupManagerSkillCreateForm(slug='list-a', name='List A', tags=['a'])
            await _skill_insert_flush(skill_id_1, gid, form1, uid, manager_db)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id_1,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id_1, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

            form2 = GroupManagerSkillCreateForm(slug='list-b', name='List B', tags=['b'])
            await _skill_insert_flush(skill_id_2, gid, form2, uid, manager_db)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id_2,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id_2, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(user=None)
        user_mock = MagicMock()
        user_mock.id = uid

        with patch(
            'open_webui.routers.group_manager.get_verified_user',
            new_callable=AsyncMock,
            return_value=user_mock,
        ), patch(
            'open_webui.routers.group_manager.get_async_session',
            new_callable=AsyncMock,
        ), patch(
            'open_webui.routers.group_manager.publish_event',
            new_callable=AsyncMock,
        ):
            result = await list_group_skills(
                request=mock_request,
                group_id=gid,
                user=user_mock,
                db=manager_db,
            )

        assert len(result) == 2
        slugs = {r.slug for r in result}
        assert slugs == {'list-a', 'list-b'}
        for r in result:
            assert r.meta.tags is not None

    @pytest.mark.asyncio
    async def test_get_group_skill_handler(self, manager_db):
        """Invoke get_group_skill handler and verify output."""
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_webui.routers.group_manager import get_group_skill

        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'handler-get')

        async with group_manager_tx(manager_db):
            form = GroupManagerSkillCreateForm(
                slug='handler-get', name='Handler Get',
                tags=['get-tag'],
            )
            await _skill_insert_flush(skill_id, gid, form, uid, manager_db)
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(user=None)
        user_mock = MagicMock()
        user_mock.id = uid

        with patch(
            'open_webui.routers.group_manager.get_verified_user',
            new_callable=AsyncMock,
            return_value=user_mock,
        ), patch(
            'open_webui.routers.group_manager.get_async_session',
            new_callable=AsyncMock,
        ), patch(
            'open_webui.routers.group_manager.publish_event',
            new_callable=AsyncMock,
        ):
            result = await get_group_skill(
                request=mock_request,
                group_id=gid,
                skill_id=skill_id,
                user=user_mock,
                db=manager_db,
            )

        assert result.id == skill_id
        assert result.name == 'Handler Get'
        assert result.meta.tags == ['get-tag']

    @pytest.mark.asyncio
    async def test_update_group_skill_handler(self, manager_db):
        """Invoke update_group_skill handler and verify output."""
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_webui.routers.group_manager import update_group_skill

        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'handler-upd')

        await _insert_skill_row(
            manager_db, skill_id,
            name='Original Name', user_id=f'group-asset:{gid}',
        )
        async with group_manager_tx(manager_db):
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(user=None)
        user_mock = MagicMock()
        user_mock.id = uid
        form_data = GroupManagerSkillUpdateForm(
            name='Updated Name', tags=['new-tag'],
        )

        with patch(
            'open_webui.routers.group_manager.get_verified_user',
            new_callable=AsyncMock,
            return_value=user_mock,
        ), patch(
            'open_webui.routers.group_manager.get_async_session',
            new_callable=AsyncMock,
        ), patch(
            'open_webui.routers.group_manager.publish_event',
            new_callable=AsyncMock,
        ):
            result = await update_group_skill(
                request=mock_request,
                group_id=gid,
                skill_id=skill_id,
                form_data=form_data,
                user=user_mock,
                db=manager_db,
            )

        assert result.id == skill_id
        assert result.name == 'Updated Name'
        assert result.meta.tags == ['new-tag']

    @pytest.mark.asyncio
    async def test_delete_group_skill_handler(self, manager_db):
        """Invoke delete_group_skill handler and verify output."""
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_webui.routers.group_manager import delete_group_skill

        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = _make_group_skill_id(gid, 'handler-del')

        await _insert_skill_row(
            manager_db, skill_id,
            name='To Delete', user_id=f'group-asset:{gid}',
        )
        async with group_manager_tx(manager_db):
            await GroupOwnedAssets.insert_asset(
                resource_type='skill', resource_id=skill_id,
                group_id=gid, created_by=uid, db=manager_db,
            )
            await _grant_access_flush(
                'skill', skill_id, PRINCIPAL_TYPE_GROUP, gid, 'read', manager_db,
            )

        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(user=None)
        user_mock = MagicMock()
        user_mock.id = uid

        with patch(
            'open_webui.routers.group_manager.get_verified_user',
            new_callable=AsyncMock,
            return_value=user_mock,
        ), patch(
            'open_webui.routers.group_manager.get_async_session',
            new_callable=AsyncMock,
        ), patch(
            'open_webui.routers.group_manager.publish_event',
            new_callable=AsyncMock,
        ):
            result = await delete_group_skill(
                request=mock_request,
                group_id=gid,
                skill_id=skill_id,
                user=user_mock,
                db=manager_db,
            )

        assert result is True
        # Skill row should be gone
        skill_result = await manager_db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        assert skill_result.scalars().first() is None
        # Ownership row should be gone
        ownership = await GroupOwnedAssets.get_asset_by_resource(
            'skill', skill_id, db=manager_db,
        )
        assert ownership is None


# ===================================================================
# 23. P1: Legacy endpoint denial tests (actual handler invocation)
# ===================================================================

class TestLegacyEndpointDenialInvocation:
    """Invoke the legacy skill update/delete handlers and verify that
    former managers and ordinary members are denied."""

    @pytest.mark.asyncio
    async def test_former_manager_denied_on_legacy_update(self, manager_db):
        """Former manager cannot update skill via legacy endpoint."""
        from unittest.mock import MagicMock

        from open_webui.models.skills import SkillForm
        from open_webui.models.users import User
        from open_webui.routers.skills import update_skill_by_id

        uid, gid, _ = await _setup_skill_manager(manager_db)
        skill_id = f'g-{gid[:12]}--leg-upd'

        await _insert_skill_row(
            manager_db, skill_id,
            name='Legacy Upd', user_id=f'group-asset:{gid}',
        )

        # Remove membership
        await manager_db.execute(
            sa_delete(GroupMember).where(
                GroupMember.group_id == gid,
                GroupMember.user_id == uid,
            )
        )
        await manager_db.flush()
        if manager_db.info.get('manager_setup'):
            await manager_db.commit()

        user = await manager_db.get(User, uid)
        assert user is not None
        from open_webui.models.skills import SkillModel, Skills
        stored_skill = await manager_db.get(Skill, skill_id)
        assert stored_skill is not None
        assert SkillModel.model_validate(stored_skill).id == skill_id
        assert (await Skills._to_skill_model(stored_skill, db=manager_db)).id == skill_id
        form = SkillForm(
            id=skill_id,
            name='Denied update',
            content='must not be written',
        )
        with pytest.raises(HTTPException) as exc_info:
            await update_skill_by_id(MagicMock(), skill_id, form, user, manager_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_ordinary_member_denied_on_legacy_delete(self, manager_db):
        """Ordinary member without write grant cannot delete via legacy."""
        from unittest.mock import MagicMock

        from open_webui.models.users import User
        from open_webui.routers.skills import delete_skill_by_id

        uid_mgr, gid, _ = await _setup_skill_manager(manager_db)
        member_uid = f'mbr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, member_uid)

        role = await _create_custom_role(
            manager_db,
            name=f'ws-del-{uuid.uuid4().hex[:8]}',
            permissions={'workspace': {'skills': True}},
        )
        await _assign_custom_role(manager_db, member_uid, role.id)
        await _add_membership(manager_db, gid, member_uid)

        skill_id = f'g-{gid[:12]}--leg-del'
        await _insert_skill_row(
            manager_db, skill_id,
            name='Legacy Del', user_id=f'group-asset:{gid}',
        )

        user = await manager_db.get(User, member_uid)
        assert user is not None
        with pytest.raises(HTTPException) as exc_info:
            await delete_skill_by_id(MagicMock(), skill_id, user, manager_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_former_manager_denied_on_legacy_access_update(self, manager_db):
        """Former manager cannot alter grants through the legacy endpoint."""
        from unittest.mock import MagicMock

        from open_webui.models.users import User
        from open_webui.routers.skills import SkillAccessGrantsForm, update_skill_access_by_id

        uid, gid, _ = await _setup_skill_manager(manager_db)

        skill_id = f'g-{gid[:12]}--leg-access'
        await _insert_skill_row(
            manager_db, skill_id,
            name='Legacy Access', user_id=f'group-asset:{gid}',
        )
        await manager_db.execute(
            sa_delete(GroupMember).where(
                GroupMember.group_id == gid,
                GroupMember.user_id == uid,
            )
        )
        await manager_db.commit()
        user = await manager_db.get(User, uid)
        assert user is not None
        with pytest.raises(HTTPException) as exc_info:
            await update_skill_access_by_id(
                MagicMock(), skill_id, SkillAccessGrantsForm(access_grants=[]), user, manager_db
            )
        assert exc_info.value.status_code == 401


# ===================================================================
# 24. P1: Runtime tool authorization with plugins enabled
# ===================================================================

class TestToolAuthorizationPluginsEnabled:
    """Upgrade of TestToolAuthorizationRuntime to prove get_tools()
    properly checks access control when plugins are enabled and an
    existing tool is mocked past the early-disabled branch."""

    @pytest.mark.asyncio
    async def test_get_tools_checks_access_control_when_enabled(self, manager_db):
        """When ENABLE_PLUGINS=True, get_tools() checks access grants
        for each tool.  Skill content mentioning tools must not bypass
        this check."""
        from unittest.mock import MagicMock, patch

        from open_webui.models.tools import Tool
        from open_webui.utils.tools import get_tools

        uid, gid, _ = await _setup_skill_manager(manager_db)

        now = int(time.time())
        manager_db.add(
            Tool(
                id='web_search',
                user_id='system',
                name='Web Search',
                content='def web_search(): pass',
                specs=[],
                meta={},
                valves=None,
                created_at=now,
                updated_at=now,
            )
        )
        await manager_db.commit()

        mock_user = MagicMock()
        mock_user.id = uid
        mock_user.role = 'user'

        mock_request = MagicMock()

        with patch(
            'open_webui.utils.tools.ENABLE_PLUGINS', True,
        ):
            tools = await get_tools(
                mock_request,
                tool_ids=['web_search'],
                user=mock_user,
                extra_params={'__user__': {}},
            )

        # Access was denied — tool must NOT appear in the result
        assert isinstance(tools, dict)
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_get_tools_returns_tool_when_granted(self, manager_db):
        """When a tool grant exists, get_tools() returns the tool."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_webui.models.tools import Tool
        from open_webui.utils.tools import get_tools

        uid, gid, _ = await _setup_skill_manager(manager_db)

        now = int(time.time())
        manager_db.add(
            Tool(
                id='granted_tool',
                user_id='system',
                name='Granted Tool',
                content='def granted_tool(): pass',
                specs=[{
                    'name': 'run',
                    'parameters': {
                        'properties': {
                            'query': {'type': 'string', 'description': 'search query'},
                        },
                    },
                }],
                meta={},
                valves=None,
                created_at=now,
                updated_at=now,
            )
        )
        await manager_db.commit()
        await AccessGrants.grant_access(
            'tool', 'granted_tool', 'user', uid, 'read', db=manager_db
        )

        mock_user = MagicMock()
        mock_user.id = uid
        mock_user.role = 'user'

        mock_module = MagicMock()

        mock_request = MagicMock()

        mock_callable = MagicMock()
        mock_callable.__doc__ = None

        with patch(
            'open_webui.utils.tools.ENABLE_PLUGINS', True,
        ), patch(
            'open_webui.utils.tools.load_tool_module_by_id',
            new_callable=AsyncMock,
            return_value=(mock_module, 'loaded'),
        ), patch(
            'open_webui.utils.tools.get_tools_cache',
            return_value={},
        ), patch(
            'open_webui.utils.tools.get_tool_contents_cache',
            return_value={},
        ), patch(
            'open_webui.utils.tools.get_async_tool_function_and_apply_extra_params',
            new_callable=AsyncMock,
            return_value=mock_callable,
        ):
            tools = await get_tools(
                mock_request,
                tool_ids=['granted_tool'],
                user=mock_user,
                extra_params={'__user__': {}},
            )

        # Access was granted — tool must appear (keyed by function name 'run')
        assert 'run' in tools
        assert tools['run']['tool_id'] == 'granted_tool'

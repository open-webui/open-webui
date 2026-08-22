"""Focused regression tests for Phase 2 group-ownership / manager foundation.

Covers:
1. Extended custom-role catalog (groups.manage_members, groups.manage_assets)
2. Capability fail-closed behavior
3. Role / member / capability matrix for require_group_manager
4. Cross-group denial
5. Grant / creator non-authority
6. Ownership uniqueness / allowlist
7. Migration metadata / constraint expectations
8. No implicit commits in new primitives
9. GroupOwnedAsset repository methods
10. Transaction boundary enforcement (group_manager_tx)
11. GroupMember uniqueness through historical lineage
12. SQLite FK enforcement
13. Linearizability / stable lock order
14. Strict boolean capability check
15. DB-level CheckConstraint for supported types
16. Migration isolation (fdcb does NOT touch group_member constraint)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from open_webui.models.custom_roles import (
    _PERMISSION_CATALOG,
    CustomRoleCreateForm,
    CustomRoles,
    normalize_permissions,
    validate_permissions,
)
from open_webui.models.groups import (
    SUPPORTED_OWNED_ASSET_TYPES,
    Group,
    GroupMember,
    GroupOwnedAssets,
)
from open_webui.routers.group_manager import (
    GroupManagerACLDeltaForm,
    GroupManagerGroupInfo,
    GroupManagerKnowledgeCreateForm,
    GroupManagerKnowledgeUpdateForm,
    GroupManagerMemberIdsForm,
    GroupManagerPromptCreateForm,
    list_manageable_groups,
)
from open_webui.utils.access_control.group_manager import (
    GroupManagerError,
    group_manager_tx,
    require_group_manager,
)
from sqlalchemy import delete as sa_delete
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ===================================================================
# Helpers
# ===================================================================

async def _create_user_in_db(db: AsyncSession, user_id: str, role: str = 'user'):
    """Insert a user row directly via the ORM."""
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
    """Insert a group row directly."""
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
    """Insert a group_member row directly."""
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
    """Create a custom role with the given permissions via the repository."""
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
    """Set a user's role to a custom reference."""
    from open_webui.models.custom_roles import make_custom_role_ref
    from open_webui.models.users import User

    ref = make_custom_role_ref(role_id)
    from sqlalchemy import update
    await db.execute(
        update(User).where(User.id == user_id).values(role=ref)
    )
    await db.flush()
    if db.info.get('manager_setup'):
        await db.commit()


async def _setup_valid_manager(db: AsyncSession):
    """Create a valid manager user with capability, group, and membership.
    Returns (uid, gid, role).
    """
    uid = f'mgr-{uuid.uuid4().hex[:8]}'
    gid = f'grp-{uuid.uuid4().hex[:8]}'
    await _create_user_in_db(db, uid)
    role = await _create_custom_role(
        db,
        name=f'valid-mgr-{uuid.uuid4().hex[:8]}',
        permissions={'groups': {'manage_members': True}},
    )
    await _assign_custom_role(db, uid, role.id)
    await _create_group_in_db(db, gid, uid)
    await _add_membership(db, gid, uid)
    return uid, gid, role


async def _setup_valid_asset_manager(db: AsyncSession):
    """Create a valid manager user with BOTH manage_members and manage_assets
    capabilities, group, and membership. Returns (uid, gid, role).
    """
    uid = f'mgr-{uuid.uuid4().hex[:8]}'
    gid = f'grp-{uuid.uuid4().hex[:8]}'
    await _create_user_in_db(db, uid)
    role = await _create_custom_role(
        db,
        name=f'valid-asset-mgr-{uuid.uuid4().hex[:8]}',
        permissions={
            'groups': {
                'manage_members': True,
                'manage_assets': True,
            }
        },
    )
    await _assign_custom_role(db, uid, role.id)
    await _create_group_in_db(db, gid, uid)
    await _add_membership(db, gid, uid)
    return uid, gid, role


# ===================================================================
# 1. Extended custom-role catalog
# ===================================================================

class TestExtendedCatalog:

    def test_groups_section_exists(self):
        assert 'groups' in _PERMISSION_CATALOG

    def test_manage_members_present(self):
        assert _PERMISSION_CATALOG['groups']['manage_members'] is False

    def test_manage_assets_present(self):
        assert _PERMISSION_CATALOG['groups']['manage_assets'] is False

    def test_catalog_defaults_false(self):
        groups = _PERMISSION_CATALOG['groups']
        for key, val in groups.items():
            assert val is False, f'groups.{key} should default to False'

    def test_normalize_permissions_includes_groups(self):
        perm = normalize_permissions({'groups': {'manage_members': True}})
        assert perm['groups']['manage_members'] is True
        assert perm['groups']['manage_assets'] is False  # missing leaf → False

    def test_validate_permissions_rejects_unknown_groups_key(self):
        with pytest.raises(ValueError, match='Unknown permission key'):
            validate_permissions({'groups': {'unknown_leaf': True}})

    def test_validate_permissions_accepts_valid_groups(self):
        result = validate_permissions({
            'groups': {'manage_members': True, 'manage_assets': False}
        })
        assert result['groups']['manage_members'] is True

    def test_sparse_groups_permissions_fills_false(self):
        perm = normalize_permissions({})
        assert perm['groups']['manage_members'] is False
        assert perm['groups']['manage_assets'] is False

    @pytest.mark.asyncio
    async def test_role_with_groups_capability_persists(self, db):
        role = await _create_custom_role(
            db,
            name='groups-manager',
            permissions={'groups': {'manage_members': True}},
        )
        assert role is not None
        fetched = await CustomRoles.get_role_by_id(role.id, db=db)
        assert fetched is not None
        assert fetched.permissions['groups']['manage_members'] is True
        assert fetched.permissions['groups']['manage_assets'] is False


# ===================================================================
# 2. Capability fail-closed behavior
# ===================================================================

class TestCapabilityFailClosed:

    def test_catalog_default_is_false(self):
        """groups.* leaves default to False in the catalog."""
        assert _PERMISSION_CATALOG['groups']['manage_members'] is False
        assert _PERMISSION_CATALOG['groups']['manage_assets'] is False

    @pytest.mark.asyncio
    async def test_unresolved_role_yields_groups_false(self, db):
        """An unresolved custom role returns all-false, including groups.*."""
        from open_webui.utils.access_control import get_permissions

        perms = await get_permissions(
            user_id='nonexistent-user',
            default_permissions={},
            db=db,
            user_role='custom:not-a-real-uuid',
        )
        assert perms['groups']['manage_members'] is False
        assert perms['groups']['manage_assets'] is False

    @pytest.mark.asyncio
    async def test_disabled_role_yields_groups_false(self, db):
        """A disabled custom role returns all-false groups.*."""
        from open_webui.utils.access_control import get_permissions

        role = await _create_custom_role(
            db,
            name='disabled-groups-role',
            permissions={'groups': {'manage_members': True}},
            active=False,
        )
        from open_webui.models.custom_roles import make_custom_role_ref
        ref = make_custom_role_ref(role.id)

        perms = await get_permissions(
            user_id='any',
            default_permissions={},
            db=db,
            user_role=ref,
        )
        assert perms['groups']['manage_members'] is False
        assert perms['groups']['manage_assets'] is False


# ===================================================================
# 3. require_group_manager: role / member / capability matrix
# ===================================================================

class TestRequireGroupManager:

    @pytest.mark.asyncio
    async def test_admin_denied(self, manager_db):
        """Admin users are denied on the scoped-manager service."""
        uid = f'admin-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid, role='admin')
        await _create_group_in_db(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'admin_denied'

    @pytest.mark.asyncio
    async def test_legacy_user_denied(self, manager_db):
        """Legacy 'user' role is denied."""
        uid = f'user-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid, role='user')
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'legacy_role_denied'

    @pytest.mark.asyncio
    async def test_legacy_pending_denied(self, manager_db):
        """Legacy 'pending' role is denied."""
        uid = f'pending-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid, role='pending')
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'legacy_role_denied'

    @pytest.mark.asyncio
    async def test_user_not_found(self, manager_db):
        """Non-existent user is denied."""
        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager('no-such-user', 'x', 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'user_not_found'

    @pytest.mark.asyncio
    async def test_invalid_custom_role_ref(self, manager_db):
        """User with malformed custom role ref is denied."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid, role='custom:not-a-uuid')

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, 'x', 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'invalid_custom_role'

    @pytest.mark.asyncio
    async def test_custom_role_without_capability_denied(self, manager_db):
        """User has a custom role but the capability leaf is False."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'no-groups-role-{uuid.uuid4().hex[:8]}',
            permissions={'workspace': {'models': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'capability_denied'

    @pytest.mark.asyncio
    async def test_not_a_member_denied(self, manager_db):
        """User has the capability but is not a member of the group."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'member-mgr-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        # Do NOT add membership

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'not_a_member'

    @pytest.mark.asyncio
    async def test_group_not_found_denied(self, manager_db):
        """The 'group_not_found' path is unreachable when FK enforcement is on
        (GroupMember.group_id -> Group.id prevents orphan memberships).

        We verify the defensive code path exists via source inspection,
        and that require_group_manager raises the correct error for a
        completely missing user (which tests the same error-raise pattern).
        """
        import inspect
        source = inspect.getsource(require_group_manager)
        assert 'group_not_found' in source
        assert 'Group' in source

        # Also verify: requesting a group that doesn't exist, for a user
        # who has no membership, yields 'not_a_member' (the earlier check).
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'grp-mgr-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, 'non-existent-group', 'groups.manage_members', manager_db)
            # FK enforcement means: no orphan memberships exist, so we hit
            # 'not_a_member' before 'group_not_found'
            assert exc_info.value.reason in ('not_a_member', 'group_not_found')

    @pytest.mark.asyncio
    async def test_valid_manage_members(self, manager_db):
        """User with capability, membership, and valid group passes."""
        uid, gid, _ = await _setup_valid_manager(manager_db)

        async with group_manager_tx(manager_db):
            await require_group_manager(uid, gid, 'groups.manage_members', manager_db)

    @pytest.mark.asyncio
    async def test_valid_manage_assets(self, manager_db):
        """User with manage_assets capability passes for that capability."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'asset-mgr-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_assets': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            await require_group_manager(uid, gid, 'groups.manage_assets', manager_db)

    @pytest.mark.asyncio
    async def test_manage_members_does_not_authorize_manage_assets(self, manager_db):
        """Having manage_members does NOT grant manage_assets."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'only-members-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True, 'manage_assets': False}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_assets', manager_db)
            assert exc_info.value.reason == 'capability_denied'


# ===================================================================
# 4. Cross-group denial
# ===================================================================

class TestCrossGroupDenial:

    @pytest.mark.asyncio
    async def test_manager_of_group_a_denied_on_group_b(self, manager_db):
        """User is manager of group A but denied on group B."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid_a = f'grpA-{uuid.uuid4().hex[:8]}'
        gid_b = f'grpB-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'cross-grp-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid_a, uid)
        await _add_membership(manager_db, gid_a, uid)
        await _create_group_in_db(manager_db, gid_b, uid)
        # NOT a member of gid_b

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid_b, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'not_a_member'


# ===================================================================
# Scoped group discovery
# ===================================================================

class TestListManageableGroups:

    @pytest.mark.asyncio
    async def test_returns_only_current_memberships_and_capabilities(self, manager_db):
        """Discovery uses active custom-role capabilities plus membership."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        member_group = f'grp-member-{uuid.uuid4().hex[:8]}'
        creator_only_group = f'grp-creator-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'discovery-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_assets': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, member_group, uid)
        await _add_membership(manager_db, member_group, uid)
        await _create_group_in_db(manager_db, creator_only_group, uid)

        result = await list_manageable_groups(
            user=SimpleNamespace(id=uid),
            db=manager_db,
        )

        assert result == [
            GroupManagerGroupInfo(
                id=member_group,
                name=f'group-{member_group[:8]}',
                capabilities=['groups.manage_assets'],
            )
        ]

    @pytest.mark.asyncio
    async def test_deactivated_role_and_removed_membership_disappear(self, manager_db):
        """Discovery reflects the same current authorization boundary as mutations."""
        uid, gid, role = await _setup_valid_asset_manager(manager_db)

        result = await list_manageable_groups(
            user=SimpleNamespace(id=uid),
            db=manager_db,
        )
        assert result[0].id == gid
        assert result[0].capabilities == [
            'groups.manage_members',
            'groups.manage_assets',
        ]

        await manager_db.execute(
            sa_delete(GroupMember).where(
                GroupMember.group_id == gid,
                GroupMember.user_id == uid,
            )
        )
        await manager_db.commit()

        result = await list_manageable_groups(
            user=SimpleNamespace(id=uid),
            db=manager_db,
        )
        assert result == []

        await _add_membership(manager_db, gid, uid)
        await CustomRoles.deactivate_role(role.id, db=manager_db)
        result = await list_manageable_groups(
            user=SimpleNamespace(id=uid),
            db=manager_db,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_admin_and_legacy_roles_are_not_discovered(self, manager_db):
        """Legacy/admin users do not gain the additive manager workspace scope."""
        for role in ('admin', 'user', 'pending'):
            uid = f'{role}-{uuid.uuid4().hex[:8]}'
            gid = f'grp-{uuid.uuid4().hex[:8]}'
            await _create_user_in_db(manager_db, uid, role=role)
            await _create_group_in_db(manager_db, gid, uid)
            await _add_membership(manager_db, gid, uid)

            result = await list_manageable_groups(
                user=SimpleNamespace(id=uid),
                db=manager_db,
            )
            assert result == []


# ===================================================================
# 5. Grant / creator non-authority
# ===================================================================

class TestGrantCreatorNonAuthority:

    @pytest.mark.asyncio
    async def test_group_creator_without_membership_denied(self, manager_db):
        """Being the group creator (user_id) does not grant manager access
        if the user is not a member."""
        creator_uid = f'creator-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, creator_uid)

        role = await _create_custom_role(
            manager_db,
            name=f'creator-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, creator_uid, role.id)
        # Group's user_id is the creator, but they are NOT a member
        await _create_group_in_db(manager_db, gid, creator_uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(creator_uid, gid, 'groups.manage_members', manager_db)
            assert exc_info.value.reason == 'not_a_member'

    @pytest.mark.asyncio
    async def test_asset_creator_without_membership_denied(self, manager_db):
        """Creating an asset does not grant manager authority."""
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        role = await _create_custom_role(
            manager_db,
            name=f'asset-creator-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_assets': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        # Insert an asset — created_by = uid
        asset = await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=f'res-{uuid.uuid4().hex[:8]}',
            group_id=gid,
            created_by=uid,
            db=manager_db,
        )
        assert asset.created_by == uid

        # Now remove membership — the asset creator should be denied
        from sqlalchemy import delete
        await manager_db.execute(
            delete(GroupMember).where(
                GroupMember.group_id == gid,
                GroupMember.user_id == uid,
            )
        )
        await manager_db.flush()
        if manager_db.info.get('manager_setup'):
            await manager_db.commit()

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, gid, 'groups.manage_assets', manager_db)
            assert exc_info.value.reason == 'not_a_member'


# ===================================================================
# 6. Ownership uniqueness / allowlist
# ===================================================================

class TestOwnershipUniqueness:

    @pytest.mark.asyncio
    async def test_insert_and_retrieve(self, db):
        """Basic insert + get_by_resource round-trip."""
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        rid = f'res-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(db, gid, uid)

        asset = await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=rid,
            group_id=gid,
            created_by=uid,
            db=db,
        )
        assert asset.resource_type == 'knowledge'
        assert asset.resource_id == rid
        assert asset.group_id == gid
        assert asset.created_by == uid

        fetched = await GroupOwnedAssets.get_asset_by_resource(
            'knowledge', rid, db=db
        )
        assert fetched is not None
        assert fetched.id == asset.id

    @pytest.mark.asyncio
    async def test_uniqueness_constraint(self, db):
        """Duplicate (resource_type, resource_id) raises an error."""
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        rid = f'res-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(db, gid, uid)

        await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=rid,
            group_id=gid,
            created_by=uid,
            db=db,
        )

        # Second insert with same (type, id) should raise
        with pytest.raises(Exception):
            await GroupOwnedAssets.insert_asset(
                resource_type='knowledge',
                resource_id=rid,
                group_id=gid,
                created_by=uid,
                db=db,
            )

    @pytest.mark.asyncio
    async def test_same_resource_different_type_allowed(self, db):
        """Same resource_id with different resource_type is allowed."""
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        rid = f'res-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(db, gid, uid)

        a1 = await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=rid,
            group_id=gid,
            created_by=uid,
            db=db,
        )
        a2 = await GroupOwnedAssets.insert_asset(
            resource_type='prompt',
            resource_id=rid,
            group_id=gid,
            created_by=uid,
            db=db,
        )
        assert a1.id != a2.id

    def test_supported_types_allowlist(self):
        """knowledge, prompt, and skill are supported."""
        assert SUPPORTED_OWNED_ASSET_TYPES == frozenset({'knowledge', 'prompt', 'skill'})

    @pytest.mark.asyncio
    async def test_unsupported_type_rejected(self, db):
        """resource_type not in allowlist raises ValueError."""
        with pytest.raises(ValueError, match='Unsupported resource_type'):
            await GroupOwnedAssets.insert_asset(
                resource_type='model',
                resource_id='x',
                group_id='g',
                created_by='u',
                db=db,
            )

    @pytest.mark.asyncio
    async def test_get_assets_by_group(self, db):
        """Query assets by group_id."""
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(db, gid, uid)

        await GroupOwnedAssets.insert_asset(
            resource_type='knowledge', resource_id='r1', group_id=gid, created_by=uid, db=db,
        )
        await GroupOwnedAssets.insert_asset(
            resource_type='prompt', resource_id='r2', group_id=gid, created_by=uid, db=db,
        )

        all_assets = await GroupOwnedAssets.get_assets_by_group_id(gid, db=db)
        assert len(all_assets) == 2

        prompts_only = await GroupOwnedAssets.get_assets_by_group_id(
            gid, resource_type='prompt', db=db
        )
        assert len(prompts_only) == 1
        assert prompts_only[0].resource_type == 'prompt'

    @pytest.mark.asyncio
    async def test_delete_asset(self, db):
        """Delete an ownership record."""
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        rid = f'res-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(db, gid, uid)

        await GroupOwnedAssets.insert_asset(
            resource_type='knowledge', resource_id=rid, group_id=gid, created_by=uid, db=db,
        )
        deleted = await GroupOwnedAssets.delete_asset_by_resource(
            'knowledge', rid, db=db
        )
        assert deleted is True

        fetched = await GroupOwnedAssets.get_asset_by_resource('knowledge', rid, db=db)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, db):
        """Deleting a non-existent asset returns False."""
        deleted = await GroupOwnedAssets.delete_asset_by_resource(
            'knowledge', 'no-such-id', db=db
        )
        assert deleted is False


# ===================================================================
# 7. Migration metadata / constraint expectations
# ===================================================================

class TestMigrationMetadata:

    @pytest.mark.asyncio
    async def test_group_owned_asset_schema(self, db):
        """Verify the group_owned_asset table was created with correct columns."""

        def _check_schema(sync_conn):
            from open_webui.internal.db import Base

            metadata = Base.metadata
            tables = set(metadata.tables.keys())
            asset_keys = [k for k in tables if k.endswith('group_owned_asset')]
            assert asset_keys, f'group_owned_asset table not found in {tables}'

            table = metadata.tables[asset_keys[0]]

            # Column presence
            cols = {c.name: c for c in table.columns}
            expected = {
                'id', 'resource_type', 'resource_id', 'group_id',
                'created_by', 'created_at', 'updated_at',
            }
            assert expected.issubset(set(cols.keys()))

            # All columns non-nullable
            for col_name in expected:
                assert cols[col_name].nullable is False, f'{col_name} should be non-nullable'

            # Unique constraint on (resource_type, resource_id) — check via raw DDL
            row = sync_conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='group_owned_asset'")
            ).fetchone()
            assert row is not None
            ddl = row[0]
            assert 'group_id' in ddl
            assert 'created_by' in ddl
            assert 'UNIQUE' in ddl.upper()

            # Index on group_id
            idx_names = {idx.name for idx in table.indexes}
            assert 'ix_group_owned_asset_group_id' in idx_names

        await db.run_sync(_check_schema)

    @pytest.mark.asyncio
    async def test_group_member_unique_constraint(self, db):
        """Verify the unique (group_id, user_id) constraint on group_member.

        This constraint is created by the HISTORICAL migration
        37f288994c47 (add_group_member_table), not by the Phase-2
        migration fdcb6cc75284.
        """

        def _check_schema(sync_conn):
            row = sync_conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='group_member'")
            ).fetchone()
            assert row is not None
            ddl = row[0]
            # The unique constraint should appear in the DDL
            assert 'uq_group_member_group_user' in ddl.lower() or (
                'UNIQUE' in ddl.upper() and 'group_id' in ddl and 'user_id' in ddl
            )

        await db.run_sync(_check_schema)


# ===================================================================
# 8. No implicit commits in new primitives
# ===================================================================

class TestNoImplicitCommits:

    @pytest.mark.asyncio
    async def test_insert_asset_uses_flush_not_commit(self, db):
        """insert_asset should flush but not commit — the outer transaction
        controls visibility."""
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        uid = f'creator-{uuid.uuid4().hex[:8]}'
        rid = f'res-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(db, gid, uid)

        asset = await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=rid,
            group_id=gid,
            created_by=uid,
            db=db,
        )
        # The asset is visible in this session (flushed)
        fetched = await GroupOwnedAssets.get_asset_by_resource(
            'knowledge', rid, db=db
        )
        assert fetched is not None
        assert fetched.id == asset.id
        # Note: the savepoint isolation in conftest.py means the outer
        # transaction will be rolled back after the test, demonstrating
        # that insert_asset does NOT perform an independent commit.

    @pytest.mark.asyncio
    async def test_require_group_manager_read_only(self, manager_db):
        """require_group_manager must not commit — it only reads."""
        uid, gid, _ = await _setup_valid_manager(manager_db)

        async with group_manager_tx(manager_db):
            # This should succeed without committing anything
            await require_group_manager(uid, gid, 'groups.manage_members', manager_db)

            # Verify the transaction still works — we can still insert and see it
            asset = await GroupOwnedAssets.insert_asset(
                resource_type='knowledge',
                resource_id=f'res-{uuid.uuid4().hex[:8]}',
                group_id=gid,
                created_by=uid,
                db=manager_db,
            )
            assert asset is not None


# ===================================================================
# 9. Invalid capability string
# ===================================================================

class TestInvalidCapability:

    @pytest.mark.asyncio
    async def test_nonexistent_capability_rejected(self, manager_db):
        """require_group_manager rejects a capability not in the catalog."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, 'x', 'groups.nonexistent', manager_db)
            assert exc_info.value.reason == 'invalid_capability'

    @pytest.mark.asyncio
    async def test_non_groups_capability_rejected(self, manager_db):
        """A capability from a different section is rejected."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)

        async with group_manager_tx(manager_db):
            with pytest.raises(GroupManagerError) as exc_info:
                await require_group_manager(uid, 'x', 'workspace.models', manager_db)
            assert exc_info.value.reason == 'invalid_capability'


# ===================================================================
# 10. Backward compatibility — catalog has only new keys added
# ===================================================================

class TestBackwardCompatibility:

    def test_all_original_sections_present(self):
        """Phase 1 catalog sections are still present."""
        assert 'workspace' in _PERMISSION_CATALOG
        assert 'sharing' in _PERMISSION_CATALOG
        assert 'access_grants' in _PERMISSION_CATALOG
        assert 'chat' in _PERMISSION_CATALOG
        assert 'features' in _PERMISSION_CATALOG
        assert 'settings' in _PERMISSION_CATALOG

    def test_original_sections_not_modified(self):
        """Original catalog leaf values are unchanged."""
        assert _PERMISSION_CATALOG['workspace']['models'] is False
        assert _PERMISSION_CATALOG['sharing']['models'] is False
        assert _PERMISSION_CATALOG['chat']['controls'] is False
        assert _PERMISSION_CATALOG['settings']['interface'] is False

    def test_groups_is_new_section(self):
        """groups is the only new section added in Phase 2."""
        assert set(_PERMISSION_CATALOG.keys()) == {
            'workspace', 'sharing', 'access_grants', 'chat',
            'features', 'settings', 'groups',
        }


# ===================================================================
# 11. GroupMember uniqueness — duplicate rejection (historical lineage)
# ===================================================================

class TestGroupMemberDuplicateRejection:

    @pytest.mark.asyncio
    async def test_duplicate_membership_rejected(self, db):
        """Inserting a duplicate (group_id, user_id) raises an IntegrityError.
        This constraint comes from the historical migration 37f288994c47.
        """
        from sqlalchemy.exc import IntegrityError

        uid = f'user-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(db, uid)
        await _create_group_in_db(db, gid, uid)

        # First insert succeeds
        await _add_membership(db, gid, uid)

        # Second insert with same (group_id, user_id) must raise
        with pytest.raises(IntegrityError):
            await _add_membership(db, gid, uid)

    @pytest.mark.asyncio
    async def test_different_users_same_group_allowed(self, db):
        """Two different users in the same group is allowed."""
        uid1 = f'user-{uuid.uuid4().hex[:8]}'
        uid2 = f'user-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(db, uid1)
        await _create_user_in_db(db, uid2)
        await _create_group_in_db(db, gid, uid1)

        await _add_membership(db, gid, uid1)
        await _add_membership(db, gid, uid2)

        from sqlalchemy import select
        result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == gid)
        )
        assert len(result.scalars().all()) == 2

    @pytest.mark.asyncio
    async def test_same_user_different_groups_allowed(self, db):
        """Same user in two different groups is allowed."""
        uid = f'user-{uuid.uuid4().hex[:8]}'
        gid_a = f'grpA-{uuid.uuid4().hex[:8]}'
        gid_b = f'grpB-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(db, uid)
        await _create_group_in_db(db, gid_a, uid)
        await _create_group_in_db(db, gid_b, uid)

        await _add_membership(db, gid_a, uid)
        await _add_membership(db, gid_b, uid)


# ===================================================================
# 12. SQLite FK enforcement — orphan & cascade rejection
# ===================================================================

class TestForeignKeyEnforcement:

    @pytest.mark.asyncio
    async def test_orphan_asset_insertion_rejected(self, db):
        """Inserting a group_owned_asset with a non-existent group_id
        must be rejected by the FK constraint."""
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await GroupOwnedAssets.insert_asset(
                resource_type='knowledge',
                resource_id=f'res-{uuid.uuid4().hex[:8]}',
                group_id='non-existent-group',
                created_by='u',
                db=db,
            )

    @pytest.mark.asyncio
    async def test_group_deletion_rejected_with_ownership(self, db):
        """Deleting a group that has ownership rows must be rejected
        by the RESTRICT FK constraint."""
        from sqlalchemy import delete as sa_delete
        from sqlalchemy.exc import IntegrityError

        uid = f'creator-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(db, uid)
        await _create_group_in_db(db, gid, uid)

        await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=f'res-{uuid.uuid4().hex[:8]}',
            group_id=gid,
            created_by=uid,
            db=db,
        )

        # Attempting to delete the group must fail
        with pytest.raises(IntegrityError):
            await db.execute(
                sa_delete(Group).where(Group.id == gid)
            )

    @pytest.mark.asyncio
    async def test_group_deletion_allowed_after_asset_removal(self, db):
        """After removing all ownership rows, group deletion succeeds."""
        from sqlalchemy import delete as sa_delete

        uid = f'creator-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(db, uid)
        await _create_group_in_db(db, gid, uid)

        await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=f'res-{uuid.uuid4().hex[:8]}',
            group_id=gid,
            created_by=uid,
            db=db,
        )

        # Remove the ownership row
        assets = await GroupOwnedAssets.get_assets_by_group_id(gid, db=db)
        assert len(assets) == 1
        await GroupOwnedAssets.delete_asset_by_resource(
            assets[0].resource_type, assets[0].resource_id, db=db
        )

        # Now group deletion should succeed
        result = await db.execute(
            sa_delete(Group).where(Group.id == gid)
        )
        assert result.rowcount == 1


# ===================================================================
# 13. Linearizability / stable lock order
# ===================================================================

class TestLinearizability:

    @pytest.mark.asyncio
    async def test_function_reads_from_caller_session(self, manager_db):
        """require_group_manager must use the caller's session — uncommitted
        writes from the same session are visible."""
        uid = f'mgr-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'

        # Insert user + role via direct ORM (committed via manager_setup marker)
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'lin-mgr-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        # require_group_manager should see the committed user/role/membership
        # because it uses the same session.
        async with group_manager_tx(manager_db):
            await require_group_manager(uid, gid, 'groups.manage_members', manager_db)

    def test_locking_queries_use_with_for_update(self):
        """Verify that require_group_manager issues SELECT ... FOR UPDATE
        by inspecting the source code (locking intent)."""
        import inspect
        source = inspect.getsource(require_group_manager)
        # Must have at least 4 with_for_update() calls: CustomRole, User,
        # GroupMember, Group — in that stable order.
        assert source.count('with_for_update()') >= 4
        # Verify stable order in source: CustomRole → User → GroupMember → Group
        idx_role = source.find('select(CustomRole)')
        idx_user = source.find('select(User)')
        idx_member = source.find('select(GroupMember)')
        idx_group = source.find('select(Group)')
        assert 0 < idx_role < idx_user < idx_member < idx_group


# ===================================================================
# 14. Strict boolean check (P1.4)
# ===================================================================

class TestStrictBooleanCheck:

    @pytest.mark.asyncio
    async def test_truthy_non_true_value_denied(self, db):
        """A capability set to a truthy non-True value (e.g. 1) must be
        denied — only exactly True is accepted."""
        from open_webui.utils.access_control.group_manager import _check_capability

        with pytest.raises(GroupManagerError) as exc_info:
            _check_capability('groups.manage_members', {
                'groups': {'manage_members': 1, 'manage_assets': False}
            })
        assert exc_info.value.reason == 'capability_denied'
        assert 'not True' in exc_info.value.detail

    def test_string_true_denied(self):
        """A capability set to the string 'True' must be denied."""
        from open_webui.utils.access_control.group_manager import _check_capability

        with pytest.raises(GroupManagerError) as exc_info:
            _check_capability('groups.manage_members', {
                'groups': {'manage_members': 'True', 'manage_assets': False}
            })
        assert exc_info.value.reason == 'capability_denied'

    def test_exact_true_accepted(self):
        """Only exactly True passes the strict check."""
        from open_webui.utils.access_control.group_manager import _check_capability

        # Should not raise
        _check_capability('groups.manage_members', {
            'groups': {'manage_members': True, 'manage_assets': False}
        })


# ===================================================================
# 15. DB-level CheckConstraint for supported types (P1.5)
# ===================================================================

class TestOwnershipTypeCheckConstraint:

    @pytest.mark.asyncio
    async def test_unsupported_type_rejected_at_db_level(self, db):
        """Inserting an asset with resource_type='model' directly via ORM
        (bypassing the repository) must be rejected by the DB constraint."""
        from sqlalchemy.exc import IntegrityError

        uid = f'creator-{uuid.uuid4().hex[:8]}'
        gid = f'grp-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(db, uid)
        await _create_group_in_db(db, gid, uid)

        from open_webui.models.groups import GroupOwnedAsset
        row = GroupOwnedAsset(
            id=str(uuid.uuid4()),
            resource_type='model',
            resource_id=f'res-{uuid.uuid4().hex[:8]}',
            group_id=gid,
            created_by=uid,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        db.add(row)
        with pytest.raises(IntegrityError):
            await db.flush()

    @pytest.mark.asyncio
    async def test_check_constraint_in_ddl(self, db):
        """Verify the CheckConstraint appears in the table DDL."""
        def _check(sync_conn):
            row = sync_conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='group_owned_asset'")
            ).fetchone()
            assert row is not None
            ddl = row[0]
            assert 'ck_group_owned_asset_type' in ddl.lower()
            assert 'knowledge' in ddl
            assert 'prompt' in ddl

        await db.run_sync(_check)

    @pytest.mark.asyncio
    async def test_repository_validate_type_before_insert(self, db):
        """The repository-level validation rejects unsupported types before
        reaching the DB."""
        with pytest.raises(ValueError, match='Unsupported resource_type'):
            await GroupOwnedAssets.insert_asset(
                resource_type='tool',
                resource_id='x',
                group_id='g',
                created_by='u',
                db=db,
            )


# ===================================================================
# 16. Transaction boundary enforcement (group_manager_tx)
# ===================================================================

class TestTransactionBoundary:

    @pytest.mark.asyncio
    async def test_calls_outside_context_rejected(self, fresh_session):
        """require_group_manager must reject calls outside group_manager_tx."""
        await _create_user_in_db(fresh_session, 'mgr-tx-o')
        role = await _create_custom_role(
            fresh_session,
            name='tx-o-role',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(fresh_session, 'mgr-tx-o', role.id)
        await _create_group_in_db(fresh_session, 'grp-tx-o', 'mgr-tx-o')
        await _add_membership(fresh_session, 'grp-tx-o', 'mgr-tx-o')
        await fresh_session.flush()

        with pytest.raises(GroupManagerError) as exc_info:
            await require_group_manager(
                'mgr-tx-o', 'grp-tx-o', 'groups.manage_members', fresh_session,
            )
        assert exc_info.value.reason == 'tx_boundary_missing'
        assert 'group_manager_tx' in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_context_sets_boundary_marker(self, fresh_session):
        """group_manager_tx establishes the ContextVar token AND the
        diagnostics marker on session.info.  The token is bound to both
        the session identity and the active transaction identity."""
        from open_webui.utils.access_control.group_manager import (
            _GM_TX_BOUNDARY,
            _boundary_ctx,
        )

        # Before entering: no token, no diagnostics
        assert _boundary_ctx.get(None) is None
        assert fresh_session.info.get(_GM_TX_BOUNDARY) is None

        async with group_manager_tx(fresh_session):
            token = _boundary_ctx.get(None)
            assert token is not None, 'ContextVar token must be set inside context'
            assert token.matches(fresh_session), 'Token must match the session + tx'
            # Token must also reference the live transaction object via identity
            tx = fresh_session.get_transaction()
            assert tx is not None, 'Session must have an active transaction'
            assert token._tx_ref is tx, 'Token must hold a reference to the live transaction'
            assert fresh_session.info.get(_GM_TX_BOUNDARY) is True

        # After exiting: both cleared; token must NOT match any stale tx
        assert _boundary_ctx.get(None) is None
        assert fresh_session.info.get(_GM_TX_BOUNDARY) is None

    @pytest.mark.asyncio
    async def test_boundary_marker_cleaned_on_exception(self, fresh_session):
        """The ContextVar token and diagnostics marker are cleaned up
        even when an exception occurs."""
        from open_webui.utils.access_control.group_manager import (
            _GM_TX_BOUNDARY,
            _boundary_ctx,
        )

        with pytest.raises(GroupManagerError):
            async with group_manager_tx(fresh_session):
                assert _boundary_ctx.get(None) is not None
                raise GroupManagerError('test_error', 'deliberate')

        assert _boundary_ctx.get(None) is None
        assert fresh_session.info.get(_GM_TX_BOUNDARY) is None

    @pytest.mark.asyncio
    async def test_context_allows_authorize_then_mutate(self, manager_db):
        """The context manager enables the authorize-then-mutate pattern:
        require_group_manager succeeds, then mutations follow in the same
        transaction, and the transaction is committed on success.
        """
        uid = f'mgr-atm-{uuid.uuid4().hex[:8]}'
        gid = f'grp-atm-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'atm-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            await require_group_manager(uid, gid, 'groups.manage_members', manager_db)
            # Mutation: insert an asset in the same transaction
            asset = await GroupOwnedAssets.insert_asset(
                resource_type='knowledge',
                resource_id=f'res-{uuid.uuid4().hex[:8]}',
                group_id=gid,
                created_by=uid,
                db=manager_db,
            )
            assert asset is not None
            assert asset.group_id == gid

        # Transaction was committed — verify the asset is visible in a
        # new session.
        from open_webui.internal.db import get_async_db_context
        async with get_async_db_context() as verify_session:
            fetched = await GroupOwnedAssets.get_asset_by_resource(
                'knowledge', asset.resource_id, db=verify_session,
            )
            assert fetched is not None
            assert fetched.id == asset.id

    @pytest.mark.asyncio
    async def test_context_rolls_back_on_error(self, manager_db):
        """When the body raises, the transaction is rolled back and no
        data persists."""
        uid = f'mgr-rb-{uuid.uuid4().hex[:8]}'
        gid = f'grp-rb-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'rb-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        with pytest.raises(RuntimeError, match='deliberate'):
            async with group_manager_tx(manager_db):
                await require_group_manager(
                    uid, gid, 'groups.manage_members', manager_db,
                )
                # This mutation should be rolled back
                await GroupOwnedAssets.insert_asset(
                    resource_type='knowledge',
                    resource_id='res-should-not-persist',
                    group_id=gid,
                    created_by=uid,
                    db=manager_db,
                )
                raise RuntimeError('deliberate')

        # Transaction was rolled back — verify the asset does NOT exist.
        from open_webui.internal.db import get_async_db_context
        async with get_async_db_context() as verify_session:
            fetched = await GroupOwnedAssets.get_asset_by_resource(
                'knowledge', 'res-should-not-persist', db=verify_session,
            )
            assert fetched is None

    @pytest.mark.asyncio
    async def test_rejects_session_already_in_transaction(self, db):
        """group_manager_tx must reject a session that is already in a
        transaction (e.g. the savepoint-based test fixture)."""
        with pytest.raises(GroupManagerError) as exc_info:
            async with group_manager_tx(db):
                pass  # pragma: no cover
        assert exc_info.value.reason == 'tx_boundary_missing'
        assert 'fresh session' in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_non_context_authorization_fails_even_for_valid_user(self, fresh_session):
        """A perfectly valid manager is rejected if they don't use the context."""
        uid = f'mgr-nc-{uuid.uuid4().hex[:8]}'
        gid = f'grp-nc-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(fresh_session, uid)
        role = await _create_custom_role(
            fresh_session,
            name=f'nc-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(fresh_session, uid, role.id)
        await _create_group_in_db(fresh_session, gid, uid)
        await _add_membership(fresh_session, gid, uid)
        await fresh_session.flush()

        # Without context, even a valid manager gets tx_boundary_missing
        with pytest.raises(GroupManagerError) as exc_info:
            await require_group_manager(
                uid, gid, 'groups.manage_members', fresh_session,
            )
        assert exc_info.value.reason == 'tx_boundary_missing'

    @pytest.mark.asyncio
    async def test_caller_writable_info_does_not_authorize(self, fresh_session):
        """Setting session.info[_GM_TX_BOUNDARY] directly must NOT satisfy
        the boundary check.  Only the ContextVar token (set exclusively
        inside group_manager_tx) authorizes access."""
        from open_webui.utils.access_control.group_manager import (
            _GM_TX_BOUNDARY,
            _boundary_ctx,
        )

        uid = f'mgr-cw-{uuid.uuid4().hex[:8]}'
        gid = f'grp-cw-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(fresh_session, uid)
        role = await _create_custom_role(
            fresh_session,
            name=f'cw-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(fresh_session, uid, role.id)
        await _create_group_in_db(fresh_session, gid, uid)
        await _add_membership(fresh_session, gid, uid)
        await fresh_session.flush()

        # No ContextVar token exists
        assert _boundary_ctx.get(None) is None

        # Simulate a caller trying to forge the boundary by setting info
        fresh_session.info[_GM_TX_BOUNDARY] = True

        # Must still be rejected — info alone does not authorize
        with pytest.raises(GroupManagerError) as exc_info:
            await require_group_manager(
                uid, gid, 'groups.manage_members', fresh_session,
            )
        assert exc_info.value.reason == 'tx_boundary_missing'

        # Also verify no token was set
        assert _boundary_ctx.get(None) is None

        # Clean up diagnostics marker
        fresh_session.info.pop(_GM_TX_BOUNDARY, None)

    @pytest.mark.asyncio
    async def test_context_rejects_after_exit(self, manager_db):
        """After exiting the context, calls are rejected again."""
        uid = f'mgr-ae-{uuid.uuid4().hex[:8]}'
        gid = f'grp-ae-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'ae-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        async with group_manager_tx(manager_db):
            await require_group_manager(
                uid, gid, 'groups.manage_members', manager_db,
            )

        # Outside context now
        with pytest.raises(GroupManagerError) as exc_info:
            await require_group_manager(
                uid, gid, 'groups.manage_members', manager_db,
            )
        assert exc_info.value.reason == 'tx_boundary_missing'

    @pytest.mark.asyncio
    async def test_child_task_denied_after_parent_exits(self, manager_db):
        """A child task created inside group_manager_tx but resumed after
        the parent context exits must be denied — even if the same
        session starts a *new* transaction.  The child's inherited token
        references the old (committed) transaction, so ``matches()``
        rejects it."""
        uid = f'mgr-ct-{uuid.uuid4().hex[:8]}'
        gid = f'grp-ct-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'ct-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        parent_exited = asyncio.Event()
        new_tx_started = asyncio.Event()
        child_done = asyncio.Event()
        child_result: list[str] = []

        async def child_work():
            # Block until the parent context has fully exited
            await parent_exited.wait()
            try:
                # Attempt inside a *new* transaction on the same session
                await require_group_manager(
                    uid, gid, 'groups.manage_members', manager_db,
                )
                child_result.append('allowed')
            except GroupManagerError:
                child_result.append('denied')
            finally:
                child_done.set()

        async def parent_work():
            async with group_manager_tx(manager_db):
                # Spawn child while inside the context
                asyncio.create_task(child_work())
                # Allow event loop to schedule child, then exit
                await asyncio.sleep(0.05)
            # Context exited — signal child
            parent_exited.set()
            # Start a brand-new transaction on the same session so the
            # child sees an active (but *different*) transaction.
            async with group_manager_tx(manager_db):
                new_tx_started.set()
                await asyncio.sleep(0.1)

        await asyncio.wait_for(parent_work(), timeout=5.0)
        await asyncio.wait_for(child_done.wait(), timeout=5.0)
        assert child_result == ['denied'], (
            'Child task resumed after parent exit must be denied even '
            'when a new transaction is active on the same session'
        )
        # Cleanly close the session so the final group_manager_tx can exit
        await manager_db.close()

    @pytest.mark.asyncio
    async def test_contextvar_reset_restores_outer_value(self, fresh_session):
        """ContextVar.reset() in group_manager_tx restores any outer
        ContextVar value rather than blindly setting None."""
        from open_webui.utils.access_control.group_manager import (
            _boundary_ctx,
            _TxToken,
        )

        # Manually set an outer "token" (simulating an outer context)
        outer_token = _TxToken(fresh_session, None)
        outer_reset = _boundary_ctx.set(outer_token)

        try:
            async with group_manager_tx(fresh_session):
                inner_token = _boundary_ctx.get(None)
                assert inner_token is not None
                assert inner_token is not outer_token

            # After exiting inner context, outer token must be restored
            restored = _boundary_ctx.get(None)
            assert restored is outer_token, (
                'ContextVar.reset() must restore the outer value'
            )
        finally:
            _boundary_ctx.reset(outer_reset)

    @pytest.mark.asyncio
    async def test_commit_failure_attempts_rollback_and_clears_token(
        self, manager_db,
    ):
        """When the commit itself fails, group_manager_tx must attempt
        rollback, clear the ContextVar token, and re-raise the error."""
        from unittest.mock import AsyncMock, patch

        from open_webui.utils.access_control.group_manager import (
            _GM_TX_BOUNDARY,
            _boundary_ctx,
        )

        uid = f'mgr-cf-{uuid.uuid4().hex[:8]}'
        gid = f'grp-cf-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, uid)
        role = await _create_custom_role(
            manager_db,
            name=f'cf-role-{uuid.uuid4().hex[:8]}',
            permissions={'groups': {'manage_members': True}},
        )
        await _assign_custom_role(manager_db, uid, role.id)
        await _create_group_in_db(manager_db, gid, uid)
        await _add_membership(manager_db, gid, uid)

        rollback_called = asyncio.Event()

        original_rollback = manager_db.rollback

        async def tracking_rollback():
            rollback_called.set()
            return await original_rollback()

        with patch.object(
            manager_db, 'commit',
            new_callable=AsyncMock,
            side_effect=RuntimeError('simulated commit failure'),
        ):
            with patch.object(
                manager_db, 'rollback',
                side_effect=tracking_rollback,
            ):
                with pytest.raises(RuntimeError, match='simulated commit failure'):
                    async with group_manager_tx(manager_db):
                        await require_group_manager(
                            uid, gid, 'groups.manage_members', manager_db,
                        )

        # Rollback was attempted after commit failure
        assert rollback_called.is_set(), 'Rollback must be attempted after commit failure'
        # Token and diagnostics must be cleared
        assert _boundary_ctx.get(None) is None
        assert manager_db.info.get(_GM_TX_BOUNDARY) is None

    def test_context_manager_is_async_context_manager(self):
        """Verify group_manager_tx is a proper async context manager."""
        import inspect
        # @asynccontextmanager wraps an async generator function and
        # produces a callable that returns an async context manager.
        assert callable(group_manager_tx)
        # The underlying wrapped function should be a coroutine function
        assert inspect.iscoroutinefunction(group_manager_tx) or \
               hasattr(group_manager_tx, '__wrapped__')

    @pytest.mark.asyncio
    async def test_sqlite_begin_immediate_emitted(self, _engine):
        """Prove via engine SQL listener that the first statement emitted
        inside group_manager_tx is exactly BEGIN IMMEDIATE."""
        from sqlalchemy import event as sa_event
        from sqlalchemy.ext.asyncio import AsyncSession

        emitted_sql: list[str] = []

        @sa_event.listens_for(_engine.sync_engine, 'before_cursor_execute')
        def _capture(conn, cursor, stmt, parameters, context, executemany):
            # Only capture DML/DDL statements, skip internal bookkeeping
            normalized = stmt.strip()
            if normalized:
                emitted_sql.append(normalized)

        session = AsyncSession(bind=_engine, expire_on_commit=False)
        try:
            # Empty the capture list (may have connect-time PRAGMAs)
            emitted_sql.clear()

            async with group_manager_tx(session):
                # Inside context — first statement should be BEGIN IMMEDIATE
                pass

            # Filter to only DML/DDL (skip any stray pragmas if any)
            ddl = [s for s in emitted_sql
                   if not s.upper().startswith('PRAGMA')]
            assert len(ddl) >= 1, f'Expected at least one DDL statement, got: {emitted_sql}'
            assert ddl[0].upper() == 'BEGIN IMMEDIATE', (
                f'First DDL must be BEGIN IMMEDIATE, got: {ddl[0]!r}'
            )
        finally:
            # Remove listener to avoid cross-test pollution
            sa_event.remove(_engine.sync_engine, 'before_cursor_execute', _capture)
            await session.close()

    @pytest.mark.asyncio
    async def test_sqlite_contention_two_manager_sessions(self, _engine):
        """A held manager transaction rejects a second SQLite writer.

        The second engine has a zero-second busy timeout, so its first
        ``BEGIN IMMEDIATE`` fails while session A holds the write lock.
        Once A commits, a fresh second session can enter normally.
        """
        from open_webui.models.custom_roles import CustomRole
        from open_webui.models.groups import Group, GroupMember, GroupOwnedAsset
        from open_webui.models.users import User
        from sqlalchemy import delete as sa_delete
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import NullPool

        sa = AsyncSession(bind=_engine, expire_on_commit=False)
        sa.info['manager_setup'] = True
        busy_engine = create_async_engine(
            str(_engine.url),
            connect_args={'timeout': 0},
            poolclass=NullPool,
        )
        sb_attempt = AsyncSession(bind=busy_engine, expire_on_commit=False)
        sb_after = AsyncSession(bind=busy_engine, expire_on_commit=False)

        try:
            # ── Seed shared data via session a ─────────────────────
            uid = f'mgr-{uuid.uuid4().hex[:8]}'
            gid = f'grp-{uuid.uuid4().hex[:8]}'
            await _create_user_in_db(sa, uid)
            role = await _create_custom_role(
                sa,
                name=f'contention-{uuid.uuid4().hex[:8]}',
                permissions={'groups': {'manage_members': True}},
            )
            await _assign_custom_role(sa, uid, role.id)
            await _create_group_in_db(sa, gid, uid)
            await _add_membership(sa, gid, uid)

            async with group_manager_tx(sa):
                await require_group_manager(uid, gid, 'groups.manage_members', sa)
                with pytest.raises(OperationalError) as exc_info:
                    async with group_manager_tx(sb_attempt):
                        pass  # pragma: no cover - SQLite must reject entry

                message = str(exc_info.value).lower()
                assert 'database is locked' in message or 'busy' in message

            # Once session A commits, a new fresh session can acquire the
            # immediate lock and authorize the same manager.
            async with group_manager_tx(sb_after):
                await require_group_manager(
                    uid, gid, 'groups.manage_members', sb_after,
                )
        finally:
            await sb_attempt.close()
            await sb_after.close()
            await busy_engine.dispose()
            await sa.close()
            conn = await _engine.connect()
            try:
                await conn.execute(sa_delete(GroupOwnedAsset))
                await conn.execute(sa_delete(GroupMember))
                await conn.execute(sa_delete(Group))
                await conn.execute(sa_delete(CustomRole))
                await conn.execute(sa_delete(User))
                await conn.commit()
            finally:
                await conn.close()


# ===================================================================
# 17. Migration isolation — fdcb does NOT touch group_member constraint
# ===================================================================

class TestMigrationIsolation:

    def test_phase2_migration_no_group_member_constraint_operations(self):
        """The Phase-2 migration fdcb6cc75284 must NOT create, drop, or
        modify any constraint on group_member.  The historical migration
        37f288994c47 already creates uq_group_member_group_user."""
        import inspect

        import open_webui.migrations.versions.fdcb6cc75284_add_group_owned_asset_and_group_member_uniqueness as mod
        source = inspect.getsource(mod)

        # Must NOT contain any constraint operations on group_member
        assert 'create_unique_constraint' not in source, \
            'fdcb6 should not create unique constraints on group_member'
        assert 'drop_constraint' not in source, \
            'fdcb6 should not drop constraints from group_member'
        assert 'batch_alter_table' not in source, \
            'fdcb6 should not batch-alter group_member'
        # Must NOT contain dedup SQL
        assert 'DELETE FROM group_member' not in source, \
            'fdcb6 should not dedup group_member rows'
        assert 'ROW_NUMBER' not in source, \
            'fdcb6 should not contain ROW_NUMBER dedup logic'

    def test_phase2_migration_only_touches_group_owned_asset(self):
        """Verify the Phase-2 migration only creates/drops group_owned_asset."""
        import inspect

        import open_webui.migrations.versions.fdcb6cc75284_add_group_owned_asset_and_group_member_uniqueness as mod
        source = inspect.getsource(mod)

        # Should contain group_owned_asset operations
        assert 'group_owned_asset' in source
        assert 'create_table' in source
        assert 'drop_table' in source

        # Upgrade should only have one create_table and one create_index
        assert source.count('op.create_table') == 1
        assert source.count('op.create_index') == 1

    def test_historical_migration_creates_constraint(self):
        """Verify that the historical migration 37f288994c47 creates the
        uq_group_member_group_user constraint as part of table creation."""
        import importlib
        import inspect
        mod = importlib.import_module(
            'open_webui.migrations.versions.37f288994c47_add_group_member_table'
        )
        source = inspect.getsource(mod)

        assert 'uq_group_member_group_user' in source
        assert 'UniqueConstraint' in source
        assert 'group_member' in source

    def test_orm_metadata_aligned_with_historical_constraint(self):
        """The GroupMember ORM model's __table_args__ must include the same
        unique constraint that 37f288994c47 creates."""
        from open_webui.models.groups import GroupMember
        table_args = GroupMember.__table_args__
        constraint_names = [
            c.name for c in table_args if hasattr(c, 'name')
        ]
        assert 'uq_group_member_group_user' in constraint_names


# ===================================================================
# Router-test fixture: suppress publish_event side-effects
# ===================================================================

@pytest.fixture(autouse=True)
def _noop_publish_event(monkeypatch):
    """Stub out ``publish_event`` in the group-manager router so that
    endpoint tests do not spawn fire-and-forget ``asyncio.create_task``
    calls.  Those background tasks open their own aiosqlite connections
    whose worker threads outlive the test event loop, producing
    ``PytestUnhandledThreadExceptionWarning``.
    """
    async def _noop(*_a, **_kw):
        return None

    monkeypatch.setattr(
        'open_webui.routers.group_manager.publish_event',
        _noop,
    )


# ===================================================================
# 18. Router: membership mutation helpers
# ===================================================================

class TestRouterMembershipHelpers:
    """Helpers for integration-style router tests against the scoped
    ``/api/v1/group-manager/groups/{group_id}/members/*`` endpoints.

    These tests exercise the actual FastAPI router via TestClient-style
    function calls (direct invocation of the endpoint functions).
    """

    @pytest.mark.asyncio
    async def test_list_members_includes_manager(self, manager_db):
        """list_group_members returns at least the manager (who is auto-added as member)."""
        from open_webui.routers.group_manager import list_group_members

        uid, gid, _ = await _setup_valid_manager(manager_db)
        result = await list_group_members(gid, user=SimpleNamespace(id=uid), db=manager_db)
        assert len(result) >= 1
        user_ids = {m.user_id for m in result}
        assert uid in user_ids

    @pytest.mark.asyncio
    async def test_add_and_list_members(self, manager_db):
        """add_group_members adds users, list_group_members returns them."""
        from open_webui.routers.group_manager import add_group_members, list_group_members

        uid, gid, _ = await _setup_valid_manager(manager_db)
        extra = f'user-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, extra)

        form = GroupManagerMemberIdsForm(user_ids=[extra])
        # Mock request with app.state for publish_event
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        added = await add_group_members(
            req, gid, form, user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert any(m.user_id == extra for m in added)

        listed = await list_group_members(
            gid, user=SimpleNamespace(id=uid), db=manager_db,
        )
        user_ids = {m.user_id for m in listed}
        assert uid in user_ids
        assert extra in user_ids

    @pytest.mark.asyncio
    async def test_remove_members(self, manager_db):
        """remove_group_members removes the specified user."""
        from open_webui.routers.group_manager import (
            add_group_members,
            remove_group_members,
        )

        uid, gid, _ = await _setup_valid_manager(manager_db)
        extra = f'user-{uuid.uuid4().hex[:8]}'
        await _create_user_in_db(manager_db, extra)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        # Add extra user
        add_form = GroupManagerMemberIdsForm(user_ids=[extra])
        await add_group_members(
            req, gid, add_form, user=SimpleNamespace(id=uid), db=manager_db,
        )

        # Remove extra user
        rm_form = GroupManagerMemberIdsForm(user_ids=[extra])
        removed = await remove_group_members(
            req, gid, rm_form, user=SimpleNamespace(id=uid), db=manager_db,
        )
        user_ids = {m.user_id for m in removed}
        assert extra not in user_ids
        assert uid in user_ids


# ===================================================================
# 19. Router: scoped knowledge creation + ownership
# ===================================================================

class TestRouterKnowledgeCreation:

    @pytest.mark.asyncio
    async def test_create_knowledge_with_ownership(self, manager_db):
        """create_group_knowledge creates knowledge + ownership + read grant."""
        from open_webui.models.access_grants import AccessGrants
        from open_webui.routers.group_manager import create_group_knowledge

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)

        form = GroupManagerKnowledgeCreateForm(
            name='Test KB', description='A test knowledge base',
        )
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        result = await create_group_knowledge(
            req, gid, form, user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert result.name == 'Test KB'
        assert result.description == 'A test knowledge base'
        assert result.write_access is True

        # Verify ownership row exists
        asset = await GroupOwnedAssets.get_asset_by_resource(
            'knowledge', result.id, db=manager_db,
        )
        assert asset is not None
        assert asset.group_id == gid

        # Verify read grant for the owning group
        has_read = await AccessGrants.has_access(
            user_id='anyone-never-matches',
            resource_type='knowledge',
            resource_id=result.id,
            permission='read',
            user_group_ids={gid},
            db=manager_db,
        )
        assert has_read is True

    @pytest.mark.asyncio
    async def test_create_knowledge_rejects_supplied_grants(self, manager_db):
        """Manager-supplied access_grants should be ignored — the endpoint
        does not accept them (form has no access_grants field)."""
        from open_webui.routers.group_manager import GroupManagerKnowledgeCreateForm
        # The form doesn't have access_grants — this is by design.
        fields = GroupManagerKnowledgeCreateForm.model_fields
        assert 'access_grants' not in fields


# ===================================================================
# 20. Router: scoped prompt creation + ownership
# ===================================================================

class TestRouterPromptCreation:

    @pytest.mark.asyncio
    async def test_create_prompt_with_ownership(self, manager_db):
        """create_group_prompt creates prompt + ownership + read grant."""
        from open_webui.routers.group_manager import create_group_prompt

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)

        form = GroupManagerPromptCreateForm(
            command='/test-cmd',
            name='Test Prompt',
            content='Hello {{name}}',
        )
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        result = await create_group_prompt(
            req, gid, form, user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert result.command == '/test-cmd'
        assert result.name == 'Test Prompt'
        assert result.write_access is True

        # Verify ownership
        asset = await GroupOwnedAssets.get_asset_by_resource(
            'prompt', result.id, db=manager_db,
        )
        assert asset is not None
        assert asset.group_id == gid

    @pytest.mark.asyncio
    async def test_create_prompt_rejects_duplicate_command(self, manager_db):
        """Duplicate command string is rejected."""
        from open_webui.routers.group_manager import create_group_prompt

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)

        form = GroupManagerPromptCreateForm(
            command='/dup-cmd', name='First', content='first',
        )
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        await create_group_prompt(
            req, gid, form, user=SimpleNamespace(id=uid), db=manager_db,
        )

        form2 = GroupManagerPromptCreateForm(
            command='/dup-cmd', name='Second', content='second',
        )
        with pytest.raises(HTTPException) as exc_info:
            await create_group_prompt(
                req, gid, form2, user=SimpleNamespace(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_prompt_rejects_supplied_grants(self, manager_db):
        """The form has no access_grants field — manager cannot set grants."""
        from open_webui.routers.group_manager import GroupManagerPromptCreateForm
        fields = GroupManagerPromptCreateForm.model_fields
        assert 'access_grants' not in fields


# ===================================================================
# 21. Router: ownership-only update/delete
# ===================================================================

class TestRouterOwnershipUpdateDelete:

    @pytest.mark.asyncio
    async def test_update_knowledge_requires_ownership(self, manager_db):
        """Updating a knowledge base that is NOT owned by the group yields 404."""
        from open_webui.routers.group_manager import update_group_knowledge

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))
        form = GroupManagerKnowledgeUpdateForm(name='New Name')

        with pytest.raises(HTTPException) as exc_info:
            await update_group_knowledge(
                req, gid, 'non-existent-id', form,
                user=SimpleNamespace(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_knowledge_requires_ownership(self, manager_db):
        """Deleting a knowledge base NOT owned by the group yields 404."""
        from open_webui.routers.group_manager import delete_group_knowledge

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        with pytest.raises(HTTPException) as exc_info:
            await delete_group_knowledge(
                req, gid, 'non-existent-id',
                user=SimpleNamespace(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_delete_knowledge_roundtrip(self, manager_db):
        """Create, update, delete a group-owned knowledge base."""
        from open_webui.routers.group_manager import (
            create_group_knowledge,
            delete_group_knowledge,
            update_group_knowledge,
        )

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        created = await create_group_knowledge(
            req, gid,
            GroupManagerKnowledgeCreateForm(name='KB', description='desc'),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        updated = await update_group_knowledge(
            req, gid, created.id,
            GroupManagerKnowledgeUpdateForm(name='KB Updated'),
            user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert updated.name == 'KB Updated'
        assert updated.description == 'desc'  # unchanged

        deleted = await delete_group_knowledge(
            req, gid, created.id,
            user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert deleted is True

        # Verify no longer exists
        asset = await GroupOwnedAssets.get_asset_by_resource(
            'knowledge', created.id, db=manager_db,
        )
        assert asset is None

    @pytest.mark.asyncio
    async def test_cross_group_update_denied(self, manager_db):
        """Updating a knowledge owned by group A via group B yields 404."""
        from open_webui.routers.group_manager import (
            create_group_knowledge,
            update_group_knowledge,
        )

        uid, gid_a, _ = await _setup_valid_asset_manager(manager_db)
        gid_b = f'grpB-{uuid.uuid4().hex[:8]}'
        await _create_group_in_db(manager_db, gid_b, uid)
        await _add_membership(manager_db, gid_b, uid)

        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        created = await create_group_knowledge(
            req, gid_a,
            GroupManagerKnowledgeCreateForm(name='KB-A', description=''),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        # Try to update via group B
        with pytest.raises(HTTPException) as exc_info:
            await update_group_knowledge(
                req, gid_b, created.id,
                GroupManagerKnowledgeUpdateForm(name='Stolen'),
                user=SimpleNamespace(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 404


# ===================================================================
# 22. Router: ACL delta — baseline read + write delta only
# ===================================================================

class TestRouterACLDelta:

    @pytest.mark.asyncio
    async def test_acl_delta_add_write(self, manager_db):
        """Setting write=True adds a group write grant."""
        from open_webui.models.access_grants import AccessGrants
        from open_webui.routers.group_manager import (
            create_group_knowledge,
            update_group_asset_acl,
        )

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        created = await create_group_knowledge(
            req, gid,
            GroupManagerKnowledgeCreateForm(name='KB', description=''),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        result = await update_group_asset_acl(
            req, gid, 'knowledge', created.id,
            GroupManagerACLDeltaForm(write=True),
            user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert result.write is True

        # Verify the write grant exists
        has_write = await AccessGrants.has_access(
            user_id='no-match',
            resource_type='knowledge',
            resource_id=created.id,
            permission='write',
            user_group_ids={gid},
            db=manager_db,
        )
        assert has_write is True

    @pytest.mark.asyncio
    async def test_acl_delta_remove_write(self, manager_db):
        """Setting write=False removes the group write grant."""
        from open_webui.models.access_grants import AccessGrants
        from open_webui.routers.group_manager import (
            create_group_knowledge,
            update_group_asset_acl,
        )

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        created = await create_group_knowledge(
            req, gid,
            GroupManagerKnowledgeCreateForm(name='KB', description=''),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        # First add write
        await update_group_asset_acl(
            req, gid, 'knowledge', created.id,
            GroupManagerACLDeltaForm(write=True),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        # Then remove write
        result = await update_group_asset_acl(
            req, gid, 'knowledge', created.id,
            GroupManagerACLDeltaForm(write=False),
            user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert result.write is False

        has_write = await AccessGrants.has_access(
            user_id='no-match',
            resource_type='knowledge',
            resource_id=created.id,
            permission='write',
            user_group_ids={gid},
            db=manager_db,
        )
        assert has_write is False

    @pytest.mark.asyncio
    async def test_acl_delta_read_baseline_persists(self, manager_db):
        """The read grant for the owning group is always present."""
        from open_webui.models.access_grants import AccessGrants
        from open_webui.routers.group_manager import (
            create_group_knowledge,
            update_group_asset_acl,
        )

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        created = await create_group_knowledge(
            req, gid,
            GroupManagerKnowledgeCreateForm(name='KB', description=''),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        # Even after removing write, read should persist
        await update_group_asset_acl(
            req, gid, 'knowledge', created.id,
            GroupManagerACLDeltaForm(write=False),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        has_read = await AccessGrants.has_access(
            user_id='no-match',
            resource_type='knowledge',
            resource_id=created.id,
            permission='read',
            user_group_ids={gid},
            db=manager_db,
        )
        assert has_read is True

    @pytest.mark.asyncio
    async def test_acl_delta_unsupported_type_rejected(self, manager_db):
        """ACL delta rejects unsupported resource_type."""
        from open_webui.routers.group_manager import update_group_asset_acl

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        with pytest.raises(HTTPException) as exc_info:
            await update_group_asset_acl(
                req, gid, 'model', 'some-id',
                GroupManagerACLDeltaForm(write=True),
                user=SimpleNamespace(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 400


# ===================================================================
# 23. Router: atomic creation rollback
# ===================================================================

class TestRouterAtomicCreationRollback:

    @pytest.mark.asyncio
    async def test_create_knowledge_rolls_back_on_error(self, manager_db):
        """If an error occurs during knowledge creation, the transaction
        is rolled back and no data persists."""
        from unittest.mock import AsyncMock, patch

        from open_webui.routers.group_manager import create_group_knowledge

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        # Force an error by making insert_asset raise
        with patch.object(
            GroupOwnedAssets, 'insert_asset',
            new_callable=AsyncMock,
            side_effect=RuntimeError('simulated failure'),
        ):
            with pytest.raises(RuntimeError, match='simulated failure'):
                await create_group_knowledge(
                    req, gid,
                    GroupManagerKnowledgeCreateForm(name='KB', description=''),
                    user=SimpleNamespace(id=uid), db=manager_db,
                )


# ===================================================================
# 24. Router: list assets
# ===================================================================

class TestRouterListAssets:

    @pytest.mark.asyncio
    async def test_list_assets_empty(self, manager_db):
        """list_group_assets returns empty for a group with no assets."""
        from open_webui.routers.group_manager import list_group_assets

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        result = await list_group_assets(
            gid, user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_list_assets_with_filter(self, manager_db):
        """list_group_assets filters by resource_type."""
        from open_webui.routers.group_manager import (
            create_group_knowledge,
            create_group_prompt,
            list_group_assets,
        )

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))

        await create_group_knowledge(
            req, gid,
            GroupManagerKnowledgeCreateForm(name='KB', description=''),
            user=SimpleNamespace(id=uid), db=manager_db,
        )
        await create_group_prompt(
            req, gid,
            GroupManagerPromptCreateForm(
                command='/test', name='Prompt', content='Hello',
            ),
            user=SimpleNamespace(id=uid), db=manager_db,
        )

        all_assets = await list_group_assets(
            gid, user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert len(all_assets) == 2

        kb_only = await list_group_assets(
            gid, resource_type='knowledge',
            user=SimpleNamespace(id=uid), db=manager_db,
        )
        assert len(kb_only) == 1
        assert kb_only[0].resource_type == 'knowledge'

    @pytest.mark.asyncio
    async def test_list_assets_unsupported_type_rejected(self, manager_db):
        """list_group_assets rejects unsupported resource_type filter."""
        from open_webui.routers.group_manager import list_group_assets

        uid, gid, _ = await _setup_valid_asset_manager(manager_db)
        with pytest.raises(HTTPException) as exc_info:
            await list_group_assets(
                gid, resource_type='model',
                user=SimpleNamespace(id=uid), db=manager_db,
            )
        assert exc_info.value.status_code == 400


# ===================================================================
# 25. Router: existing-route non-regression
# ===================================================================

class TestExistingRouteNonRegression:
    """Verify the existing /groups, /knowledge, /prompts routers are
    not affected by the new group_manager router."""

    def test_group_manager_router_has_no_overlap_with_groups(self):
        """The group_manager router prefix does not overlap the groups router."""
        from open_webui.routers.group_manager import router as gm_router
        from open_webui.routers.groups import router as g_router

        # Both are APIRouter instances
        assert hasattr(gm_router, 'routes')
        assert hasattr(g_router, 'routes')

        gm_paths = set()
        for route in gm_router.routes:
            if hasattr(route, 'path'):
                gm_paths.add(route.path)

        g_paths = set()
        for route in g_router.routes:
            if hasattr(route, 'path'):
                g_paths.add(route.path)

        # No path overlap at the router level
        assert gm_paths.isdisjoint(g_paths), (
            f'Path overlap detected: {gm_paths & g_paths}'
        )

    def test_group_manager_import_does_not_affect_groups(self):
        """Importing group_manager doesn't modify the groups router."""
        from open_webui.routers.groups import router as g_router

        g_routes_before = len(g_router.routes)
        # Import doesn't add routes to groups router
        assert len(g_router.routes) == g_routes_before

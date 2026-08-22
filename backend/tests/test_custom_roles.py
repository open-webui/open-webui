"""Focused regression tests for the custom-role foundation (Phase 1).

Covers:
1. Custom-role reference format validation
2. Reserved-role invariants (admin, user, pending)
3. Fail-closed resolution for unknown/malformed/disabled roles
4. Permission isolation (custom roles do NOT inherit group permissions)
5. Lifecycle rules (create, list, update, deactivate)
6. Sparse / no-default permissions (missing leaves fixed false)
7. No group OR-merging for custom roles
8. JSON persistence round-trip
9. Invalid / inactive refs fail closed
10. Exact admin bypass (get_admin_user, has_permission)
11. has_permission with custom roles
12. role_name_exists
13. fill_missing_permissions
14. Permission validation (malformed, unknown, non-boolean, None)
15. Explicit True retention after normalize_permissions
16. Create rejects null; Update rejects explicit null but omits preserve
17. Catalog immutability (deep-copy safety)
18. Migration schema validation (c5a8d3e2f1b0)
19. Test isolation (savepoint rollback demonstrable)
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from open_webui.constants import ERROR_MESSAGES
from open_webui.models.custom_roles import (
    RESERVED_ROLE_NAMES,
    CustomRoleAssignForm,
    CustomRoleCreateForm,
    CustomRoles,
    CustomRoleUpdateForm,
    extract_custom_role_id,
    get_permission_catalog,
    is_custom_role_ref,
    make_custom_role_ref,
    normalize_permissions,
    normalize_role_name,
    validate_permissions,
    validate_role_name,
)
from open_webui.utils.access_control import (
    LEGACY_PERMISSION_ROLES,
    fill_missing_permissions,
)

# ===================================================================
# 1. Format validation
# ===================================================================


class TestCustomRoleRefFormat:

    def test_valid_ref(self):
        rid = str(uuid.uuid4())
        ref = f'custom:{rid}'
        assert is_custom_role_ref(ref) is True
        assert extract_custom_role_id(ref) == rid

    def test_malformed_prefix(self):
        assert is_custom_role_ref('custom:') is False
        assert is_custom_role_ref('custom:abc') is False
        assert is_custom_role_ref('custom:not-a-uuid') is False

    def test_not_custom_prefix(self):
        assert is_custom_role_ref('admin') is False
        assert is_custom_role_ref('user') is False
        assert is_custom_role_ref('pending') is False
        assert is_custom_role_ref('custom') is False

    def test_extract_none_for_invalid(self):
        assert extract_custom_role_id('admin') is None
        assert extract_custom_role_id('custom:garbage') is None

    def test_make_custom_role_ref(self):
        rid = str(uuid.uuid4())
        assert make_custom_role_ref(rid) == f'custom:{rid}'


# ===================================================================
# Permission catalog endpoint
# ===================================================================


class TestCustomRolePermissionCatalogEndpoint:

    @pytest.mark.asyncio
    async def test_returns_canonical_catalog_with_group_capabilities(self):
        from types import SimpleNamespace

        from open_webui.routers.custom_roles import get_custom_role_permission_catalog

        result = await get_custom_role_permission_catalog(user=SimpleNamespace(role='admin'))

        assert result == get_permission_catalog()
        assert set(result['groups']) == {
            'manage_members',
            'manage_assets',
            'manage_skills',
        }
        assert all(value is False for value in result['groups'].values())

    def test_endpoint_is_exact_admin_protected_and_precedes_role_id_route(self):
        from fastapi.routing import APIRoute
        from open_webui.routers.custom_roles import router
        from open_webui.utils.auth import get_admin_user

        routes = [route for route in router.routes if isinstance(route, APIRoute)]
        permission_route = next(route for route in routes if route.path == '/permissions')
        role_route = next(route for route in routes if route.path == '/{role_id}')

        assert get_admin_user in [dependency.call for dependency in permission_route.dependant.dependencies]
        assert router.routes.index(permission_route) < router.routes.index(role_route)


# ===================================================================
# 2. Reserved-role invariants
# ===================================================================


class TestReservedRoleInvariants:

    def test_reserved_set(self):
        assert RESERVED_ROLE_NAMES == {'admin', 'user', 'pending'}

    def test_validate_role_name_rejects_reserved(self):
        for name in ('admin', 'user', 'pending', 'Admin', 'USER', 'Pending'):
            with pytest.raises(ValueError, match='reserved'):
                validate_role_name(name)

    def test_validate_role_name_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_role_name('')

    def test_validate_role_name_rejects_long(self):
        with pytest.raises(ValueError, match='64'):
            validate_role_name('a' * 65)

    def test_validate_role_name_accepts_valid(self):
        assert validate_role_name('manager') == 'manager'
        assert validate_role_name('Team Lead') == 'team lead'
        assert validate_role_name('content-editor') == 'content-editor'
        assert validate_role_name('test_role_123') == 'test_role_123'

    def test_normalize_role_name(self):
        assert normalize_role_name('  Manager  ') == 'manager'
        assert normalize_role_name('Team   Lead') == 'team lead'


# ===================================================================
# 3. Fail-closed resolution
# ===================================================================


class TestFailClosedResolution:

    def test_unresolved_role_uses_catalog_shape(self):
        """Unresolved custom roles get a full-deny tree from the fixed
        server-owned catalog, not from the caller's default_permissions."""
        from open_webui.models.custom_roles import normalize_permissions

        catalog_result = normalize_permissions(None)

        def assert_all_false(d):
            for v in d.values():
                if isinstance(v, dict):
                    assert_all_false(v)
                else:
                    assert v is False

        assert_all_false(catalog_result)

    def test_caller_config_cannot_change_unresolved_shape(self):
        """Regression: even if DEFAULT_USER_PERMISSIONS is mutated, the
        unresolved custom-role fallback still uses the fixed catalog."""
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.custom_roles import (
            _PERMISSION_CATALOG,
            normalize_permissions,
        )

        snapshot = DEFAULT_USER_PERMISSIONS.copy()
        try:
            # Mutate the caller config to add a bogus top-level key
            DEFAULT_USER_PERMISSIONS['bogus_key'] = True  # type: ignore[assignment]
            DEFAULT_USER_PERMISSIONS['workspace'] = {'only_this': True}  # type: ignore[assignment]

            result = normalize_permissions(None)

            # The result must come from the catalog, not from the config
            assert 'bogus_key' not in result
            assert result == normalize_permissions(None)
            # Catalog structure is intact
            assert set(result.keys()) == set(_PERMISSION_CATALOG.keys())
        finally:
            DEFAULT_USER_PERMISSIONS.clear()
            DEFAULT_USER_PERMISSIONS.update(snapshot)

    @pytest.mark.asyncio
    async def test_unresolved_ref_yields_catalog_deny_tree(self, db):
        """End-to-end: a user with a non-existent custom role ref gets
        the fixed catalog all-false tree, not the caller's config shape."""
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.custom_roles import normalize_permissions
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())
        fake_ref = f'custom:{uuid.uuid4()}'

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Unknown Ref',
            role=fake_ref,
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)
        # Must match the fixed catalog deny tree, not the caller config shape
        assert perms == normalize_permissions(None)

    def test_legacy_permission_roles(self):
        assert LEGACY_PERMISSION_ROLES == {'user', 'pending'}


# ===================================================================
# 4. Database lifecycle (CRUD) — isolated via savepoints
# ===================================================================


@pytest.mark.asyncio
class TestCustomRoleLifecycle:

    async def test_create_role(self, db):

        form = CustomRoleCreateForm(
            name='manager',
            display_name='Manager',
            permissions={'workspace': {'models': True, 'knowledge': True}},
        )
        role = await CustomRoles.create_role(form, db=db)
        assert role is not None
        assert role.name == 'manager'
        assert role.display_name == 'Manager'
        assert role.active is True
        # Permissions are normalised to the full canonical tree on persist
        expected = normalize_permissions({'workspace': {'models': True, 'knowledge': True}})
        assert role.permissions == expected
        assert role.id

    async def test_create_duplicate_name_raises(self, db):
        await CustomRoles.create_role(
            CustomRoleCreateForm(name='editor', display_name='Editor'), db=db
        )
        with pytest.raises(ValueError, match='already exists'):
            await CustomRoles.create_role(
                CustomRoleCreateForm(name='editor', display_name='Editor Copy'), db=db
            )

    async def test_get_role_by_id(self, db):
        created = await CustomRoles.create_role(
            CustomRoleCreateForm(name='analyst', display_name='Analyst'), db=db
        )
        fetched = await CustomRoles.get_role_by_id(created.id, db=db)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == 'analyst'

    async def test_get_role_by_name(self, db):
        created = await CustomRoles.create_role(
            CustomRoleCreateForm(name='auditor', display_name='Auditor'), db=db
        )
        fetched = await CustomRoles.get_role_by_name('auditor', db=db)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_active_role_inactive_returns_none(self, db):
        created = await CustomRoles.create_role(
            CustomRoleCreateForm(name='disabled_role', display_name='Disabled'), db=db
        )
        await CustomRoles.deactivate_role(created.id, db=db)
        result = await CustomRoles.get_active_role_by_id(created.id, db=db)
        assert result is None

    async def test_list_roles(self, db):
        before = await CustomRoles.list_roles(db=db)
        before_count = before['total']
        for name in ('alpha', 'beta', 'gamma'):
            await CustomRoles.create_role(
                CustomRoleCreateForm(name=name, display_name=name.title()), db=db
            )
        result = await CustomRoles.list_roles(db=db)
        assert result['total'] == before_count + 3
        assert len(result['items']) == before_count + 3

    async def test_list_roles_exclude_inactive(self, db):
        await CustomRoles.create_role(
            CustomRoleCreateForm(name='active_only', display_name='Active'), db=db
        )
        r2 = await CustomRoles.create_role(
            CustomRoleCreateForm(name='inactive_one', display_name='Inactive'), db=db
        )
        await CustomRoles.deactivate_role(r2.id, db=db)

        result = await CustomRoles.list_roles(include_inactive=False, db=db)
        # The active_only role should appear in active list
        names = [r.name for r in result['items']]
        assert 'active_only' in names
        assert 'inactive_one' not in names

    async def test_update_role_display_name(self, db):
        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='updatable', display_name='Old Name'), db=db
        )
        updated = await CustomRoles.update_role(
            role.id, CustomRoleUpdateForm(display_name='New Name'), db=db
        )
        assert updated.display_name == 'New Name'
        assert updated.name == 'updatable'

    async def test_update_role_permissions(self, db):

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='perm_update', display_name='PermUpdate'), db=db
        )
        new_perms = {'workspace': {'models': True}}
        updated = await CustomRoles.update_role(
            role.id, CustomRoleUpdateForm(permissions=new_perms), db=db
        )
        assert updated.permissions == normalize_permissions(new_perms)

    async def test_deactivate_role(self, db):
        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='to_deactivate', display_name='ToDeactivate'), db=db
        )
        deactivated = await CustomRoles.deactivate_role(role.id, db=db)
        assert deactivated.active is False

    async def test_deactivate_resets_assigned_users_only(self, db):
        from open_webui.models.users import User
        from sqlalchemy import select

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='reset_on_deactivate', display_name='Reset'), db=db
        )
        unrelated = await CustomRoles.create_role(
            CustomRoleCreateForm(name='unrelated_role', display_name='Unrelated'), db=db
        )
        now = int(time.time())
        assigned_id = str(uuid.uuid4())
        unrelated_id = str(uuid.uuid4())
        assigned = User(
            id=assigned_id,
            email=f'{assigned_id}@test.local',
            name='Assigned',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        unaffected = User(
            id=unrelated_id,
            email=f'{unrelated_id}@test.local',
            name='Unaffected',
            role=f'custom:{unrelated.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add_all([assigned, unaffected])
        await db.flush()

        await CustomRoles.deactivate_role(role.id, db=db)

        rows = (
            await db.execute(select(User).where(User.id.in_([assigned_id, unrelated_id])))
        ).scalars().all()
        by_id = {row.id: row for row in rows}
        assert by_id[assigned_id].role == 'user'
        assert by_id[unrelated_id].role == f'custom:{unrelated.id}'

    async def test_delete_resets_assignments_and_is_safe_when_repeated(self, db):
        from open_webui.models.users import User

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='reset_on_delete', display_name='Delete Reset'), db=db
        )
        now = int(time.time())
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=f'{user_id}@test.local',
            name='Delete Assigned',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        deleted = await CustomRoles.delete_role(role.id, db=db)

        assert deleted.id == role.id
        assert await CustomRoles.get_role_by_id(role.id, db=db) is None
        refreshed = await db.get(User, user_id)
        assert refreshed.role == 'user'
        assert await CustomRoles.delete_role(role.id, db=db) is None

    async def test_failed_deactivation_rolls_back_role_and_user_reset(self, manager_db):
        from open_webui.models.users import User

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='rollback_deactivate', display_name='Rollback'), db=manager_db
        )
        now = int(time.time())
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=f'{user_id}@test.local',
            name='Rollback Assigned',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        manager_db.add(user)
        await manager_db.flush()
        await manager_db.commit()

        with patch.object(
            manager_db,
            'commit',
            new_callable=AsyncMock,
            side_effect=RuntimeError('commit failed'),
        ):
            with pytest.raises(RuntimeError, match='commit failed'):
                await CustomRoles.deactivate_role(role.id, db=manager_db)

        role_after = await CustomRoles.get_role_by_id(role.id, db=manager_db)
        user_after = await manager_db.get(User, user_id)
        assert role_after.active is True
        assert user_after.role == f'custom:{role.id}'

    async def test_failed_delete_rolls_back_role_and_user_reset(self, manager_db):
        from open_webui.models.users import User

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='rollback_delete', display_name='Rollback Delete'), db=manager_db
        )
        now = int(time.time())
        user_id = str(uuid.uuid4())
        manager_db.add(
            User(
                id=user_id,
                email=f'{user_id}@test.local',
                name='Rollback Delete Assigned',
                role=f'custom:{role.id}',
                profile_image_url='/user.png',
                last_active_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await manager_db.flush()
        await manager_db.commit()

        with patch.object(
            manager_db,
            'commit',
            new_callable=AsyncMock,
            side_effect=RuntimeError('commit failed'),
        ):
            with pytest.raises(RuntimeError, match='commit failed'):
                await CustomRoles.delete_role(role.id, db=manager_db)

        assert await CustomRoles.get_role_by_id(role.id, db=manager_db) is not None
        user_after = await manager_db.get(User, user_id)
        assert user_after.role == f'custom:{role.id}'


# ===================================================================
# Role lifecycle router
# ===================================================================


class TestCustomRoleLifecycleRouter:
    @pytest.mark.asyncio
    async def test_assign_endpoint_rejects_exact_admin_self_assignment(self, db):
        from types import SimpleNamespace

        from fastapi import HTTPException
        from open_webui.models.users import User
        from open_webui.routers.custom_roles import assign_custom_role

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='self_assignment', display_name='Self Assignment'), db=db
        )
        now = int(time.time())
        first_admin_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())
        for user_id, created_at in ((first_admin_id, now - 10), (admin_id, now)):
            db.add(
                User(
                    id=user_id,
                    email=f'{user_id}@test.local',
                    name='Admin',
                    role='admin',
                    profile_image_url='/user.png',
                    last_active_at=now,
                    created_at=created_at,
                    updated_at=now,
                )
            )
        await db.flush()

        with pytest.raises(HTTPException) as exc_info:
            await assign_custom_role(
                SimpleNamespace(),
                CustomRoleAssignForm(role_id=role.id, user_id=admin_id),
                user=SimpleNamespace(id=admin_id, role='admin'),
                db=db,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == ERROR_MESSAGES.ACTION_PROHIBITED
        assert (await db.get(User, admin_id)).role == 'admin'

    @pytest.mark.asyncio
    async def test_deactivate_endpoint_resets_users_and_emits_metadata_events(self, db, monkeypatch):
        from types import SimpleNamespace

        from open_webui.models.users import User
        from open_webui.routers.custom_roles import deactivate_custom_role

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='router_deactivate', display_name='Router Deactivate'), db=db
        )
        now = int(time.time())
        user_id = str(uuid.uuid4())
        db.add(
            User(
                id=user_id,
                email=f'{user_id}@test.local',
                name='Router Assigned',
                role=f'custom:{role.id}',
                profile_image_url='/user.png',
                last_active_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await db.flush()

        events = []

        async def capture_event(_request, event, **kwargs):
            events.append((event.name, kwargs.get('data')))

        monkeypatch.setattr('open_webui.routers.custom_roles.publish_event', capture_event)
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))
        admin = SimpleNamespace(id='admin', role='admin')

        result = await deactivate_custom_role(
            request,
            role.id,
            user=admin,
            db=db,
        )

        assert result.active is False
        assert (await db.get(User, user_id)).role == 'user'
        assert ('custom_role.deactivated', {'name': role.name, 'reset_to': 'user', 'reset_user_count': 1}) in events
        assert ('user.role_updated', {'role': 'user', 'reason': 'custom_role_deactivated'}) in events

    @pytest.mark.asyncio
    async def test_delete_endpoint_removes_role_resets_users_and_emits_event(self, db, monkeypatch):
        from types import SimpleNamespace

        from open_webui.models.users import User
        from open_webui.routers.custom_roles import delete_custom_role

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='router_delete', display_name='Router Delete'), db=db
        )
        now = int(time.time())
        user_id = str(uuid.uuid4())
        db.add(
            User(
                id=user_id,
                email=f'{user_id}@test.local',
                name='Router Delete Assigned',
                role=f'custom:{role.id}',
                profile_image_url='/user.png',
                last_active_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await db.flush()

        events = []

        async def capture_event(_request, event, **kwargs):
            events.append((event.name, kwargs.get('data')))

        monkeypatch.setattr('open_webui.routers.custom_roles.publish_event', capture_event)
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(instance_id='test')))
        admin = SimpleNamespace(id='admin', role='admin')

        result = await delete_custom_role(
            request,
            role.id,
            user=admin,
            db=db,
        )

        assert result.id == role.id
        assert await CustomRoles.get_role_by_id(role.id, db=db) is None
        assert (await db.get(User, user_id)).role == 'user'
        assert ('custom_role.deleted', {'name': role.name, 'reset_to': 'user', 'reset_user_count': 1}) in events
        assert ('user.role_updated', {'role': 'user', 'reason': 'custom_role_deleted'}) in events

    def test_lifecycle_routes_require_exact_admin(self):
        from fastapi.routing import APIRoute
        from open_webui.routers.custom_roles import router
        from open_webui.utils.auth import get_admin_user

        routes = [route for route in router.routes if isinstance(route, APIRoute)]
        lifecycle_routes = [
            route
            for route in routes
            if route.path in {'/{role_id}', '/{role_id}/deactivate'}
            and ('DELETE' in route.methods or route.path.endswith('/deactivate'))
        ]
        assert len(lifecycle_routes) == 2
        for route in lifecycle_routes:
            assert get_admin_user in [dependency.call for dependency in route.dependant.dependencies]


# ===================================================================
# 5. Permission isolation
# ===================================================================


@pytest.mark.asyncio
class TestPermissionIsolation:

    async def test_custom_role_permissions_used(self, db):
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='limited_user',
                display_name='Limited User',
                permissions={
                    'workspace': {'models': False, 'knowledge': True, 'prompts': False},
                    'chat': {'delete': False},
                },
            ),
            db=db,
        )

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Test User',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)
        assert perms['workspace']['models'] is False
        assert perms['workspace']['knowledge'] is True
        assert perms['chat']['delete'] is False

    async def test_disabled_custom_role_all_false(self, db):
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='disabled_perm',
                display_name='Disabled',
                permissions={'workspace': {'models': True}},
            ),
            db=db,
        )
        await CustomRoles.deactivate_role(role.id, db=db)

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Disabled User',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)

        def assert_all_false(d):
            for v in d.values():
                if isinstance(v, dict):
                    assert_all_false(v)
                else:
                    assert v is False

        assert_all_false(perms)


# ===================================================================
# 6. Sparse / no-default permissions: missing leaves fixed false
# ===================================================================


@pytest.mark.asyncio
class TestSparsePermissions:

    async def test_sparse_permissions_fill_missing_as_false(self, db):
        """A custom role that only sets workspace.models should have
        all other leaves set to False (fail-closed), not to config defaults."""
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='sparse_role',
                display_name='Sparse Role',
                permissions={
                    'workspace': {'models': True},
                    'features': {'web_search': True},
                },
            ),
            db=db,
        )

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Sparse User',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)

        # Specified leaves should be preserved
        assert perms['workspace']['models'] is True
        assert perms['features']['web_search'] is True

        # Unspecified leaves within the same group should be False
        # (filled by fill_missing_permissions from the schema, not from config defaults)
        assert perms['workspace']['knowledge'] is False
        assert perms['workspace']['prompts'] is False
        assert perms['chat']['delete'] is False

    async def test_empty_permissions_all_false(self, db):
        """A custom role with {} permissions should yield all-False."""
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='empty_perms',
                display_name='Empty Perms',
                permissions={},
            ),
            db=db,
        )

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Empty Perms User',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)

        def assert_all_false(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    assert_all_false(v)
                else:
                    assert v is False, f'{k} should be False'

        assert_all_false(perms)


# ===================================================================
# 7. No group OR-merging for custom roles
# ===================================================================


@pytest.mark.asyncio
class TestNoGroupMerge:

    async def test_custom_role_ignores_group_permissions(self, db):
        """Custom roles must NOT inherit or merge group permissions."""
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.groups import GroupForm, Groups
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions, has_permission

        now = int(time.time())
        uid = str(uuid.uuid4())

        # Create a group with permissive permissions
        group = await Groups.insert_new_group(
            uid,
            GroupForm(
                name='permissive_group',
                description='Permissive',
                permissions={'features': {'web_search': True}},
            ),
            db=db,
        )
        await Groups.add_users_to_group(group.id, user_ids=[uid], db=db)

        # Create a custom role that denies web_search
        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='deny_search',
                display_name='Deny Search',
                permissions={'features': {'web_search': False}},
            ),
            db=db,
        )

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='No Merge User',
            role=f'custom:{role.id}',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        # get_permissions should use ONLY the custom role, not the group
        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)
        assert perms['features']['web_search'] is False

        # has_permission should also use the custom role
        assert await has_permission(uid, 'features.web_search', DEFAULT_USER_PERMISSIONS, db=db) is False


# ===================================================================
# 8. JSON persistence round-trip
# ===================================================================


@pytest.mark.asyncio
class TestJsonPersistence:

    async def test_permissions_persist_as_json_string(self, db):
        """Verify that permissions dict round-trips through the DB as a
        JSON string and comes back correctly.  Stored value is the full
        canonical tree produced by normalize_permissions."""
        from sqlalchemy import text

        permissions = {
            'workspace': {'models': True, 'knowledge': False},
            'chat': {'delete': True, 'share': False},
            'features': {'web_search': True},
        }

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='json_test',
                display_name='JSON Test',
                permissions=permissions,
            ),
            db=db,
        )

        # Reload via ORM — should match the normalised canonical tree
        fetched = await CustomRoles.get_role_by_id(role.id, db=db)
        assert fetched is not None
        assert fetched.permissions == normalize_permissions(permissions)

        # Also verify the raw DB column is a JSON string (not binary, not pickled)
        result = await db.execute(
            text('SELECT permissions FROM custom_role WHERE id = :id'),
            {'id': role.id},
        )
        raw = result.scalar()
        assert isinstance(raw, str)
        assert '"models": true' in raw
        assert '"delete": true' in raw

    async def test_empty_permissions_persists(self, db):
        """{} is normalised to the full deny tree on persist."""

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='empty_json',
                display_name='Empty JSON',
                permissions={},
            ),
            db=db,
        )
        fetched = await CustomRoles.get_role_by_id(role.id, db=db)
        assert fetched is not None
        assert fetched.permissions == normalize_permissions({})

    async def test_null_permissions_rejected_on_create(self, db):
        """Explicit null permissions must be rejected by the create form."""
        with pytest.raises(ValueError, match='must not be null'):
            CustomRoleCreateForm(
                name='null_perms',
                display_name='Null Perms',
                permissions=None,
            )


# ===================================================================
# 9. Invalid / inactive refs fail closed
# ===================================================================


@pytest.mark.asyncio
class TestInvalidInactiveRefs:

    async def test_unknown_custom_role_ref_yields_empty_perms(self, db):
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())
        fake_ref = f'custom:{uuid.uuid4()}'

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Unknown Ref',
            role=fake_ref,
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)

        def assert_all_false(d):
            for v in d.values():
                if isinstance(v, dict):
                    assert_all_false(v)
                else:
                    assert v is False

        assert_all_false(perms)

    async def test_malformed_ref_yields_empty_perms(self, db):
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import get_permissions

        now = int(time.time())
        uid = str(uuid.uuid4())

        user = User(
            id=uid,
            email=f'{uid}@test.local',
            name='Malformed Ref',
            role='custom:not-a-valid-uuid',
            profile_image_url='/user.png',
            last_active_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()

        perms = await get_permissions(uid, DEFAULT_USER_PERMISSIONS, db=db)

        def assert_all_false(d):
            for v in d.values():
                if isinstance(v, dict):
                    assert_all_false(v)
                else:
                    assert v is False

        assert_all_false(perms)


# ===================================================================
# 10. Exact admin bypass
# ===================================================================


class TestExactAdminBypass:

    def test_get_admin_user_rejects_custom_role(self):
        """get_admin_user must only pass for role == 'admin'."""
        from fastapi import HTTPException
        from open_webui.utils.auth import get_admin_user

        # Simulate a non-admin user
        fake_user = AsyncMock()
        fake_user.role = f'custom:{uuid.uuid4()}'

        with pytest.raises(HTTPException) as exc_info:
            get_admin_user(user=fake_user)
        assert exc_info.value.status_code == 401

    def test_get_admin_user_passes_for_admin(self):
        from open_webui.utils.auth import get_admin_user

        fake_user = AsyncMock()
        fake_user.role = 'admin'

        result = get_admin_user(user=fake_user)
        assert result.role == 'admin'


# ===================================================================
# 11. has_permission with custom roles
# ===================================================================


@pytest.mark.asyncio
class TestHasPermissionCustomRole:

    async def test_admin_always_true(self, db):
        from open_webui.models.users import User
        from open_webui.utils.access_control import has_permission
        now = int(time.time())
        uid = str(uuid.uuid4())

        user = User(
            id=uid, email=f'{uid}@test.local', name='Admin',
            role='admin', profile_image_url='/user.png',
            last_active_at=now, created_at=now, updated_at=now,
        )
        db.add(user)
        await db.flush()

        assert await has_permission(uid, 'features.web_search', {}, db=db) is True

    async def test_custom_role_checks_only_role_perms(self, db):
        from open_webui.config import DEFAULT_USER_PERMISSIONS
        from open_webui.models.users import User
        from open_webui.utils.access_control import has_permission
        now = int(time.time())
        uid = str(uuid.uuid4())

        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='perm_test',
                display_name='Perm Test',
                permissions={'features': {'web_search': False, 'image_generation': True}},
            ),
            db=db,
        )

        user = User(
            id=uid, email=f'{uid}@test.local', name='Perm User',
            role=f'custom:{role.id}', profile_image_url='/user.png',
            last_active_at=now, created_at=now, updated_at=now,
        )
        db.add(user)
        await db.flush()

        assert await has_permission(uid, 'features.web_search', DEFAULT_USER_PERMISSIONS, db=db) is False
        assert await has_permission(uid, 'features.image_generation', DEFAULT_USER_PERMISSIONS, db=db) is True


# ===================================================================
# 12. role_name_exists
# ===================================================================


@pytest.mark.asyncio
class TestRoleNameExists:

    async def test_exists_after_create(self, db):
        await CustomRoles.create_role(
            CustomRoleCreateForm(name='check_exists', display_name='Check'), db=db
        )
        assert await CustomRoles.role_name_exists('check_exists', db=db) is True

    async def test_not_exists(self, db):
        assert await CustomRoles.role_name_exists('nonexistent_role_xyz', db=db) is False

    async def test_exclude_id(self, db):
        role = await CustomRoles.create_role(
            CustomRoleCreateForm(name='exclude_test', display_name='Exclude'), db=db
        )
        assert await CustomRoles.role_name_exists('exclude_test', exclude_id=role.id, db=db) is False
        assert await CustomRoles.role_name_exists('exclude_test', db=db) is True


# ===================================================================
# 13. fill_missing_permissions
# ===================================================================


class TestFillMissingPermissions:

    def test_fills_missing_leaves_with_template(self):
        perms = {'workspace': {'models': True}}
        template = {
            'workspace': {'models': False, 'knowledge': False, 'prompts': False},
            'chat': {'delete': True},
        }
        result = fill_missing_permissions(perms, template)
        assert result['workspace']['models'] is True  # kept
        assert result['workspace']['knowledge'] is False  # filled
        assert result['workspace']['prompts'] is False  # filled
        assert result['chat']['delete'] is True  # filled

    def test_no_mutation_of_template(self):
        """fill_missing_permissions must not mutate the default_permissions template."""
        perms = {'workspace': {'models': True}}
        template = {'workspace': {'models': False, 'knowledge': False}}
        import copy
        original_template = copy.deepcopy(template)
        fill_missing_permissions(perms, template)
        assert template == original_template


# ===================================================================
# 14. Permission validation (malformed, unknown, non-boolean, None)
# ===================================================================


class TestPermissionValidation:

    def test_rejects_none(self):
        with pytest.raises(ValueError, match='must be a dictionary'):
            validate_permissions(None)

    def test_rejects_list(self):
        with pytest.raises(ValueError, match='must be a dictionary'):
            validate_permissions([{'workspace': {'models': True}}])

    def test_rejects_string(self):
        with pytest.raises(ValueError, match='must be a dictionary'):
            validate_permissions('invalid')

    def test_rejects_unknown_top_level_key(self):
        with pytest.raises(ValueError, match='Unknown permission key: unknown_key'):
            validate_permissions({'unknown_key': True})

    def test_rejects_unknown_nested_key(self):
        with pytest.raises(ValueError, match='Unknown permission key: workspace.unknown_leaf'):
            validate_permissions({'workspace': {'unknown_leaf': True}})

    def test_rejects_non_boolean_leaf(self):
        with pytest.raises(ValueError, match='must be a boolean'):
            validate_permissions({'workspace': {'models': 'yes'}})

    def test_rejects_int_leaf(self):
        with pytest.raises(ValueError, match='must be a boolean'):
            validate_permissions({'workspace': {'models': 1}})

    def test_rejects_non_dict_intermediate(self):
        with pytest.raises(ValueError, match='must be a dict'):
            validate_permissions({'workspace': 'not_a_dict'})

    def test_empty_dict_is_valid(self):
        assert validate_permissions({}) == {}

    def test_valid_partial_doc(self):
        doc = {'workspace': {'models': True}, 'chat': {'delete': False}}
        assert validate_permissions(doc) == doc


# ===================================================================
# 15. Explicit True retention after normalize_permissions
# ===================================================================


class TestNormalizePermissions:

    def test_empty_input_returns_full_deny(self):
        from open_webui.models.custom_roles import get_permission_catalog
        result = normalize_permissions({})
        assert result == get_permission_catalog()

    def test_none_input_returns_full_deny(self):
        from open_webui.models.custom_roles import get_permission_catalog
        result = normalize_permissions(None)
        assert result == get_permission_catalog()

    def test_explicit_true_retained(self):
        result = normalize_permissions({'workspace': {'models': True}})
        assert result['workspace']['models'] is True

    def test_explicit_false_retained(self):
        result = normalize_permissions({'workspace': {'models': False}})
        assert result['workspace']['models'] is False

    def test_sparse_preserves_and_fills_false(self):
        doc = {'workspace': {'models': True}, 'features': {'web_search': True}}
        result = normalize_permissions(doc)
        assert result['workspace']['models'] is True
        assert result['features']['web_search'] is True
        assert result['workspace']['knowledge'] is False
        assert result['chat']['delete'] is False

    def test_non_mutating(self):
        doc = {'workspace': {'models': True}}
        original = {'workspace': {'models': True}}
        normalize_permissions(doc)
        assert doc == original

    def test_catalog_not_mutated(self):
        """Calling normalize_permissions must never mutate _PERMISSION_CATALOG."""
        import copy

        from open_webui.models.custom_roles import (
            _PERMISSION_CATALOG,
        )
        snapshot = copy.deepcopy(_PERMISSION_CATALOG)
        normalize_permissions({'workspace': {'models': True}})
        assert _PERMISSION_CATALOG == snapshot


# ===================================================================
# 16. Create rejects null; Update rejects explicit null but omits preserve
# ===================================================================


class TestNullPermissionsContract:

    def test_create_rejects_explicit_null(self):
        with pytest.raises(ValueError, match='must not be null'):
            CustomRoleCreateForm(
                name='null_create',
                display_name='Null Create',
                permissions=None,
            )

    def test_create_allows_omitted(self):
        """Omitting permissions defaults to {}."""
        form = CustomRoleCreateForm(
            name='omitted_create',
            display_name='Omitted Create',
        )
        assert form.permissions == {}

    def test_update_rejects_explicit_null(self):
        with pytest.raises(ValueError, match='must not be null'):
            CustomRoleUpdateForm(permissions=None)

    def test_update_allows_omitted(self):
        """Omitting permissions entirely → None (meaning preserve existing)."""
        form = CustomRoleUpdateForm(display_name='New Name')
        assert form.permissions is None

    @pytest.mark.asyncio
    async def test_update_omit_preserves_existing(self, db):
        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='omit_preserve',
                display_name='Preserve Me',
                permissions={'workspace': {'models': True}},
            ),
            db=db,
        )
        # Update display_name only — permissions should be unchanged
        updated = await CustomRoles.update_role(
            role.id,
            CustomRoleUpdateForm(display_name='Updated Name'),
            db=db,
        )
        assert updated.display_name == 'Updated Name'
        assert updated.permissions['workspace']['models'] is True
        assert updated.permissions['workspace']['knowledge'] is False


# ===================================================================
# 17. Catalog immutability (deep-copy safety)
# ===================================================================


class TestCatalogImmutability:

    def test_normalize_permissions_returns_deep_copy(self):
        """Two successive normalizations with different inputs must not
        interfere with each other."""

        r1 = normalize_permissions({'workspace': {'models': True}})
        r2 = normalize_permissions({'features': {'web_search': True}})

        assert r1['workspace']['models'] is True
        assert r1['features']['web_search'] is False
        assert r2['workspace']['models'] is False
        assert r2['features']['web_search'] is True

    def test_mutation_of_result_does_not_affect_catalog(self):
        from open_webui.models.custom_roles import (
            _PERMISSION_CATALOG,
        )
        result = normalize_permissions({'workspace': {'models': True}})
        result['workspace']['models'] = 'CORRUPTED'
        assert _PERMISSION_CATALOG['workspace']['models'] is False


# ===================================================================
# 18. Migration schema validation (c5a8d3e2f1b0)
# ===================================================================


@pytest.mark.asyncio
class TestMigrationSchema:

    async def test_custom_role_table_schema(self, db):
        """Verify the ``custom_role`` table has the expected columns,
        types, and nullability matching migration c5a8d3e2f1b0.

        Limitation: The test database is created via
        ``Base.metadata.create_all()`` (conftest), not via Alembic
        ``upgrade()``.  This test therefore verifies the ORM model's
        DDL matches the migration's intent, rather than proving the
        migration chain itself produces the correct schema.  A full
        Alembic upgrade test is impractical because ``env.py`` has
        complex module-level imports (``open_webui.env``, model
        registrations) that depend on the full application bootstrap.
        """
        from sqlalchemy import text

        def _check_schema(sync_conn):
            from open_webui.internal.db import Base

            metadata = Base.metadata
            # Table names may be prefixed (e.g. '.custom_role') depending
            # on DATABASE_SCHEMA; match by suffix.
            tables = set(metadata.tables.keys())
            custom_role_keys = [k for k in tables if k.endswith('custom_role')]
            assert custom_role_keys, f'custom_role table not found in {tables}'

            table = metadata.tables[custom_role_keys[0]]

            # Column presence
            cols = {c.name: c for c in table.columns}
            expected_cols = {
                'id', 'name', 'display_name', 'active',
                'permissions', 'created_at', 'updated_at',
            }
            assert set(cols.keys()) == expected_cols

            # permissions column: physical TEXT, NOT NULL
            perms = cols['permissions']
            assert str(perms.type) == 'TEXT'
            assert perms.nullable is False

            # active column: NOT NULL
            active = cols['active']
            assert active.nullable is False

            # Unique index on name
            idx_names = {idx.name for idx in table.indexes}
            assert 'ix_custom_role_name' in idx_names

            # Verify DDL presence via raw SQLite query
            row = sync_conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='custom_role'")
            ).fetchone()
            assert row is not None
            ddl = row[0]
            assert 'permissions' in ddl

        await db.run_sync(_check_schema)


# ===================================================================
# 18. Test isolation (savepoint rollback demonstrable)
# ===================================================================


@pytest.mark.asyncio
class TestCrossTestIsolation:

    async def test_commit_and_rollback_demonstrates_isolation(self, db):
        """Exercise a repository method that commits (via savepoint), then
        verify the outer transaction still rolls back cleanly.

        This test demonstrates that the savepoint isolation in conftest.py
        works correctly: ``session.commit()`` inside the repository only
        commits the nested savepoint; the outer transaction (and all its
        data) is rolled back when the fixture tears down.  A subsequent
        test therefore starts with a clean slate regardless of ordering.

        Limitation: we cannot prove a *different* test starts clean within
        a single test function.  The guarantee comes from the conftest
        ``db`` fixture which wraps every test in
        ``connection.begin() → session.begin_nested() → rollback()``.
        """
        # 1. Record the starting count
        before = await CustomRoles.list_roles(db=db)
        start_count = before['total']

        # 2. Exercise a repository method that commits internally
        role = await CustomRoles.create_role(
            CustomRoleCreateForm(
                name='isolation_sentinel',
                display_name='Isolation Sentinel',
                permissions={'workspace': {'models': True}},
            ),
            db=db,
        )
        assert role is not None

        # 3. Verify it's visible within this session (savepoint was committed)
        after_create = await CustomRoles.list_roles(db=db)
        assert after_create['total'] == start_count + 1
        fetched = await CustomRoles.get_role_by_id(role.id, db=db)
        assert fetched is not None
        assert fetched.name == 'isolation_sentinel'

        # 4. When this test returns, the ``db`` fixture rolls back the outer
        #    transaction, undoing all changes.  The *next* test to run will
        #    see the same starting state — no ordering dependency.

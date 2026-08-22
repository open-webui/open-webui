"""Custom role registry model, schemas, and database access layer.

Custom roles are stored as opaque ``custom:<uuid>`` references in the existing
``User.role`` column.  The registry provides the backing definition that maps
each opaque reference to a normalized name, display name, active flag, and
explicit permission set.

Invariants enforced here:
- Reserved role strings ``admin``, ``user``, ``pending`` may never be used as
  custom role names.
- Role IDs are immutable UUIDs generated at creation time.
- Role names are stored normalized (lowercased, stripped) and uniqueness is
  enforced.
- Permission documents are validated against a fixed server-owned catalog
  and normalized to a canonical full boolean tree (omissions are False).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import BigInteger, Boolean, Column, Index, Text, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESERVED_ROLE_NAMES: frozenset[str] = frozenset({'admin', 'user', 'pending'})

_CUSTOM_ROLE_PREFIX = 'custom:'
_CUSTOM_UUID_LENGTH = 36  # standard UUID4 length


# ---------------------------------------------------------------------------
# Server-owned permission catalog
# ---------------------------------------------------------------------------
# This is the SINGLE source of truth for the shape of a custom-role
# permission document.  All boolean leaves default to False (deny).
# Input validation rejects unknown keys; normalisation fills omissions
# with False.  This catalog does NOT derive from caller-supplied or
# configured defaults — it is fixed at import time.
# ---------------------------------------------------------------------------

_PERMISSION_CATALOG: dict[str, Any] = {
    'workspace': {
        'models': False,
        'knowledge': False,
        'prompts': False,
        'tools': False,
        'skills': False,
        'models_import': False,
        'models_export': False,
        'prompts_import': False,
        'prompts_export': False,
        'tools_import': False,
        'tools_export': False,
        'skills_import': False,
        'skills_export': False,
    },
    'sharing': {
        'models': False,
        'public_models': False,
        'knowledge': False,
        'public_knowledge': False,
        'prompts': False,
        'public_prompts': False,
        'tools': False,
        'public_tools': False,
        'skills': False,
        'public_skills': False,
        'notes': False,
        'public_notes': False,
        'folders': False,
        'public_chats': False,
        'open_chats': False,
        'public_calendars': False,
    },
    'access_grants': {
        'allow_users': False,
        'allow_groups': False,
    },
    'chat': {
        'controls': False,
        'valves': False,
        'system_prompt': False,
        'params': False,
        'file_upload': False,
        'web_upload': False,
        'delete': False,
        'delete_message': False,
        'continue_response': False,
        'regenerate_response': False,
        'rate_response': False,
        'edit': False,
        'share': False,
        'export': False,
        'import': False,
        'stt': False,
        'tts': False,
        'call': False,
        'multiple_models': False,
        'temporary': False,
        'temporary_enforced': False,
    },
    'features': {
        'api_keys': False,
        'notes': False,
        'folders': False,
        'channels': False,
        'direct_tool_servers': False,
        'web_search': False,
        'image_generation': False,
        'code_interpreter': False,
        'memories': False,
        'automations': False,
        'calendar': False,
        'webhooks': False,
    },
    'settings': {
        'interface': False,
    },
    'groups': {
        'manage_members': False,
        'manage_assets': False,
        'manage_skills': False,
    },
}


# ---------------------------------------------------------------------------
# Permission validation & normalisation
# ---------------------------------------------------------------------------


def _deep_merge(target: dict, source: dict) -> dict:
    """Recursively merge *source* into *target* (in-place) and return *target*.

    Leaf values in *source* always override the corresponding leaf in
    *target* so that an explicit ``True`` grant replaces the catalog
    default of ``False``.
    """
    for key, src_val in source.items():
        if key not in target:
            target[key] = src_val
        elif isinstance(src_val, dict) and isinstance(target[key], dict):
            _deep_merge(target[key], src_val)
        else:
            target[key] = src_val
    return target


def validate_permissions(doc: Any) -> dict[str, Any]:
    """Validate a raw permission document against the server-owned catalog.

    Rules:
    - *doc* must be a ``dict`` (not ``None``, not a list, not a scalar).
    - Intermediate nodes must be dicts.
    - All leaf values must be booleans (``True`` / ``False``).
    - No unknown top-level or nested keys are permitted.

    Raises ``ValueError`` on any violation.
    """
    if not isinstance(doc, dict):
        raise ValueError('Permissions must be a dictionary, not None or another type.')

    def _check(d: dict, catalog: dict, path: str = '') -> None:
        for key, value in d.items():
            full = f'{path}.{key}' if path else key
            if key not in catalog:
                raise ValueError(f'Unknown permission key: {full}')
            cat_val = catalog[key]
            if isinstance(cat_val, dict):
                if not isinstance(value, dict):
                    raise ValueError(
                        f'Permission {full} must be a dict, got {type(value).__name__}.'
                    )
                _check(value, cat_val, full)
            else:
                if not isinstance(value, bool):
                    raise ValueError(
                        f'Permission {full} must be a boolean, got {type(value).__name__}.'
                    )

    _check(doc, _PERMISSION_CATALOG)
    return doc


def normalize_permissions(doc: dict[str, Any] | None) -> dict[str, Any]:
    """Normalise a validated permission document to the full canonical tree.

    Returns a deep copy of ``_PERMISSION_CATALOG`` with overridden leaves
    from *doc*.  Missing leaves are ``False`` (fail-closed).  If *doc* is
    ``None`` or ``{}``, returns a full-deny tree.

    Uses ``copy.deepcopy`` so that the server-owned ``_PERMISSION_CATALOG``
    is never mutated.
    """
    import copy as _copy

    base = _copy.deepcopy(_PERMISSION_CATALOG)
    if not doc:
        return base

    _deep_merge(base, doc)
    return base


def get_permission_catalog() -> dict[str, Any]:
    """Return a deep copy of the server-owned permission catalog.

    Used by callers that need the canonical shape (e.g. test assertions,
    API responses showing available permissions).
    """
    import copy
    return copy.deepcopy(_PERMISSION_CATALOG)


# ---------------------------------------------------------------------------
# Role name helpers
# ---------------------------------------------------------------------------


def is_custom_role_ref(role: str) -> bool:
    """Return True if *role* is a well-formed ``custom:<uuid>`` reference."""
    if not role.startswith(_CUSTOM_ROLE_PREFIX):
        return False
    role_id = role[len(_CUSTOM_ROLE_PREFIX):]
    if len(role_id) != _CUSTOM_UUID_LENGTH:
        return False
    try:
        uuid.UUID(role_id)
        return True
    except ValueError:
        return False


def extract_custom_role_id(role: str) -> str | None:
    """Return the UUID portion of a ``custom:<uuid>`` reference, or None."""
    if is_custom_role_ref(role):
        return role[len(_CUSTOM_ROLE_PREFIX):]
    return None


def make_custom_role_ref(role_id: str) -> str:
    """Build a ``custom:<uuid>`` string from a raw UUID."""
    return f'{_CUSTOM_ROLE_PREFIX}{role_id}'


def normalize_role_name(name: str) -> str:
    """Lowercase, strip, and collapse whitespace for uniqueness checks."""
    return re.sub(r'\s+', ' ', name.strip().lower())


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r'^[a-z0-9]([a-z0-9_ -]*[a-z0-9])?$', re.IGNORECASE)


def validate_role_name(name: str) -> str:
    normalized = normalize_role_name(name)
    if not normalized:
        raise ValueError('Role name must not be empty.')
    if len(normalized) > 64:
        raise ValueError('Role name must be 64 characters or fewer.')
    if not _NAME_RE.match(normalized):
        raise ValueError(
            'Role name may only contain letters, digits, spaces, hyphens, '
            'and underscores, and must start and end with a letter or digit.'
        )
    if normalized in RESERVED_ROLE_NAMES:
        raise ValueError(
            f"'{normalized}' is a reserved role name and cannot be used for custom roles."
        )
    return normalized


# ---------------------------------------------------------------------------
# DB Schema
# ---------------------------------------------------------------------------


class CustomRole(Base):
    __tablename__ = 'custom_role'

    id = Column(Text, primary_key=True, unique=True, nullable=False)
    name = Column(Text, nullable=False, unique=True)
    display_name = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    permissions = Column(JSONField(), nullable=False, default=dict)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('ix_custom_role_name', 'name', unique=True),
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CustomRoleModel(BaseModel):
    """Pydantic schema for a custom role row."""

    id: str
    name: str
    display_name: str
    active: bool = True
    permissions: dict[str, Any]
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class CustomRoleCreateForm(BaseModel):
    """Admin form for creating a new custom role."""

    name: str
    display_name: str
    permissions: dict[str, Any] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_role_name(v)

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Display name must not be empty.')
        if len(v) > 128:
            raise ValueError('Display name must be 128 characters or fewer.')
        return v

    @field_validator('permissions', mode='before')
    @classmethod
    def validate_permissions_field(cls, v: Any) -> dict[str, Any]:
        if v is None:
            raise ValueError(
                'Permissions must not be null. '
                'Provide a permission dictionary (can be empty {}).'
            )
        if not isinstance(v, dict):
            raise ValueError('Permissions must be a dictionary.')
        validate_permissions(v)
        return v


class CustomRoleUpdateForm(BaseModel):
    """Admin form for updating an existing custom role.

    Only ``display_name``, ``active``, and ``permissions`` are mutable.
    Omitting ``permissions`` (not present in the request body) preserves
    the existing value.  Explicitly sending ``null`` is rejected.
    """

    display_name: str | None = None
    active: bool | None = None
    permissions: dict[str, Any] | None = None

    @model_validator(mode='before')
    @classmethod
    def reject_explicit_permissions_null(cls, data: Any) -> Any:
        """Distinguish 'field omitted' from 'field explicitly null'.

        If the raw input contains the key ``permissions`` with a ``None``
        value we reject it.  When the key is absent Pydantic uses the
        field default ``None`` which means 'omit / preserve existing'.
        """
        if isinstance(data, dict) and 'permissions' in data and data['permissions'] is None:
            raise ValueError(
                'Permissions must not be null. '
                'Omit the field to preserve existing permissions, '
                'or provide a permission dictionary.'
            )
        return data

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError('Display name must not be empty.')
        if len(v) > 128:
            raise ValueError('Display name must be 128 characters or fewer.')
        return v

    @field_validator('permissions', mode='before')
    @classmethod
    def validate_permissions_field(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError('Permissions must be a dictionary.')
        validate_permissions(v)
        return v


class CustomRoleResponse(BaseModel):
    """API response for a single custom role."""

    id: str
    name: str
    display_name: str
    active: bool
    permissions: dict[str, Any]
    created_at: int
    updated_at: int


class CustomRoleListResponse(BaseModel):
    items: list[CustomRoleResponse]
    total: int


class CustomRoleAssignForm(BaseModel):
    """Admin form for assigning a custom role to a user."""

    user_id: str
    role_id: str  # the UUID of the custom role


# ---------------------------------------------------------------------------
# Table access class
# ---------------------------------------------------------------------------


class CustomRolesTable:
    """Async database access methods for the ``custom_role`` table."""

    async def create_role(
        self,
        form: CustomRoleCreateForm,
        db: AsyncSession | None = None,
    ) -> CustomRoleModel | None:
        """Insert a new custom role.  Raises ValueError on name collision."""
        normalized = normalize_role_name(form.name)

        async with get_async_db_context(db) as session:
            # Check uniqueness
            existing = await session.execute(
                select(CustomRole).where(CustomRole.name == normalized)
            )
            if existing.scalars().first():
                raise ValueError(f"A custom role named '{normalized}' already exists.")

            now = int(time.time())
            role_id = str(uuid.uuid4())

            row = CustomRole(
                id=role_id,
                name=normalized,
                display_name=form.display_name.strip(),
                active=True,
                permissions=normalize_permissions(form.permissions),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return CustomRoleModel.model_validate(row)

    async def get_role_by_id(
        self,
        role_id: str,
        db: AsyncSession | None = None,
        *,
        for_update: bool = False,
    ) -> CustomRoleModel | None:
        async with get_async_db_context(db) as session:
            if for_update:
                result = await session.execute(
                    select(CustomRole).where(CustomRole.id == role_id).with_for_update()
                )
                row = result.scalars().first()
            else:
                row = await session.get(CustomRole, role_id)
            return CustomRoleModel.model_validate(row) if row else None

    async def get_role_by_name(
        self,
        name: str,
        db: AsyncSession | None = None,
    ) -> CustomRoleModel | None:
        normalized = normalize_role_name(name)
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(CustomRole).where(CustomRole.name == normalized)
            )
            row = result.scalars().first()
            return CustomRoleModel.model_validate(row) if row else None

    async def get_active_role_by_id(
        self,
        role_id: str,
        db: AsyncSession | None = None,
        *,
        for_update: bool = False,
    ) -> CustomRoleModel | None:
        """Return the role only if it exists AND is active (fail-closed)."""
        role = await self.get_role_by_id(role_id, db=db, for_update=for_update)
        if role and role.active:
            return role
        return None

    async def list_roles(
        self,
        *,
        include_inactive: bool = False,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        async with get_async_db_context(db) as session:
            stmt = select(CustomRole)
            if not include_inactive:
                stmt = stmt.where(CustomRole.active == True)  # noqa: E712

            # Count before pagination
            count_result = await session.execute(
                select(func.count()).select_from(stmt.subquery())
            )
            total = count_result.scalar() or 0

            stmt = stmt.order_by(CustomRole.name).offset(skip).limit(limit)
            result = await session.execute(stmt)
            roles = result.scalars().all()
            return {
                'items': [CustomRoleModel.model_validate(r) for r in roles],
                'total': total,
            }

    async def update_role(
        self,
        role_id: str,
        form: CustomRoleUpdateForm,
        db: AsyncSession | None = None,
    ) -> CustomRoleModel | None:
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(CustomRole).where(CustomRole.id == role_id).with_for_update()
            )
            row = result.scalars().first()
            if not row:
                return None

            now = int(time.time())
            updates: dict[str, Any] = {'updated_at': now}

            if form.display_name is not None:
                updates['display_name'] = form.display_name.strip()
            if form.active is not None:
                updates['active'] = form.active
            if form.permissions is not None:
                updates['permissions'] = normalize_permissions(form.permissions)

            try:
                await session.execute(
                    update(CustomRole).where(CustomRole.id == role_id).values(**updates)
                )
                if form.active is False:
                    await self._reset_assigned_users(session, role_id, now)
                await session.commit()
            except BaseException:
                if session.in_transaction():
                    await session.rollback()
                raise

            # Re-fetch to return fresh state
            row = await session.get(CustomRole, role_id)
            return CustomRoleModel.model_validate(row) if row else None

    async def deactivate_role(
        self,
        role_id: str,
        db: AsyncSession | None = None,
    ) -> CustomRoleModel | None:
        """Deactivate and reset all assignments to the legacy ``user`` role."""
        return await self.update_role(
            role_id,
            CustomRoleUpdateForm(active=False),
            db=db,
        )

    async def get_assigned_user_ids(
        self,
        role_id: str,
        db: AsyncSession | None = None,
    ) -> list[str]:
        """Return users currently carrying the opaque reference for *role_id*."""
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(User.id).where(User.role == make_custom_role_ref(role_id))
            )
            return list(result.scalars().all())

    async def _reset_assigned_users(
        self,
        session: AsyncSession,
        role_id: str,
        now: int,
    ) -> int:
        """Reset exact custom-role references without touching other roles."""
        from open_webui.models.users import User

        result = await session.execute(
            update(User)
            .where(User.role == make_custom_role_ref(role_id))
            .values(role='user', updated_at=now)
        )
        return int(getattr(result, 'rowcount', 0) or 0)

    async def delete_role(
        self,
        role_id: str,
        db: AsyncSession | None = None,
    ) -> CustomRoleModel | None:
        """Delete a role and atomically reset all of its assignments to ``user``."""
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(CustomRole).where(CustomRole.id == role_id).with_for_update()
            )
            row = result.scalars().first()
            if not row:
                return None

            role = CustomRoleModel.model_validate(row)
            try:
                await self._reset_assigned_users(session, role_id, int(time.time()))
                await session.delete(row)
                await session.commit()
            except BaseException:
                if session.in_transaction():
                    await session.rollback()
                raise

            return role

    async def role_name_exists(
        self,
        name: str,
        exclude_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> bool:
        normalized = normalize_role_name(name)
        async with get_async_db_context(db) as session:
            stmt = select(func.count()).select_from(CustomRole).where(
                CustomRole.name == normalized
            )
            if exclude_id:
                stmt = stmt.where(CustomRole.id != exclude_id)
            result = await session.execute(stmt)
            return (result.scalar() or 0) > 0


CustomRoles = CustomRolesTable()

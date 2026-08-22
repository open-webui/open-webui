"""Group-manager authorization service.

Provides ``require_group_manager`` which verifies that a user holds the
appropriate custom-role capability (``groups.manage_members`` or
``groups.manage_assets``), is a current member of the target group, and
the group exists.

Transaction boundary
--------------------
All calls to ``require_group_manager`` **must** occur inside a
``group_manager_tx`` context manager.  The context manager is the
**sole owner** of the authorization-plus-mutation transaction:

1. It **rejects** sessions already in a transaction (the caller must
   pass a fresh session).
2. It **starts the transaction**: for SQLite, issues ``BEGIN IMMEDIATE``
   as the *first* SQL statement on a fresh session; for PostgreSQL, uses
   ``session.begin()``.
3. It **commits** on success or **rolls back** on error.
4. The boundary marker is cleared only *after* the transaction is closed.

On **PostgreSQL**, ``BEGIN`` (the default) combined with
``SELECT ... FOR UPDATE`` acquires **row-level locks** — only the
specific rows touched by the authorization query are locked, and other
transactions can still read and write unrelated rows.

On **SQLite**, ``BEGIN IMMEDIATE`` acquires the **database-wide write
lock** at the start of the transaction.  No other connection can write
until this transaction commits or rolls back.  This is SQLite's native
serialization mechanism — it is **not** equivalent to Postgres row-level
locks, but it provides the same linearizability guarantee for the
authorization-then-mutation unit.

Locking order (stable, both backends)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Rows are locked in a deterministic order to prevent deadlocks:

    CustomRole → User → GroupMember → Group

On PostgreSQL each ``SELECT ... FOR UPDATE`` acquires an exclusive row
lock.  On SQLite the ``BEGIN IMMEDIATE`` write lock already serialises
all writers, so ``FOR UPDATE`` is a no-op that documents intent only.

No internal sessions, commits, or flushes are performed by
``require_group_manager`` itself — it only reads.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Boundary token (ContextVar-based, caller-writable-proof)
# ------------------------------------------------------------------


class _TxToken:
    """Opaque token proving entry into ``group_manager_tx``.

    Created only inside ``group_manager_tx`` and bound to both the
    exact ``AsyncSession`` object **and** the exact
    ``AsyncSessionTransaction`` object via identity (``is``).  A caller
    who sets ``session.info[_GM_TX_BOUNDARY] = True`` manually does
    **not** hold a token, so ``_check_boundary`` rejects the call.

    The token intentionally stores object references rather than
    ``id()`` integers so the comparison is immune to id-reuse after
    garbage collection.  The ContextVar ``reset()`` in the finally
    block drops these references deterministically, preventing any
    reference cycle from persisting beyond the context lifetime.
    """

    __slots__ = ('_session_ref', '_tx_ref')

    def __init__(self, session: AsyncSession, tx: Any) -> None:
        # Store live object references; compare by ``is``.
        self._session_ref = session
        self._tx_ref = tx

    def matches(self, session: AsyncSession) -> bool:
        """Return ``True`` only when the token was created for *session*
        **and** the session's current transaction is the exact same
        object that was active when the token was minted."""
        if self._session_ref is not session:
            return False
        if not session.in_transaction():
            return False
        tx = session.get_transaction()
        if tx is None:
            return False
        return self._tx_ref is tx


# Per-async-context boundary token.  ``None`` when not inside
# ``group_manager_tx``.  Caller code cannot forge this — only
# ``group_manager_tx`` sets/clears it.
_boundary_ctx: ContextVar[_TxToken | None] = ContextVar(
    '_boundary_ctx', default=None,
)

# Diagnostics key in ``session.info`` — set/cleared by the context
# manager for debugging but **never** used as authorization proof.
_GM_TX_BOUNDARY: str = '_GM_TX_BOUNDARY'


class GroupManagerError(Exception):
    """Raised when group-manager authorization fails.

    Attributes:
        reason: short machine-readable tag
        detail: human-readable explanation
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


# ------------------------------------------------------------------
# Transaction boundary context manager
# ------------------------------------------------------------------


@asynccontextmanager
async def group_manager_tx(db: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Scoped transaction boundary for group-manager operations.

    This is the **sole owner** of the authorization-plus-mutation
    transaction.  It performs three things:

    1. **Rejects** sessions that are already in a transaction — the
       caller must pass a fresh session.
    2. **Starts the transaction**: for SQLite, issues ``BEGIN IMMEDIATE``
       as the *first* SQL statement on a fresh session (not after
       ``session.begin()`` or a deferred query); for PostgreSQL, uses
       ``async with session.begin()``.
    3. **Establishes a ContextVar token** that proves
       ``require_group_manager`` is called from *this* context manager
       with *this exact session*.

    On **success** the context manager commits the transaction; on
    **error** it rolls back.  The boundary token is cleared only
    *after* the transaction is closed.

    Usage::

        async with group_manager_tx(db):
            await require_group_manager(uid, gid, 'groups.manage_members', db)
            # … perform mutations …
        # transaction is committed (or rolled back on error)
    """
    from sqlalchemy import text

    # ── 0. Reject session already in transaction ─────────────────────
    if db.in_transaction():
        raise GroupManagerError(
            'tx_boundary_missing',
            'group_manager_tx() requires a fresh session not already in '
            'a transaction.  Do not nest transactions — pass a fresh '
            'session to this context manager.',
        )

    # ── 1. Detect backend ────────────────────────────────────────────
    is_sqlite = db.bind is not None and db.bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: issue BEGIN IMMEDIATE as the first SQL on the fresh
        # session.  This acquires the database-wide write lock *before*
        # any authorization reads, serialising the entire
        # authorization-then-mutation unit.
        await db.execute(text('BEGIN IMMEDIATE'))
    else:
        # PostgreSQL: use session.begin() which issues BEGIN (the
        # default).  Row-level locks are acquired via SELECT … FOR
        # UPDATE inside require_group_manager.
        await db.begin()

    # ── 2. Establish boundary token (only after BEGIN success) ───────
    tx_obj = db.get_transaction()
    token = _TxToken(db, tx_obj)
    reset_token = _boundary_ctx.set(token)
    db.info[_GM_TX_BOUNDARY] = True  # diagnostics only, never auth proof

    try:
        yield db
    except BaseException:
        # On error (including asyncio.CancelledError which is a
        # BaseException), rollback the transaction before clearing
        # the token so no lock or partial state leaks.
        if db.in_transaction():
            await db.rollback()
        raise
    else:
        # On success, commit the transaction.  If the commit itself
        # fails, attempt rollback before re-raising (P1.8: commit
        # failure must be handled like body failure).
        if db.in_transaction():
            try:
                await db.commit()
            except BaseException:
                if db.in_transaction():
                    await db.rollback()
                raise
    finally:
        # Restore the ContextVar to its prior value (any outer
        # context), rather than blindly setting None.  This is
        # correct even when there is no outer context because
        # ``reset`` restores the default.
        _boundary_ctx.reset(reset_token)
        db.info.pop(_GM_TX_BOUNDARY, None)


def _check_boundary(db: AsyncSession) -> None:
    """Raise if the session is not inside a ``group_manager_tx`` boundary.

    Authorization requires **all** of:

    1. A ``_TxToken`` exists in the current async-context (set only by
       ``group_manager_tx``).
    2. The token was created for *this exact session* (identity check).
    3. The token was created for *this exact transaction* — so a child
       task that outlives the parent context, or any stale-token
       reuse, is rejected.
    4. The session has an active (owned) transaction.

    Manually setting ``session.info[_GM_TX_BOUNDARY] = True`` does **not**
    satisfy condition (1), so it never authorizes access.
    """
    token = _boundary_ctx.get(None)
    if token is None or not token.matches(db):
        raise GroupManagerError(
            'tx_boundary_missing',
            'require_group_manager() must be called inside a group_manager_tx() '
            'context manager with the same session and transaction.  Setting '
            'session.info directly does not authorize access.',
        )
    if not db.in_transaction():
        raise GroupManagerError(
            'tx_boundary_missing',
            'require_group_manager() requires an active transaction.  '
            'The group_manager_tx() context manager owns the transaction.',
        )


# ------------------------------------------------------------------
# Capability check
# ------------------------------------------------------------------


def _check_capability(capability: str, custom_perms: dict[str, Any]) -> None:
    """Verify a ``groups.*`` capability leaf is ``True`` in the normalised perms.

    Raises ``GroupManagerError`` if the capability is missing, not a bool,
    or not exactly ``True``.
    """
    from open_webui.models.custom_roles import normalize_permissions

    normalized = normalize_permissions(custom_perms)
    capability_parts = capability.split('.')
    node: Any = normalized
    for part in capability_parts:
        if not isinstance(node, dict) or part not in node:
            raise GroupManagerError(
                'capability_denied',
                f'Permission leaf {capability!r} is not present or not True.',
            )
        node = node[part]

    if node is not True:
        raise GroupManagerError(
            'capability_denied',
            f'Permission leaf {capability!r} is not True (got {node!r}).',
        )


# ------------------------------------------------------------------
# Main authorization entry point
# ------------------------------------------------------------------


async def require_group_manager(  # noqa: C901
    user_id: str,
    group_id: str,
    capability: str,
    db: AsyncSession,
) -> None:
    """Verify the user is an authorized group manager for the given capability.

    Parameters
    ----------
    user_id:
        The authenticated user's ID.
    group_id:
        The target group ID.
    capability:
        A fixed ``groups.*`` permission leaf, e.g.
        ``groups.manage_members`` or ``groups.manage_assets``.
    db:
        An active ``AsyncSession``.  All reads use this session; no
        commits or flushes are performed.

    .. important::

        This function **must** be called inside a ``group_manager_tx``
        context manager.  Calls outside the boundary raise
        ``GroupManagerError`` with reason ``tx_boundary_missing``.

    Raises
    ------
    GroupManagerError
        If any check fails.  The ``reason`` field is one of:
        ``tx_boundary_missing``, ``invalid_capability``,
        ``admin_denied``, ``legacy_role_denied``, ``user_not_found``,
        ``invalid_custom_role``, ``not_a_member``, ``group_not_found``,
        ``group_inactive``, ``capability_denied``.
    """
    # ── 0. Enforce transaction boundary ─────────────────────────────
    _check_boundary(db)

    # ── 1. Validate the capability string itself ─────────────────────
    from open_webui.models.custom_roles import _PERMISSION_CATALOG

    capability_parts = capability.split('.')
    if len(capability_parts) != 2 or capability_parts[0] != 'groups':
        raise GroupManagerError(
            'invalid_capability',
            f'{capability!r} is not a recognised groups.* capability. '
            f'Valid: groups.{sorted(_PERMISSION_CATALOG.get("groups", {}))}',
        )
    groups_catalog = _PERMISSION_CATALOG.get('groups', {})
    if capability_parts[1] not in groups_catalog:
        raise GroupManagerError(
            'invalid_capability',
            f'{capability!r} is not a recognised groups.* capability. '
            f'Valid: groups.{sorted(groups_catalog)}',
        )

    # ── 2. Read User role without locking to identify the CustomRole ──
    from open_webui.models.users import User

    user_result = await db.execute(
        select(User.id, User.role).where(User.id == user_id)
    )
    user_row = user_result.first()
    if user_row is None:
        raise GroupManagerError('user_not_found', f'User {user_id!r} not found.')

    user_role = user_row.role

    # ── 3. Admin and legacy roles are denied on this service ─────────
    from open_webui.utils.access_control import LEGACY_PERMISSION_ROLES

    if user_role == 'admin':
        raise GroupManagerError(
            'admin_denied',
            'Admin users cannot use the scoped group-manager service. '
            'Use the admin router instead.',
        )
    if user_role in LEGACY_PERMISSION_ROLES:
        raise GroupManagerError(
            'legacy_role_denied',
            f'Legacy role {user_role!r} does not carry group-manager authority. '
            'Assign a custom role with the required groups.* capability.',
        )

    # ── 4. Lock CustomRole row (stable order: first) ─────────────────
    from open_webui.models.custom_roles import (
        CustomRole,
        CustomRoleModel,
        extract_custom_role_id,
    )

    role_id = extract_custom_role_id(user_role)
    if role_id is None:
        raise GroupManagerError(
            'invalid_custom_role',
            f'Custom role reference {user_role!r} is malformed.',
        )

    role_result = await db.execute(
        select(CustomRole).where(
            CustomRole.id == role_id,
            CustomRole.active.is_(True),
        ).with_for_update()
    )
    role_row = role_result.scalars().first()
    if role_row is None:
        raise GroupManagerError(
            'invalid_custom_role',
            f'Custom role reference {user_role!r} could not be resolved '
            '(unknown, inactive, or disabled).',
        )

    custom_perms = CustomRoleModel.model_validate(role_row).permissions

    # Lock the user only after the role.  Custom-role assignment and
    # deactivation use the same CustomRole → User order.  Re-check the
    # reference after locking so a concurrent legacy/user-role update cannot
    # authorize against the unlocked snapshot above.
    locked_user_result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    locked_user_row = locked_user_result.scalars().first()
    if locked_user_row is None:
        raise GroupManagerError('user_not_found', f'User {user_id!r} not found.')
    if locked_user_row.role != user_role:
        raise GroupManagerError(
            'invalid_custom_role',
            f'User {user_id!r} changed roles during authorization.',
        )

    # ── 5. Normalise and check the capability leaf (P1.4: is True) ──
    _check_capability(capability, custom_perms)

    # ── 6. Lock GroupMember row (stable order: third) ───────────────
    from open_webui.models.groups import Group, GroupMember

    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        ).with_for_update()
    )
    if member_result.scalars().first() is None:
        raise GroupManagerError(
            'not_a_member',
            f'User {user_id!r} is not a member of group {group_id!r}.',
        )

    # ── 7. Lock Group row (stable order: fourth) ────────────────────
    group_result = await db.execute(
        select(Group).where(Group.id == group_id).with_for_update()
    )
    group_row = group_result.scalars().first()
    if group_row is None:
        raise GroupManagerError(
            'group_not_found',
            f'Group {group_id!r} not found.',
        )
    # Groups have no explicit 'active' flag; existence implies active.
    # If a future schema adds an active flag, check it here.

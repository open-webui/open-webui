"""Add admin analytics permissions to stored config and groups

Revision ID: f8a9b0c1d2e3
Revises: f1e2d3c4b5a6
Create Date: 2026-05-18 12:00:00.000000

"""

from typing import Any, Sequence, Union

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_admin_permissions(permissions: dict[str, Any]) -> dict[str, Any]:
    """Add admin.analytics without importing application config (avoids circular imports)."""
    updated = dict(permissions)
    admin = dict(updated.get('admin') or {})
    admin.setdefault('analytics', False)
    updated['admin'] = admin
    return updated


def _normalize_permissions(permissions: dict | None) -> dict | None:
    if permissions is None:
        return None
    return _ensure_admin_permissions(permissions)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # Merge admin.analytics into persisted default user permissions (config table)
    if 'config' in inspector.get_table_names():
        config_row = conn.execute(sa.text('SELECT id, data FROM config ORDER BY id DESC LIMIT 1')).fetchone()
        if config_row and config_row[1]:
            data = config_row[1]
            if isinstance(data, str):
                data = json.loads(data)

            user_section = data.get('user') or {}
            permissions = user_section.get('permissions')
            if permissions is not None:
                normalized = _normalize_permissions(permissions)
                if normalized != permissions:
                    user_section['permissions'] = normalized
                    data['user'] = user_section
                    conn.execute(
                        sa.text('UPDATE config SET data = :data WHERE id = :id'),
                        {'data': data, 'id': config_row[0]},
                    )

    # Ensure existing group permission JSON includes the new admin section
    if 'group' in inspector.get_table_names():
        groups = conn.execute(sa.text('SELECT id, permissions FROM "group" WHERE permissions IS NOT NULL')).fetchall()
        for group_id, permissions in groups:
            if not permissions:
                continue
            perms = permissions
            if isinstance(perms, str):
                perms = json.loads(perms)
            normalized = _normalize_permissions(perms)
            if normalized != perms:
                conn.execute(
                    sa.text('UPDATE "group" SET permissions = :permissions WHERE id = :id'),
                    {'permissions': normalized, 'id': group_id},
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    def _strip_admin(permissions: dict | None) -> dict | None:
        if not permissions or 'admin' not in permissions:
            return permissions
        updated = dict(permissions)
        updated.pop('admin', None)
        return updated

    if 'config' in inspector.get_table_names():
        config_row = conn.execute(sa.text('SELECT id, data FROM config ORDER BY id DESC LIMIT 1')).fetchone()
        if config_row and config_row[1]:
            data = config_row[1]
            if isinstance(data, str):
                data = json.loads(data)

            user_section = data.get('user') or {}
            permissions = user_section.get('permissions')
            if permissions and 'admin' in permissions:
                user_section['permissions'] = _strip_admin(permissions)
                data['user'] = user_section
                conn.execute(
                    sa.text('UPDATE config SET data = :data WHERE id = :id'),
                    {'data': data, 'id': config_row[0]},
                )

    if 'group' in inspector.get_table_names():
        groups = conn.execute(sa.text('SELECT id, permissions FROM "group" WHERE permissions IS NOT NULL')).fetchall()
        for group_id, permissions in groups:
            if not permissions:
                continue
            perms = permissions
            if isinstance(perms, str):
                perms = json.loads(perms)
            if 'admin' not in perms:
                continue
            conn.execute(
                sa.text('UPDATE "group" SET permissions = :permissions WHERE id = :id'),
                {'permissions': _strip_admin(perms), 'id': group_id},
            )

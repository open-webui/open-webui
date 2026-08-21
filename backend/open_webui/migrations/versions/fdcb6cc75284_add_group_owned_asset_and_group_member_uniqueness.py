"""Add group_owned_asset table

Revision ID: fdcb6cc75284
Revises: c5a8d3e2f1b0
Create Date: 2026-08-21 00:00:00.000000

Phase 2 of custom-role foundation: adds the group-owned-asset table that
tracks exactly one owning group per (resource_type, resource_id).

The historical migration ``37f288994c47`` (add_group_member_table) already
creates the ``group_member`` table with the ``uq_group_member_group_user``
unique constraint.  This migration does NOT create, drop, or modify that
constraint — it only introduces ``group_owned_asset``.

Changes:
1. group_owned_asset: new table with unique (resource_type, resource_id),
   index on group_id, CheckConstraint for supported types, and
   RESTRICT on group deletion (no cascade).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fdcb6cc75284'
down_revision: str | None = 'c5a8d3e2f1b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── group_owned_asset: new table ────────────────────────────────────
    op.create_table(
        'group_owned_asset',
        sa.Column('id', sa.Text(), nullable=False, primary_key=True),
        sa.Column('resource_type', sa.Text(), nullable=False),
        sa.Column('resource_id', sa.Text(), nullable=False),
        sa.Column(
            'group_id',
            sa.Text(),
            sa.ForeignKey('group.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        # Exactly one owner per (resource_type, resource_id)
        sa.UniqueConstraint(
            'resource_type',
            'resource_id',
            name='uq_group_owned_asset_resource',
        ),
        # Portable type allowlist enforced at DB level
        sa.CheckConstraint(
            "resource_type IN ('knowledge', 'prompt')",
            name='ck_group_owned_asset_type',
        ),
    )
    op.create_index(
        'ix_group_owned_asset_group_id',
        'group_owned_asset',
        ['group_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_group_owned_asset_group_id', table_name='group_owned_asset')
    op.drop_table('group_owned_asset')

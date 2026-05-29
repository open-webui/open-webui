"""Add workspace and workspace_member tables; add workspace_id to chat

Company custom: Team Workspaces V1
Revision ID: w001_workspace_v1
Revises: a0b1c2d3e4f5
Create Date: 2026-05-29 00:00:00.000000

Rollback: run downgrade() — drops workspace_member, workspace tables and
          removes workspace_id column from chat. No existing data is touched
          by upgrade (workspace_id is nullable, existing rows keep NULL).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'w001_workspace_v1'
down_revision: Union[str, None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- workspace table --------------------------------------------------
    op.create_table(
        'workspace',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('meta', sa.Text(), nullable=True),   # JSON stored as Text (JSONField)
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.Column('deleted_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
    )

    # -- workspace_member table -------------------------------------------
    op.create_table(
        'workspace_member',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),
    )
    op.create_index('ws_member_workspace_id_idx', 'workspace_member', ['workspace_id'])
    op.create_index('ws_member_user_id_idx', 'workspace_member', ['user_id'])

    # -- chat.workspace_id (nullable — all existing rows remain NULL) ------
    op.add_column('chat', sa.Column('workspace_id', sa.String(), nullable=True))
    op.create_index('chat_workspace_id_idx', 'chat', ['workspace_id'])


def downgrade() -> None:
    op.drop_index('chat_workspace_id_idx', table_name='chat')
    op.drop_column('chat', 'workspace_id')

    op.drop_index('ws_member_user_id_idx', table_name='workspace_member')
    op.drop_index('ws_member_workspace_id_idx', table_name='workspace_member')
    op.drop_table('workspace_member')

    op.drop_table('workspace')

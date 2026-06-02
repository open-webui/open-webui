"""Update messages and channel member table

Revision ID: 2f1211949ecc
Revises: 37f288994c47
Create Date: 2025-11-27 03:07:56.200231

"""

from typing import Sequence, Union

import open_webui.internal.db
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2f1211949ecc'
down_revision: Union[str, None] = '37f288994c47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # New columns to be added to channel_member table
    cm_cols = {c['name'] for c in inspector.get_columns('channel_member')}
    if 'status' not in cm_cols:
        op.add_column('channel_member', sa.Column('status', sa.Text(), nullable=True))
    if 'is_active' not in cm_cols:
        op.add_column(
            'channel_member',
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                default=True,
                server_default=sa.sql.expression.true(),
            ),
        )
    if 'is_channel_muted' not in cm_cols:
        op.add_column(
            'channel_member',
            sa.Column(
                'is_channel_muted',
                sa.Boolean(),
                nullable=False,
                default=False,
                server_default=sa.sql.expression.false(),
            ),
        )
    if 'is_channel_pinned' not in cm_cols:
        op.add_column(
            'channel_member',
            sa.Column(
                'is_channel_pinned',
                sa.Boolean(),
                nullable=False,
                default=False,
                server_default=sa.sql.expression.false(),
            ),
        )
    if 'data' not in cm_cols:
        op.add_column('channel_member', sa.Column('data', sa.JSON(), nullable=True))
    if 'meta' not in cm_cols:
        op.add_column('channel_member', sa.Column('meta', sa.JSON(), nullable=True))
    if 'joined_at' not in cm_cols:
        op.add_column('channel_member', sa.Column('joined_at', sa.BigInteger(), nullable=False))
    if 'left_at' not in cm_cols:
        op.add_column('channel_member', sa.Column('left_at', sa.BigInteger(), nullable=True))
    if 'last_read_at' not in cm_cols:
        op.add_column('channel_member', sa.Column('last_read_at', sa.BigInteger(), nullable=True))
    if 'updated_at' not in cm_cols:
        op.add_column('channel_member', sa.Column('updated_at', sa.BigInteger(), nullable=True))

    # New columns to be added to message table
    msg_cols = {c['name'] for c in inspector.get_columns('message')}
    if 'is_pinned' not in msg_cols:
        op.add_column(
            'message',
            sa.Column(
                'is_pinned',
                sa.Boolean(),
                nullable=False,
                default=False,
                server_default=sa.sql.expression.false(),
            ),
        )
    if 'pinned_at' not in msg_cols:
        op.add_column('message', sa.Column('pinned_at', sa.BigInteger(), nullable=True))
    if 'pinned_by' not in msg_cols:
        op.add_column('message', sa.Column('pinned_by', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('channel_member', 'updated_at')
    op.drop_column('channel_member', 'last_read_at')

    op.drop_column('channel_member', 'meta')
    op.drop_column('channel_member', 'data')

    op.drop_column('channel_member', 'is_channel_pinned')
    op.drop_column('channel_member', 'is_channel_muted')

    op.drop_column('message', 'pinned_by')
    op.drop_column('message', 'pinned_at')
    op.drop_column('message', 'is_pinned')

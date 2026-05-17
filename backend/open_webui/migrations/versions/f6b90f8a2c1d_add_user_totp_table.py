"""Add user TOTP table

Revision ID: f6b90f8a2c1d
Revises: 461111b60977
Create Date: 2026-05-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = 'f6b90f8a2c1d'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'user_totp' not in existing_tables:
        op.create_table(
            'user_totp',
            sa.Column(
                'user_id',
                sa.String(),
                sa.ForeignKey('user.id', ondelete='CASCADE'),
                nullable=False,
                primary_key=True,
            ),
            sa.Column('secret', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('backup_codes', sa.JSON(), nullable=True),
            sa.Column('last_used_at', sa.BigInteger(), nullable=True),
            sa.Column('last_used_step', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('idx_user_totp_enabled', 'user_totp', ['enabled'])


def downgrade() -> None:
    op.drop_index('idx_user_totp_enabled', table_name='user_totp')
    op.drop_table('user_totp')

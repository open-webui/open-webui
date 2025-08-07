"""Add TOTP fields to user table

Revision ID: e4f7b8c9d2a1
Revises: d31026856c01
Create Date: 2025-08-04 21:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

import open_webui.internal.db
from open_webui.internal.db import JSONField

# revision identifiers, used by Alembic.
revision: str = "e4f7b8c9d2a1"
down_revision: Union[str, None] = "d31026856c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add TOTP fields to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('totp_secret', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('totp_enabled', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('totp_backup_codes', JSONField(), nullable=True))


def downgrade() -> None:
    # Remove TOTP fields from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('totp_backup_codes')
        batch_op.drop_column('totp_enabled')
        batch_op.drop_column('totp_secret')

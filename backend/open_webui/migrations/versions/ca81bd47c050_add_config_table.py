"""Add config table

Revision ID: ca81bd47c050
Revises: 7e5b5dc7342b
Create Date: 2024-08-25 15:26:35.241684

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "ca81bd47c050"
down_revision: Union[str, None] = "7e5b5dc7342b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "config",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String,  nullable=False, server_default='system@default'),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint('email', 'version', name='_email_version_uc')
    )


def downgrade():
    op.drop_table("config")

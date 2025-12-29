"""expand tenant logo column

Revision ID: 6a50f39757df
Revises: 0b4e9ce3cb0a
Create Date: 2025-03-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "6a50f39757df"
down_revision: Union[str, None] = "0b4e9ce3cb0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.alter_column(
            "tenant",
            "logo_image_url",
            type_=mysql.MEDIUMTEXT(),
            existing_nullable=True,
        )
    else:
        op.alter_column(
            "tenant",
            "logo_image_url",
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.alter_column(
            "tenant",
            "logo_image_url",
            type_=sa.String(length=255),
            existing_nullable=True,
        )
    else:
        op.alter_column(
            "tenant",
            "logo_image_url",
            type_=sa.String(length=255),
            existing_nullable=True,
        )

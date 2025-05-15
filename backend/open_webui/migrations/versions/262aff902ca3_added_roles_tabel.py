"""Added roles tabel

Revision ID: 262aff902ca3
Revises: 9f0c9cd09105
Create Date: 2025-04-14 14:25:33.528446

"""

import time

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "262aff902ca3"
down_revision: Union[str, None] = "9f0c9cd09105"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String()),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    # Insert default roles into the database.
    current_time = int(time.time())

    connection = op.get_bind()
    connection.execute(
        sa.text(
            f"""
            INSERT INTO roles (name, created_at, updated_at) VALUES
            ('pending', {current_time}, {current_time}),
            ('admin', {current_time}, {current_time}),
            ('user', {current_time}, {current_time})
            """
        )
    )


def downgrade():
    op.drop_table("roles")

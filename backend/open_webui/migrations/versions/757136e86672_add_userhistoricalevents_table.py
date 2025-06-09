"""Add UserHistoricalEvents table

Revision ID: 757136e86672
Revises: 9f0c9cd09105
Create Date: 2025-06-09 03:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "757136e86672"
down_revision = "9f0c9cd09105"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_historical_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=True),
        sa.Column("active_at_hr", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "active_at_hr", name="uq_events_user_id_active_at_hr"
        ),
    )


def downgrade():
    op.drop_table("user_historical_events")

"""
Add attention check columns to moderation_session

Revision ID: fe12ab34cd56
Revises: cc33dd44ee55
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fe12ab34cd56"
down_revision = "cc33dd44ee55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("moderation_session") as batch_op:
        batch_op.add_column(sa.Column("is_attention_check", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))
        batch_op.add_column(sa.Column("attention_check_selected", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))
        batch_op.add_column(sa.Column("attention_check_passed", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))

    # Drop server_default after backfilling defaults
    with op.batch_alter_table("moderation_session") as batch_op:
        batch_op.alter_column("is_attention_check", server_default=None)
        batch_op.alter_column("attention_check_selected", server_default=None)
        batch_op.alter_column("attention_check_passed", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("moderation_session") as batch_op:
        batch_op.drop_column("attention_check_passed")
        batch_op.drop_column("attention_check_selected")
        batch_op.drop_column("is_attention_check")

"""Add STT credit ledger table

Revision ID: c6a3c9d4b1e2
Revises: 3e0e00844bb0
Create Date: 2025-12-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "c6a3c9d4b1e2"
down_revision = "3e0e00844bb0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stt_credit_ledger",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("credits_delta", sa.Integer(), nullable=False),
        sa.Column("free_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paid_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reference_id", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )

    op.create_index(
        "ix_stt_credit_ledger_user_id", "stt_credit_ledger", ["user_id"], unique=False
    )
    op.create_index(
        "ix_stt_credit_ledger_source", "stt_credit_ledger", ["source"], unique=False
    )
    op.create_index(
        "ix_stt_credit_ledger_reference_id",
        "stt_credit_ledger",
        ["reference_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_stt_credit_ledger_reference_id", table_name="stt_credit_ledger")
    op.drop_index("ix_stt_credit_ledger_source", table_name="stt_credit_ledger")
    op.drop_index("ix_stt_credit_ledger_user_id", table_name="stt_credit_ledger")
    op.drop_table("stt_credit_ledger")


"""Create stripe_payment_history table

Revision ID: 29c6dc90b192
Revises: 7bd38c980997
Create Date: 2025-02-19 12:29:28.487440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '29c6dc90b192'
down_revision: Union[str, None] = '7bd38c980997'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_payment_history",
        sa.Column("id", sa.String, primary_key=True, unique=True),
        sa.Column("stripe_transaction_id", sa.String, unique=True, nullable=False),
        sa.Column("company_id", sa.String, sa.ForeignKey("company.id"), nullable=False),
        sa.Column("user_id", sa.String, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("description", sa.Text, nullable=False, server_default="Standard Subscription Charge"),
        sa.Column("charged_amount", sa.DECIMAL(10, 2), nullable=False, server_default="15.00"),
        sa.Column("currency", sa.String, nullable=False, server_default="EUR"),
        sa.Column("payment_status", sa.String, nullable=False),
        sa.Column("payment_method", sa.String, nullable=True),
        sa.Column("payment_date", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("payment_metadata", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("stripe_payment_history")

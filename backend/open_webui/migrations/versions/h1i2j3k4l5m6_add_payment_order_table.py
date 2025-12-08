"""Add payment_order table

Revision ID: h1i2j3k4l5m6
Revises: 2b3c4d5e6f7g
Create Date: 2025-12-07 22:00:00.000000

添加支付订单表，用于存储用户自助充值订单信息。
"""

from alembic import op
import sqlalchemy as sa

revision = "h1i2j3k4l5m6"
down_revision = "2b3c4d5e6f7g"
branch_labels = None
depends_on = None


def upgrade():
    """创建 payment_order 表"""
    op.create_table(
        "payment_order",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("out_trade_no", sa.String(64), unique=True, nullable=False),
        sa.Column("trade_no", sa.String(64), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(20), nullable=False, server_default="alipay"),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("expired_at", sa.BigInteger(), nullable=False),
    )

    # 创建索引
    op.create_index("ix_payment_order_user_id", "payment_order", ["user_id"])
    op.create_index("ix_payment_order_out_trade_no", "payment_order", ["out_trade_no"], unique=True)
    op.create_index("ix_payment_order_status", "payment_order", ["status"])


def downgrade():
    """删除 payment_order 表"""
    op.drop_index("ix_payment_order_status", table_name="payment_order")
    op.drop_index("ix_payment_order_out_trade_no", table_name="payment_order")
    op.drop_index("ix_payment_order_user_id", table_name="payment_order")
    op.drop_table("payment_order")

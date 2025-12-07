"""Add precharge fields to billing_log

Revision ID: 240e45fa2f01
Revises: f8c9d0e4a3b2
Create Date: 2025-12-06 18:00:00.000000

添加预扣费相关字段到billing_log表：
- precharge_id: 预扣费事务ID（UUID）
- status: 记录状态（precharge | settled | refunded）
- estimated_tokens: 预估tokens总数
- refund_amount: 退款金额（毫）
"""

from alembic import op
import sqlalchemy as sa


revision = "240e45fa2f01"
down_revision = "f8c9d0e4a3b2"
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：添加预扣费字段"""
    connection = op.get_bind()
    is_sqlite = connection.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: 使用batch模式
        with op.batch_alter_table("billing_log") as batch_op:
            batch_op.add_column(sa.Column("precharge_id", sa.String(), nullable=True))
            batch_op.add_column(
                sa.Column("status", sa.String(20), nullable=True, server_default="settled")
            )
            batch_op.add_column(sa.Column("estimated_tokens", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("refund_amount", sa.Integer(), nullable=True))
            batch_op.create_index("ix_billing_log_precharge_id", ["precharge_id"])
    else:
        # PostgreSQL: 直接操作
        op.add_column("billing_log", sa.Column("precharge_id", sa.String(), nullable=True))
        op.add_column(
            "billing_log",
            sa.Column("status", sa.String(20), nullable=True, server_default="settled"),
        )
        op.add_column(
            "billing_log", sa.Column("estimated_tokens", sa.Integer(), nullable=True)
        )
        op.add_column(
            "billing_log", sa.Column("refund_amount", sa.Integer(), nullable=True)
        )
        op.create_index("ix_billing_log_precharge_id", "billing_log", ["precharge_id"])


def downgrade():
    """降级数据库：删除预扣费字段"""
    connection = op.get_bind()
    is_sqlite = connection.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("billing_log") as batch_op:
            batch_op.drop_index("ix_billing_log_precharge_id")
            batch_op.drop_column("refund_amount")
            batch_op.drop_column("estimated_tokens")
            batch_op.drop_column("status")
            batch_op.drop_column("precharge_id")
    else:
        op.drop_index("ix_billing_log_precharge_id", table_name="billing_log")
        op.drop_column("billing_log", "refund_amount")
        op.drop_column("billing_log", "estimated_tokens")
        op.drop_column("billing_log", "status")
        op.drop_column("billing_log", "precharge_id")

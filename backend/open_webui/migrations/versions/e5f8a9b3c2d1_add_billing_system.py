"""Add billing system

Revision ID: e5f8a9b3c2d1
Revises: d31026856c01
Create Date: 2025-12-05 10:00:00.000000

添加计费模块相关表和字段：
- user 表新增 balance, total_consumed, billing_status 字段
- 新增 model_pricing 表（模型定价）
- 新增 billing_log 表（计费日志）
- 新增 recharge_log 表（充值日志）
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e5f8a9b3c2d1"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：添加计费系统"""
    # 检查数据库类型
    connection = op.get_bind()
    is_postgresql = connection.dialect.name == "postgresql"

    # 根据数据库类型选择NUMERIC类型
    numeric_type = postgresql.NUMERIC(20, 6) if is_postgresql else sa.REAL

    # 1. 修改 user 表：新增计费字段
    op.add_column(
        "user",
        sa.Column(
            "balance",
            numeric_type,
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "total_consumed",
            numeric_type,
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "billing_status",
            sa.String(20),
            server_default="active",
            nullable=False,
        ),
    )

    # 2. 创建 model_pricing 表
    op.create_table(
        "model_pricing",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column(
            "input_price",
            numeric_type,
            nullable=False,
        ),
        sa.Column(
            "output_price",
            numeric_type,
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default="true" if is_postgresql else "1",
            nullable=False,
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", name="uq_model_pricing_model_id"),
    )

    # 3. 创建 billing_log 表
    op.create_table(
        "billing_log",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column(
            "prompt_tokens", sa.Integer(), server_default="0"
        ),
        sa.Column(
            "completion_tokens", sa.Integer(), server_default="0"
        ),
        sa.Column(
            "total_cost",
            numeric_type,
            nullable=False,
        ),
        sa.Column(
            "balance_after",
            numeric_type,
            nullable=True,
        ),
        sa.Column(
            "log_type",
            sa.String(20),
            server_default="deduct",
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 创建 billing_log 索引
    op.create_index(
        "idx_billing_log_user_id", "billing_log", ["user_id"], unique=False
    )
    op.create_index(
        "idx_billing_log_created_at", "billing_log", ["created_at"], unique=False
    )
    op.create_index(
        "idx_billing_log_user_created",
        "billing_log",
        ["user_id", "created_at"],
        unique=False,
    )

    # 4. 创建 recharge_log 表
    op.create_table(
        "recharge_log",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "amount",
            numeric_type,
            nullable=False,
        ),
        sa.Column("operator_id", sa.String(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 创建 recharge_log 索引
    op.create_index(
        "idx_recharge_log_user_id", "recharge_log", ["user_id"], unique=False
    )
    op.create_index(
        "idx_recharge_log_created_at", "recharge_log", ["created_at"], unique=False
    )


def downgrade():
    """降级数据库：移除计费系统"""
    # 删除索引
    op.drop_index("idx_recharge_log_created_at", "recharge_log")
    op.drop_index("idx_recharge_log_user_id", "recharge_log")
    op.drop_index("idx_billing_log_user_created", "billing_log")
    op.drop_index("idx_billing_log_created_at", "billing_log")
    op.drop_index("idx_billing_log_user_id", "billing_log")

    # 删除表
    op.drop_table("recharge_log")
    op.drop_table("billing_log")
    op.drop_table("model_pricing")

    # 删除 user 表字段
    op.drop_column("user", "billing_status")
    op.drop_column("user", "total_consumed")
    op.drop_column("user", "balance")

"""Add user_feedback table for user suggestions

Revision ID: 1c2d3e4f5a6b
Revises: f8c9d0e4a3b2
Create Date: 2025-12-07 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1c2d3e4f5a6b"
down_revision = "f8c9d0e4a3b2"
branch_labels = None
depends_on = None


def upgrade():
    # 新增 user_feedback 表：用于用户主动提交建议/反馈
    # 字段说明：
    # - id: 主键
    # - user_id: 提交用户
    # - content: 反馈正文
    # - contact: 联系方式（可选）
    # - status: 处理状态（pending/resolved）
    # - created_at/updated_at: 秒级时间戳
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("contact", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    # SQLite does not support server_default on existing rows; ensure default is set for new rows only.


def downgrade():
    # 回滚时直接删除表
    op.drop_table("user_feedback")

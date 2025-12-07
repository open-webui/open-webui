"""Merge heads for user_feedback branch and legacy head

Revision ID: 2b3c4d5e6f7g
Revises: 1c2d3e4f5a6b, b2c3d4e5f6a7
Create Date: 2025-12-07 12:10:00.000000

此迁移用于合并分叉的两个 head（user_feedback 分支与 b2c3d4e5f6a7），不做实际数据变更。
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2b3c4d5e6f7g"
down_revision = ("1c2d3e4f5a6b", "b2c3d4e5f6a7")
branch_labels = None
depends_on = None


def upgrade():
    # 纯合并迁移，无实际操作
    pass


def downgrade():
    # 回滚时仅拆分分叉
    pass

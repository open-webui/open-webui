"""Add missing username field to user table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-07 15:00:00.000000

修复 user 表字段缺失问题：
- 添加 username 字段 (String(50), nullable)

问题来源：
- username 字段在模型中存在但从未通过迁移添加
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：添加 username 字段"""
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)

    # 获取 user 表的现有列
    existing_columns = {col['name'] for col in inspector.get_columns('user')}

    # 添加 username 字段（仅当不存在时）
    if "username" not in existing_columns:
        op.add_column("user", sa.Column("username", sa.String(50), nullable=True))


def downgrade():
    """降级数据库：删除 username 字段"""
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)

    # 获取 user 表的现有列
    existing_columns = {col['name'] for col in inspector.get_columns('user')}

    # 删除 username 字段（仅当存在时）
    if "username" in existing_columns:
        op.drop_column("user", "username")

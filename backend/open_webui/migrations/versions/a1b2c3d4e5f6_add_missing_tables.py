"""Add missing tables (announcement, user_model_credential, message)

Revision ID: a1b2c3d4e5f6
Revises: 240e45fa2f01
Create Date: 2025-12-07 14:00:00.000000

补充以下表的迁移（这些表之前通过手动建表方式创建）：
- announcement: 公告主表
- announcement_read: 公告阅读记录表
- user_model_credential: 用户私有模型凭据表
- message: 消息表
- message_reaction: 消息反应表

注意：此迁移会检查表是否已存在，仅创建不存在的表，兼容手动建表的环境。
"""

from alembic import op
import sqlalchemy as sa
from open_webui.internal.db import JSONField
from open_webui.migrations.util import get_existing_tables


revision = "a1b2c3d4e5f6"
down_revision = "240e45fa2f01"
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：创建缺失的表"""
    connection = op.get_bind()
    is_sqlite = connection.dialect.name == "sqlite"
    existing_tables = set(get_existing_tables())

    # 1. 创建 announcement 表
    if "announcement" not in existing_tables:
        op.create_table(
            "announcement",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.Column("meta", JSONField(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        # 创建索引
        op.create_index("idx_announcement_status", "announcement", ["status"])
        op.create_index("idx_announcement_created_at", "announcement", ["created_at"])

    # 2. 创建 announcement_read 表
    if "announcement_read" not in existing_tables:
        op.create_table(
            "announcement_read",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("announcement_id", sa.Text(), nullable=False),
            sa.Column("read_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        # 创建索引
        op.create_index("idx_announcement_read_user", "announcement_read", ["user_id"])
        op.create_index(
            "idx_announcement_read_announcement", "announcement_read", ["announcement_id"]
        )
        op.create_index(
            "idx_announcement_read_unique",
            "announcement_read",
            ["user_id", "announcement_id"],
            unique=True,
        )

    # 3. 创建 user_model_credential 表
    if "user_model_credential" not in existing_tables:
        op.create_table(
            "user_model_credential",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("model_id", sa.String(), nullable=False),
            sa.Column("base_url", sa.Text(), nullable=True),
            sa.Column("api_key", sa.Text(), nullable=False),
            sa.Column("config", JSONField(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        # 创建索引
        op.create_index(
            "ix_user_model_credential_user_id", "user_model_credential", ["user_id"]
        )

    # 4. 创建 message 表
    if "message" not in existing_tables:
        op.create_table(
            "message",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("channel_id", sa.Text(), nullable=True),
            sa.Column("reply_to_id", sa.Text(), nullable=True),
            sa.Column("parent_id", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("data", JSONField(), nullable=True),
            sa.Column("meta", JSONField(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # 5. 创建 message_reaction 表
    if "message_reaction" not in existing_tables:
        op.create_table(
            "message_reaction",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("message_id", sa.Text(), nullable=True),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade():
    """降级数据库：删除表"""
    # 按照依赖关系逆序删除

    # 1. 删除 message_reaction 表
    op.drop_table("message_reaction")

    # 2. 删除 message 表
    op.drop_table("message")

    # 3. 删除 user_model_credential 表（先删除索引）
    op.drop_index("ix_user_model_credential_user_id", "user_model_credential")
    op.drop_table("user_model_credential")

    # 4. 删除 announcement_read 表（先删除索引）
    op.drop_index("idx_announcement_read_unique", "announcement_read")
    op.drop_index("idx_announcement_read_announcement", "announcement_read")
    op.drop_index("idx_announcement_read_user", "announcement_read")
    op.drop_table("announcement_read")

    # 5. 删除 announcement 表（先删除索引）
    op.drop_index("idx_announcement_created_at", "announcement")
    op.drop_index("idx_announcement_status", "announcement")
    op.drop_table("announcement")

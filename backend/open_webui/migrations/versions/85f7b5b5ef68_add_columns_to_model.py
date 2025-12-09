"""add_columns_to_model

Revision ID: 85f7b5b5ef68
Revises: h1i2j3k4l5m6
Create Date: 2025-12-09 11:19:15.576715

"""

# 验证示例（手动执行，不会在迁移中运行）:
# python -c "
# from open_webui.internal.db import get_db
# from sqlalchemy import inspect
# with get_db() as db:
#     insp = inspect(db.bind)
#     cols = insp.get_columns('model')
#     names = [c['name'] for c in cols]
#     print('model columns:', names)
# "


from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from open_webui.internal.db import JSONField

# revision identifiers, used by Alembic.
revision: str = "85f7b5b5ef68"
down_revision: Union[str, None] = "h1i2j3k4l5m6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 model 表添加 UI/分组/排序相关字段，并为 provider 建索引。"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {col["name"] for col in inspector.get_columns("model")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("model")}

    if "icon_url" not in existing_cols:
        op.add_column("model", sa.Column("icon_url", sa.Text(), nullable=True))

    if "provider" not in existing_cols:
        op.add_column("model", sa.Column("provider", sa.String(length=50), nullable=True))
    if "idx_model_provider" not in existing_indexes:
        op.create_index("idx_model_provider", "model", ["provider"])

    if "description" not in existing_cols:
        op.add_column("model", sa.Column("description", sa.Text(), nullable=True))

    if "context_length" not in existing_cols:
        op.add_column(
            "model",
            sa.Column(
                "context_length",
                sa.Integer(),
                nullable=False,
                server_default="4096",
            ),
        )

    if "tags" not in existing_cols:
        op.add_column("model", sa.Column("tags", JSONField(), nullable=True))

    if "sort_order" not in existing_cols:
        op.add_column(
            "model",
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {col["name"] for col in inspector.get_columns("model")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("model")}

    if "idx_model_provider" in existing_indexes:
        op.drop_index("idx_model_provider", table_name="model")

    if "provider" in existing_cols:
        op.drop_column("model", "provider")
    if "icon_url" in existing_cols:
        op.drop_column("model", "icon_url")
    if "description" in existing_cols:
        op.drop_column("model", "description")
    if "context_length" in existing_cols:
        op.drop_column("model", "context_length")
    if "tags" in existing_cols:
        op.drop_column("model", "tags")
    if "sort_order" in existing_cols:
        op.drop_column("model", "sort_order")

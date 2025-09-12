"""Add noteplus table

Revision ID: add_noteplus_table
Revises: 3af16a1c9fb6
Create Date: 2025-08-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_noteplus_table"
down_revision = "3af16a1c9fb6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "noteplus",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("category_major", sa.Text(), nullable=True),  # 대분류
        sa.Column("category_middle", sa.Text(), nullable=True),  # 중분류
        sa.Column("category_minor", sa.Text(), nullable=True),  # 소분류
        sa.Column("access_control", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )
    
    # Create indexes for better category search performance
    op.create_index("idx_noteplus_category_major", "noteplus", ["category_major"])
    op.create_index("idx_noteplus_category_middle", "noteplus", ["category_middle"])
    op.create_index("idx_noteplus_category_minor", "noteplus", ["category_minor"])
    op.create_index("idx_noteplus_user_id", "noteplus", ["user_id"])


def downgrade():
    op.drop_index("idx_noteplus_user_id", "noteplus")
    op.drop_index("idx_noteplus_category_minor", "noteplus")
    op.drop_index("idx_noteplus_category_middle", "noteplus")
    op.drop_index("idx_noteplus_category_major", "noteplus")
    op.drop_table("noteplus")
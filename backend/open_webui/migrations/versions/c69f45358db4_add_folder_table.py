"""Add folder table

Revision ID: c69f45358db4
Revises: 3ab32c4b8f59
Create Date: 2024-10-16 02:02:35.241684

"""

from alembic import op
import sqlalchemy as sa

revision = "c69f45358db4"
down_revision = "3ab32c4b8f59"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "folder",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("is_expanded", sa.Boolean(), default=False, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", "user_id"),
    )

    op.add_column(
        "chat",
        sa.Column("folder_id", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("chat", "folder_id")

    op.drop_table("folder")

"""Simplify moderation tables

Revision ID: bb22cc33dd44
Revises: b9d4578a786b
Create Date: 2025-10-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "bb22cc33dd44"
down_revision = "b9d4578a786b"
branch_labels = None
depends_on = None


def upgrade():
    # moderation_session table safety-create if missing
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "moderation_session" not in inspector.get_table_names():
        op.create_table(
            "moderation_session",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("child_id", sa.Text(), nullable=False),
            sa.Column("scenario_prompt", sa.Text(), nullable=False),
            sa.Column("original_response", sa.Text(), nullable=False),
            sa.Column("strategies", sa.JSON(), nullable=True),
            sa.Column("custom_instructions", sa.JSON(), nullable=True),
            sa.Column("highlighted_texts", sa.JSON(), nullable=True),
            sa.Column("refactored_response", sa.Text(), nullable=True),
            sa.Column("session_metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_moderation_session_user_id", "moderation_session", ["user_id"])
        op.create_index("idx_moderation_session_child_id", "moderation_session", ["child_id"]) 
        op.create_index("idx_moderation_session_created_at", "moderation_session", ["created_at"]) 


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "moderation_session" in inspector.get_table_names():
        op.drop_index("idx_moderation_session_created_at", table_name="moderation_session")
        op.drop_index("idx_moderation_session_child_id", table_name="moderation_session")
        op.drop_index("idx_moderation_session_user_id", table_name="moderation_session")
        op.drop_table("moderation_session")



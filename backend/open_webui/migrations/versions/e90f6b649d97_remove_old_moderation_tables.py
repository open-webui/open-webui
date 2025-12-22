"""remove_old_moderation_tables

Revision ID: e90f6b649d97
Revises: 01e073659718
Create Date: 2025-12-22 14:17:51.217733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'e90f6b649d97'
down_revision: Union[str, None] = '01e073659718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove old moderation tables that have been replaced by moderation_session.
    
    These tables are no longer used:
    - moderation_question_answer
    - moderation_applied
    - moderation_scenario
    
    Migration is idempotent - checks for table existence before dropping.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop moderation_question_answer table and its indexes
    if "moderation_question_answer" in existing_tables:
        # Drop indexes first
        try:
            op.drop_index("idx_mqa_answered_at", table_name="moderation_question_answer")
        except Exception:
            pass  # Index may not exist
        try:
            op.drop_index("idx_mqa_scenario_id", table_name="moderation_question_answer")
        except Exception:
            pass  # Index may not exist
        # Drop table
        op.drop_table("moderation_question_answer")
    
    # Drop moderation_applied table and its indexes
    if "moderation_applied" in existing_tables:
        # Drop indexes first
        try:
            op.drop_index("idx_mapplied_confirmed", table_name="moderation_applied")
        except Exception:
            pass  # Index may not exist
        try:
            op.drop_index("idx_mapplied_scenario_id", table_name="moderation_applied")
        except Exception:
            pass  # Index may not exist
        # Drop table
        op.drop_table("moderation_applied")
    
    # Drop moderation_scenario table and its indexes
    if "moderation_scenario" in existing_tables:
        # Drop indexes first
        try:
            op.drop_index("idx_mscenario_created_at", table_name="moderation_scenario")
        except Exception:
            pass  # Index may not exist
        try:
            op.drop_index("idx_mscenario_child_id", table_name="moderation_scenario")
        except Exception:
            pass  # Index may not exist
        try:
            op.drop_index("idx_mscenario_user_id", table_name="moderation_scenario")
        except Exception:
            pass  # Index may not exist
        # Drop table
        op.drop_table("moderation_scenario")


def downgrade() -> None:
    """
    Recreate the old moderation tables (for rollback purposes).
    Note: This recreates empty tables - data will be lost.
    """
    # Recreate moderation_scenario table
    op.create_table(
        "moderation_scenario",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("child_id", sa.Text(), nullable=False),
        sa.Column("scenario_prompt", sa.Text(), nullable=False),
        sa.Column("original_response", sa.Text(), nullable=False),
        sa.Column("is_applicable", sa.Boolean(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("idx_mscenario_user_id", "moderation_scenario", ["user_id"])
    op.create_index("idx_mscenario_child_id", "moderation_scenario", ["child_id"])
    op.create_index("idx_mscenario_created_at", "moderation_scenario", ["created_at"])
    
    # Recreate moderation_applied table
    op.create_table(
        "moderation_applied",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("version_index", sa.Integer(), nullable=False),
        sa.Column("strategies", sa.Text(), nullable=False),
        sa.Column("custom_instructions", sa.Text(), nullable=False),
        sa.Column("highlighted_texts", sa.Text(), nullable=False),
        sa.Column("refactored_response", sa.Text(), nullable=False),
        sa.Column("confirmed_preferred", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("idx_mapplied_scenario_id", "moderation_applied", ["scenario_id"])
    op.create_index("idx_mapplied_confirmed", "moderation_applied", ["confirmed_preferred"])
    
    # Recreate moderation_question_answer table
    op.create_table(
        "moderation_question_answer",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("question_key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("answered_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("idx_mqa_scenario_id", "moderation_question_answer", ["scenario_id"])
    op.create_index("idx_mqa_answered_at", "moderation_question_answer", ["answered_at"])

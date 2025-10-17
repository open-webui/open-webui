"""Add moderation tables and selection source

Revision ID: ab12cd34ef56
Revises: 018012973d35
Create Date: 2025-10-17 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "ab12cd34ef56"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    # moderation_scenario
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

    # selection: add scenario_id, source
    with op.batch_alter_table("selection") as batch_op:
        batch_op.add_column(sa.Column("scenario_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source", sa.Text(), nullable=True))  # 'prompt' | 'response'
    op.create_index("idx_selection_scenario_id", "selection", ["scenario_id"]) 
    op.create_index("idx_selection_source", "selection", ["source"]) 

    # moderation_applied
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

    # moderation_question_answer
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


def downgrade():
    op.drop_index("idx_mqa_answered_at", table_name="moderation_question_answer")
    op.drop_index("idx_mqa_scenario_id", table_name="moderation_question_answer")
    op.drop_table("moderation_question_answer")

    op.drop_index("idx_mapplied_confirmed", table_name="moderation_applied")
    op.drop_index("idx_mapplied_scenario_id", table_name="moderation_applied")
    op.drop_table("moderation_applied")

    op.drop_index("idx_selection_source", table_name="selection")
    op.drop_index("idx_selection_scenario_id", table_name="selection")
    with op.batch_alter_table("selection") as batch_op:
        batch_op.drop_column("source")
        batch_op.drop_column("scenario_id")

    op.drop_index("idx_mscenario_created_at", table_name="moderation_scenario")
    op.drop_index("idx_mscenario_child_id", table_name="moderation_scenario")
    op.drop_index("idx_mscenario_user_id", table_name="moderation_scenario")
    op.drop_table("moderation_scenario")



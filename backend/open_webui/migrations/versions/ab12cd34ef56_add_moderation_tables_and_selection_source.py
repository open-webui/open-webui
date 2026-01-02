"""Add moderation tables and selection source

Revision ID: ab12cd34ef56
Revises: 018012973d35
Create Date: 2025-10-17 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision = "ab12cd34ef56"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # moderation_scenario
    if "moderation_scenario" not in existing_tables:
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
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_scenario")]
        indexes_to_create = [
            ("idx_mscenario_user_id", ["user_id"]),
            ("idx_mscenario_child_id", ["child_id"]),
            ("idx_mscenario_created_at", ["created_at"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "moderation_scenario", columns)

    # selection: add scenario_id, source
    if "selection" in existing_tables:
        selection_columns = [col["name"] for col in inspector.get_columns("selection")]
        with op.batch_alter_table("selection") as batch_op:
            if "scenario_id" not in selection_columns:
                batch_op.add_column(sa.Column("scenario_id", sa.Text(), nullable=True))
            if "source" not in selection_columns:
                batch_op.add_column(sa.Column("source", sa.Text(), nullable=True))  # 'prompt' | 'response'
        
        # Check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("selection")]
        if "idx_selection_scenario_id" not in existing_indexes:
            op.create_index("idx_selection_scenario_id", "selection", ["scenario_id"]) 
        if "idx_selection_source" not in existing_indexes:
            op.create_index("idx_selection_source", "selection", ["source"])

    # moderation_applied
    if "moderation_applied" not in existing_tables:
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
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_applied")]
        indexes_to_create = [
            ("idx_mapplied_scenario_id", ["scenario_id"]),
            ("idx_mapplied_confirmed", ["confirmed_preferred"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "moderation_applied", columns)

    # moderation_question_answer
    if "moderation_question_answer" not in existing_tables:
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
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_question_answer")]
        indexes_to_create = [
            ("idx_mqa_scenario_id", ["scenario_id"]),
            ("idx_mqa_answered_at", ["answered_at"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "moderation_question_answer", columns)


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "moderation_question_answer" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_question_answer")]
        if "idx_mqa_answered_at" in existing_indexes:
            op.drop_index("idx_mqa_answered_at", table_name="moderation_question_answer")
        if "idx_mqa_scenario_id" in existing_indexes:
            op.drop_index("idx_mqa_scenario_id", table_name="moderation_question_answer")
        op.drop_table("moderation_question_answer")

    if "moderation_applied" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_applied")]
        if "idx_mapplied_confirmed" in existing_indexes:
            op.drop_index("idx_mapplied_confirmed", table_name="moderation_applied")
        if "idx_mapplied_scenario_id" in existing_indexes:
            op.drop_index("idx_mapplied_scenario_id", table_name="moderation_applied")
        op.drop_table("moderation_applied")

    if "selection" in existing_tables:
        selection_columns = [col["name"] for col in inspector.get_columns("selection")]
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("selection")]
        if "idx_selection_source" in existing_indexes:
            op.drop_index("idx_selection_source", table_name="selection")
        if "idx_selection_scenario_id" in existing_indexes:
            op.drop_index("idx_selection_scenario_id", table_name="selection")
        with op.batch_alter_table("selection") as batch_op:
            if "source" in selection_columns:
                batch_op.drop_column("source")
            if "scenario_id" in selection_columns:
                batch_op.drop_column("scenario_id")

    if "moderation_scenario" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_scenario")]
        if "idx_mscenario_created_at" in existing_indexes:
            op.drop_index("idx_mscenario_created_at", table_name="moderation_scenario")
        if "idx_mscenario_child_id" in existing_indexes:
            op.drop_index("idx_mscenario_child_id", table_name="moderation_scenario")
        if "idx_mscenario_user_id" in existing_indexes:
            op.drop_index("idx_mscenario_user_id", table_name="moderation_scenario")
        op.drop_table("moderation_scenario")


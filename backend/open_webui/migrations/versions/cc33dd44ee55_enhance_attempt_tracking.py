"""Enhance attempt/version tracking across tables

Revision ID: cc33dd44ee55
Revises: bb22cc33dd44
Create Date: 2025-10-22 08:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = "cc33dd44ee55"
down_revision = "bb22cc33dd44"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # moderation_session: add iteration/version tracking fields
    if "moderation_session" in existing_tables:
        moderation_session_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
        columns_to_add = [
            ("scenario_index", sa.Integer(), "0"),
            ("attempt_number", sa.Integer(), "1"),
            ("version_number", sa.Integer(), "0"),
            ("initial_decision", sa.Text(), None),
            ("is_final_version", sa.Boolean(), False),
        ]
        
        # Add columns one at a time to avoid circular dependency
        for col_name, col_type, default in columns_to_add:
            if col_name not in moderation_session_columns:
                if default is not None:
                    if isinstance(default, (str, int)):
                        op.add_column("moderation_session", sa.Column(col_name, col_type, nullable=False, server_default=str(default)))
                    elif isinstance(default, bool):
                        op.add_column("moderation_session", sa.Column(col_name, col_type, nullable=False, server_default=sa.text(str(default).lower())))
                    else:
                        op.add_column("moderation_session", sa.Column(col_name, col_type, nullable=False, server_default=default))
                else:
                    op.add_column("moderation_session", sa.Column(col_name, col_type, nullable=True))
        
        # Check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_session")]
        if "idx_mod_session_composite" not in existing_indexes:
            op.create_index(
                "idx_mod_session_composite",
                "moderation_session",
                ["user_id", "child_id", "scenario_index", "attempt_number"],
            )
        if "idx_mod_session_final" not in existing_indexes:
            op.create_index(
                "idx_mod_session_final",
                "moderation_session",
                ["user_id", "child_id", "is_final_version"],
            )

    # child_profile: add attempt tracking and current flag
    if "child_profile" in existing_tables:
        child_profile_columns = [col["name"] for col in inspector.get_columns("child_profile")]
        columns_to_add = [
            ("attempt_number", sa.Integer(), "1"),
            ("is_current", sa.Boolean(), True),
        ]
        
        # Add columns one at a time
        for col_name, col_type, default in columns_to_add:
            if col_name not in child_profile_columns:
                if isinstance(default, (str, int)):
                    op.add_column("child_profile", sa.Column(col_name, col_type, nullable=False, server_default=str(default)))
                elif isinstance(default, bool):
                    op.add_column("child_profile", sa.Column(col_name, col_type, nullable=False, server_default=sa.text(str(default).lower())))
                else:
                    op.add_column("child_profile", sa.Column(col_name, col_type, nullable=False, server_default=default))
        
        # Check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("child_profile")]
        if "idx_child_profile_user_current" not in existing_indexes:
            op.create_index(
                "idx_child_profile_user_current",
                "child_profile",
                ["user_id", "is_current"],
            )
        if "idx_child_profile_attempt" not in existing_indexes:
            op.create_index(
                "idx_child_profile_attempt",
                "child_profile",
                ["user_id", "id", "attempt_number"],
            )

    # exit_quiz_response: add attempt tracking and current flag
    if "exit_quiz_response" in existing_tables:
        exit_quiz_columns = [col["name"] for col in inspector.get_columns("exit_quiz_response")]
        columns_to_add = [
            ("attempt_number", sa.Integer(), "1"),
            ("is_current", sa.Boolean(), True),
        ]
        
        # Add columns one at a time
        for col_name, col_type, default in columns_to_add:
            if col_name not in exit_quiz_columns:
                if isinstance(default, (str, int)):
                    op.add_column("exit_quiz_response", sa.Column(col_name, col_type, nullable=False, server_default=str(default)))
                elif isinstance(default, bool):
                    op.add_column("exit_quiz_response", sa.Column(col_name, col_type, nullable=False, server_default=sa.text(str(default).lower())))
                else:
                    op.add_column("exit_quiz_response", sa.Column(col_name, col_type, nullable=False, server_default=default))
        
        # Check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("exit_quiz_response")]
        if "idx_exit_quiz_attempt" not in existing_indexes:
            op.create_index(
                "idx_exit_quiz_attempt",
                "exit_quiz_response",
                ["user_id", "child_id", "attempt_number"],
            )
        if "idx_exit_quiz_user_current" not in existing_indexes:
            op.create_index(
                "idx_exit_quiz_user_current",
                "exit_quiz_response",
                ["user_id", "is_current"],
            )


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # exit_quiz_response
    if "exit_quiz_response" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("exit_quiz_response")]
        exit_quiz_columns = [col["name"] for col in inspector.get_columns("exit_quiz_response")]
        if "idx_exit_quiz_user_current" in existing_indexes:
            op.drop_index("idx_exit_quiz_user_current", table_name="exit_quiz_response")
        if "idx_exit_quiz_attempt" in existing_indexes:
            op.drop_index("idx_exit_quiz_attempt", table_name="exit_quiz_response")
        if "is_current" in exit_quiz_columns:
            op.drop_column("exit_quiz_response", "is_current")
        if "attempt_number" in exit_quiz_columns:
            op.drop_column("exit_quiz_response", "attempt_number")

    # child_profile
    if "child_profile" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("child_profile")]
        child_profile_columns = [col["name"] for col in inspector.get_columns("child_profile")]
        if "idx_child_profile_attempt" in existing_indexes:
            op.drop_index("idx_child_profile_attempt", table_name="child_profile")
        if "idx_child_profile_user_current" in existing_indexes:
            op.drop_index("idx_child_profile_user_current", table_name="child_profile")
        if "is_current" in child_profile_columns:
            op.drop_column("child_profile", "is_current")
        if "attempt_number" in child_profile_columns:
            op.drop_column("child_profile", "attempt_number")

    # moderation_session
    if "moderation_session" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_session")]
        moderation_session_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
        if "idx_mod_session_final" in existing_indexes:
            op.drop_index("idx_mod_session_final", table_name="moderation_session")
        if "idx_mod_session_composite" in existing_indexes:
            op.drop_index("idx_mod_session_composite", table_name="moderation_session")
        if "is_final_version" in moderation_session_columns:
            op.drop_column("moderation_session", "is_final_version")
        if "initial_decision" in moderation_session_columns:
            op.drop_column("moderation_session", "initial_decision")
        if "version_number" in moderation_session_columns:
            op.drop_column("moderation_session", "version_number")
        if "attempt_number" in moderation_session_columns:
            op.drop_column("moderation_session", "attempt_number")
        if "scenario_index" in moderation_session_columns:
            op.drop_column("moderation_session", "scenario_index")

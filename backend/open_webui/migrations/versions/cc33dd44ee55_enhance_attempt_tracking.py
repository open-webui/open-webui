"""Enhance attempt/version tracking across tables

Revision ID: cc33dd44ee55
Revises: bb22cc33dd44
Create Date: 2025-10-22 08:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "cc33dd44ee55"
down_revision = "bb22cc33dd44"
branch_labels = None
depends_on = None


def upgrade():
    # moderation_session: add iteration/version tracking fields
    with op.batch_alter_table("moderation_session") as batch_op:
        batch_op.add_column(sa.Column("scenario_index", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("version_number", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("initial_decision", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("is_final_version", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))

    op.create_index(
        "idx_mod_session_composite",
        "moderation_session",
        ["user_id", "child_id", "scenario_index", "attempt_number"],
    )
    op.create_index(
        "idx_mod_session_final",
        "moderation_session",
        ["user_id", "child_id", "is_final_version"],
    )

    # child_profile: add attempt tracking and current flag
    with op.batch_alter_table("child_profile") as batch_op:
        batch_op.add_column(sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))

    op.create_index(
        "idx_child_profile_user_current",
        "child_profile",
        ["user_id", "is_current"],
    )
    op.create_index(
        "idx_child_profile_attempt",
        "child_profile",
        ["user_id", "id", "attempt_number"],
    )

    # exit_quiz_response: add attempt tracking and current flag
    with op.batch_alter_table("exit_quiz_response") as batch_op:
        batch_op.add_column(sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))

    op.create_index(
        "idx_exit_quiz_attempt",
        "exit_quiz_response",
        ["user_id", "child_id", "attempt_number"],
    )
    op.create_index(
        "idx_exit_quiz_user_current",
        "exit_quiz_response",
        ["user_id", "is_current"],
    )


def downgrade():
    # exit_quiz_response
    op.drop_index("idx_exit_quiz_user_current", table_name="exit_quiz_response")
    op.drop_index("idx_exit_quiz_attempt", table_name="exit_quiz_response")
    with op.batch_alter_table("exit_quiz_response") as batch_op:
        batch_op.drop_column("is_current")
        batch_op.drop_column("attempt_number")

    # child_profile
    op.drop_index("idx_child_profile_attempt", table_name="child_profile")
    op.drop_index("idx_child_profile_user_current", table_name="child_profile")
    with op.batch_alter_table("child_profile") as batch_op:
        batch_op.drop_column("is_current")
        batch_op.drop_column("attempt_number")

    # moderation_session
    op.drop_index("idx_mod_session_final", table_name="moderation_session")
    op.drop_index("idx_mod_session_composite", table_name="moderation_session")
    with op.batch_alter_table("moderation_session") as batch_op:
        batch_op.drop_column("is_final_version")
        batch_op.drop_column("initial_decision")
        batch_op.drop_column("version_number")
        batch_op.drop_column("attempt_number")
        batch_op.drop_column("scenario_index")


























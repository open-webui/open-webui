"""add_prolific_session_support

Revision ID: dd44ee55ff66
Revises: cc33dd44ee55
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'dd44ee55ff66'
down_revision = 'cc33dd44ee55'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # Add Prolific fields to user table
    if "user" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("user")]
        columns_to_add = [
            ("prolific_pid", sa.String()),
            ("study_id", sa.String()),
            ("current_session_id", sa.String()),
            ("session_number", sa.BigInteger()),
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in user_columns:
                if col_name == "session_number":
                    op.add_column('user', sa.Column(col_name, col_type, nullable=False, server_default='1'))
                else:
                    op.add_column('user', sa.Column(col_name, col_type, nullable=True))
        
        # Check if unique constraint exists
        existing_constraints = inspector.get_unique_constraints("user")
        if not any(constraint["name"] == "uq_user_prolific_pid" for constraint in existing_constraints):
            # Add unique constraint for prolific_pid (use batch mode for SQLite compatibility)
            with op.batch_alter_table('user') as batch_op:
                batch_op.create_unique_constraint('uq_user_prolific_pid', ['prolific_pid'])
    
    # Add session_number to moderation_session table
    if "moderation_session" in existing_tables:
        moderation_session_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
        if "session_number" not in moderation_session_columns:
            op.add_column('moderation_session', sa.Column('session_number', sa.BigInteger(), nullable=False, server_default='1'))
        
        # Check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_session")]
        if "idx_mod_session_composite" in existing_indexes:
            op.drop_index('idx_mod_session_composite', table_name='moderation_session')
        if "idx_mod_session_composite" not in existing_indexes:
            op.create_index('idx_mod_session_composite', 'moderation_session', ['user_id', 'child_id', 'scenario_index', 'attempt_number', 'session_number'])
        
        if "idx_mod_session_user_session" not in existing_indexes:
            op.create_index('idx_mod_session_user_session', 'moderation_session', ['user_id', 'session_number'])


def downgrade():
    # Check if columns/indexes exist before removing
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # Remove new indexes
    if "moderation_session" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("moderation_session")]
        if "idx_mod_session_user_session" in existing_indexes:
            op.drop_index('idx_mod_session_user_session', table_name='moderation_session')
        if "idx_mod_session_composite" in existing_indexes:
            op.drop_index('idx_mod_session_composite', table_name='moderation_session')
        moderation_session_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
        if "session_number" in moderation_session_columns:
            op.drop_column('moderation_session', 'session_number')
    
    if "user" in existing_tables:
        existing_constraints = inspector.get_unique_constraints("user")
        if any(constraint["name"] == "uq_user_prolific_pid" for constraint in existing_constraints):
            with op.batch_alter_table('user') as batch_op:
                batch_op.drop_constraint('uq_user_prolific_pid', type_='unique')
        user_columns = [col["name"] for col in inspector.get_columns("user")]
        columns_to_drop = ["session_number", "current_session_id", "study_id", "prolific_pid"]
        for col_name in columns_to_drop:
            if col_name in user_columns:
                op.drop_column('user', col_name)

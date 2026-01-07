"""Add scenario_assignments table for assignment tracking

Revision ID: n99o00p11q22
Revises: m88n99o00p11
Create Date: 2025-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'n99o00p11q22'
down_revision = 'm88n99o00p11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "scenario_assignments" not in existing_tables:
        op.create_table(
            'scenario_assignments',
            sa.Column('assignment_id', sa.String(), nullable=False, primary_key=True),
            sa.Column('participant_id', sa.String(), nullable=False),  # user_id
            sa.Column('scenario_id', sa.String(), nullable=False),
            sa.Column('child_profile_id', sa.String(), nullable=True),
            
            # Status tracking
            sa.Column('status', sa.String(), nullable=False),  # 'assigned', 'started', 'completed', 'skipped', 'abandoned'
            
            # Timestamps
            sa.Column('assigned_at', sa.BigInteger(), nullable=False),
            sa.Column('started_at', sa.BigInteger(), nullable=True),
            sa.Column('ended_at', sa.BigInteger(), nullable=True),
            
            # Sampling audit fields
            sa.Column('alpha', sa.Float(), nullable=True),  # Weighted sampling alpha parameter
            sa.Column('eligible_pool_size', sa.Integer(), nullable=True),
            sa.Column('n_assigned_before', sa.Integer(), nullable=True),  # n_assigned at time of assignment
            sa.Column('weight', sa.Float(), nullable=True),  # Calculated weight
            sa.Column('sampling_prob', sa.Float(), nullable=True),  # Realized sampling probability
            sa.Column('assignment_position', sa.Integer(), nullable=True),  # Position in session (0-indexed)
            
            # Outcome fields
            sa.Column('issue_any', sa.Integer(), nullable=True),  # 0, 1, or NULL
            sa.Column('skip_stage', sa.String(), nullable=True),  # Stage where skip occurred
            sa.Column('skip_reason', sa.String(), nullable=True),  # Reason code for skip
            sa.Column('skip_reason_text', sa.Text(), nullable=True),  # Optional text explanation
        )
        
        # Create indexes for efficient querying
        op.create_index('idx_assignments_participant_id', 'scenario_assignments', ['participant_id'])
        op.create_index('idx_assignments_scenario_id', 'scenario_assignments', ['scenario_id'])
        op.create_index('idx_assignments_status', 'scenario_assignments', ['status'])
        op.create_index('idx_assignments_assigned_at', 'scenario_assignments', ['assigned_at'])
        op.create_index('idx_assignments_participant_scenario', 'scenario_assignments', ['participant_id', 'scenario_id'])
        
        # Note: Foreign key constraint not created for SQLite compatibility
        # SQLite doesn't support ALTER TABLE ADD CONSTRAINT
        # Foreign key relationship is enforced at application level
        
        # Note: Partial unique constraint for (participant_id, scenario_id) WHERE status IN ('completed', 'skipped')
        # SQLite doesn't support partial unique indexes, so we'll enforce this in application logic
        # For PostgreSQL, we could use:
        # op.create_index(
        #     'idx_assignments_unique_completed_skipped',
        #     'scenario_assignments',
        #     ['participant_id', 'scenario_id'],
        #     unique=True,
        #     postgresql_where=sa.text("status IN ('completed', 'skipped')")
        # )


def downgrade() -> None:
    op.drop_index('idx_assignments_participant_scenario', table_name='scenario_assignments')
    op.drop_index('idx_assignments_assigned_at', table_name='scenario_assignments')
    op.drop_index('idx_assignments_status', table_name='scenario_assignments')
    op.drop_index('idx_assignments_scenario_id', table_name='scenario_assignments')
    op.drop_index('idx_assignments_participant_id', table_name='scenario_assignments')
    op.drop_table('scenario_assignments')


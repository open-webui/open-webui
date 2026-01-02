"""add_participant_name_to_consent_audit

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "consent_audit" in existing_tables:
        consent_audit_columns = [col["name"] for col in inspector.get_columns("consent_audit")]
        if "participant_name" not in consent_audit_columns:
            op.add_column('consent_audit', sa.Column('participant_name', sa.String(), nullable=True))


def downgrade():
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "consent_audit" in existing_tables:
        consent_audit_columns = [col["name"] for col in inspector.get_columns("consent_audit")]
        if "participant_name" in consent_audit_columns:
            op.drop_column('consent_audit', 'participant_name')

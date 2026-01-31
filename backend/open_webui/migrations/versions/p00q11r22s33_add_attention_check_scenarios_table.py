"""Add attention_check_scenarios table

Revision ID: p00q11r22s33
Revises: ae8bccdc8e36
Create Date: 2026-01-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "p00q11r22s33"
down_revision = "ae8bccdc8e36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "attention_check_scenarios" not in existing_tables:
        op.create_table(
            "attention_check_scenarios",
            sa.Column("scenario_id", sa.String(), nullable=False, primary_key=True),
            sa.Column("prompt_text", sa.Text(), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=False),
            # Metadata fields (matching CSV structure)
            sa.Column("trait_theme", sa.String(), nullable=True),
            sa.Column("trait_phrase", sa.String(), nullable=True),
            sa.Column("sentiment", sa.String(), nullable=True),
            sa.Column("trait_index", sa.Integer(), nullable=True),
            sa.Column("prompt_index", sa.Integer(), nullable=True),
            # Management fields
            sa.Column("set_name", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("source", sa.String(), nullable=True),
            # Timestamps
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

        # Create indexes for efficient querying
        op.create_index(
            "idx_ac_scenarios_is_active", "attention_check_scenarios", ["is_active"]
        )
        op.create_index(
            "idx_ac_scenarios_set_name", "attention_check_scenarios", ["set_name"]
        )
        op.create_index(
            "idx_ac_scenarios_trait_theme", "attention_check_scenarios", ["trait_theme"]
        )


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "attention_check_scenarios" in existing_tables:
        # Drop indexes first
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("attention_check_scenarios")
        ]
        if "idx_ac_scenarios_trait_theme" in existing_indexes:
            op.drop_index(
                "idx_ac_scenarios_trait_theme", table_name="attention_check_scenarios"
            )
        if "idx_ac_scenarios_set_name" in existing_indexes:
            op.drop_index(
                "idx_ac_scenarios_set_name", table_name="attention_check_scenarios"
            )
        if "idx_ac_scenarios_is_active" in existing_indexes:
            op.drop_index(
                "idx_ac_scenarios_is_active", table_name="attention_check_scenarios"
            )

        # Drop table
        op.drop_table("attention_check_scenarios")

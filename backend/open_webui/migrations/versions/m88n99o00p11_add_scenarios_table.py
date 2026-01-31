"""Add scenarios table for scenario tracking

Revision ID: m88n99o00p11
Revises: l67m78n89o90
Create Date: 2025-01-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "m88n99o00p11"
down_revision = "l67m78n89o90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "scenarios" not in existing_tables:
        op.create_table(
            "scenarios",
            sa.Column("scenario_id", sa.String(), nullable=False, primary_key=True),
            sa.Column("prompt_text", sa.Text(), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=False),
            # Metadata fields
            sa.Column(
                "set_name", sa.String(), nullable=True
            ),  # 'pilot', 'scaled', etc.
            sa.Column(
                "trait", sa.String(), nullable=True
            ),  # 'Agreeableness', 'Conscientiousness', etc.
            sa.Column(
                "polarity", sa.String(), nullable=True
            ),  # 'positive', 'negative', 'neutral'
            sa.Column(
                "prompt_style", sa.String(), nullable=True
            ),  # 'Journalistic', 'Should I', etc.
            sa.Column(
                "domain", sa.String(), nullable=True
            ),  # 'Internet Interaction', 'Self', etc.
            sa.Column("is_validated", sa.Boolean(), nullable=False, server_default="0"),
            # Source tracking fields
            sa.Column(
                "source", sa.String(), nullable=True
            ),  # 'json_file', 'api_generated', 'manual'
            sa.Column(
                "model_name", sa.String(), nullable=True
            ),  # Model that produced the response
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default="1"
            ),  # Whether to show to users
            # Counters
            sa.Column("n_assigned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("n_completed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("n_skipped", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("n_abandoned", sa.Integer(), nullable=False, server_default="0"),
            # Timestamps
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

        # Create indexes for efficient querying
        op.create_index("idx_scenarios_set_name", "scenarios", ["set_name"])
        op.create_index("idx_scenarios_is_validated", "scenarios", ["is_validated"])
        op.create_index("idx_scenarios_trait", "scenarios", ["trait"])
        op.create_index("idx_scenarios_polarity", "scenarios", ["polarity"])
        op.create_index("idx_scenarios_is_active", "scenarios", ["is_active"])
        op.create_index("idx_scenarios_source", "scenarios", ["source"])
        op.create_index("idx_scenarios_n_assigned", "scenarios", ["n_assigned"])


def downgrade() -> None:
    op.drop_index("idx_scenarios_n_assigned", table_name="scenarios")
    op.drop_index("idx_scenarios_source", table_name="scenarios")
    op.drop_index("idx_scenarios_is_active", table_name="scenarios")
    op.drop_index("idx_scenarios_polarity", table_name="scenarios")
    op.drop_index("idx_scenarios_trait", table_name="scenarios")
    op.drop_index("idx_scenarios_is_validated", table_name="scenarios")
    op.drop_index("idx_scenarios_set_name", table_name="scenarios")
    op.drop_table("scenarios")

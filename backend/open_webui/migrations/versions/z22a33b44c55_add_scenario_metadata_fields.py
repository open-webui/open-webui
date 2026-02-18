"""Add scenario metadata fields for pilot_scenarios JSON format

Revision ID: z22a33b44c55
Revises: y11z22a33b44
Create Date: 2026-02-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "z22a33b44c55"
down_revision: Union[str, None] = "y11z22a33b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "scenarios" not in existing_tables:
        return

    existing_columns = [col["name"] for col in inspector.get_columns("scenarios")]

    new_columns = [
        ("persona_id", sa.String(), True),
        ("age_band", sa.String(), True),
        ("gender_identity", sa.String(), True),
        ("context", sa.Text(), True),
        ("piaget_stage", sa.String(), True),
        ("trait_level", sa.String(), True),
        ("intent", sa.String(), True),
        ("subdomain", sa.String(), True),
        ("safety_notes", sa.Text(), True),
    ]

    for col_name, col_type, nullable in new_columns:
        if col_name not in existing_columns:
            op.add_column(
                "scenarios",
                sa.Column(col_name, col_type, nullable=nullable),
            )

    # Create indexes for frequently queried fields
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("scenarios")]
    for idx_name, col in [
        ("idx_scenarios_age_band", "age_band"),
        ("idx_scenarios_gender_identity", "gender_identity"),
        ("idx_scenarios_piaget_stage", "piaget_stage"),
    ]:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "scenarios", [col])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "scenarios" not in existing_tables:
        return

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("scenarios")]
    for idx_name in [
        "idx_scenarios_piaget_stage",
        "idx_scenarios_gender_identity",
        "idx_scenarios_age_band",
    ]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name="scenarios")

    existing_columns = [col["name"] for col in inspector.get_columns("scenarios")]
    for col_name in [
        "safety_notes",
        "subdomain",
        "intent",
        "trait_level",
        "piaget_stage",
        "context",
        "gender_identity",
        "age_band",
        "persona_id",
    ]:
        if col_name in existing_columns:
            op.drop_column("scenarios", col_name)

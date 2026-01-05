"""Add tenant help text column populated from default markdown

Revision ID: 7bd26b4a8c12
Revises: 6a50f39757df
Create Date: 2025-03-20 00:00:00.000000

"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision: str = "7bd26b4a8c12"
down_revision: Union[str, None] = "6a50f39757df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HELP_FILE_PATH = (
    Path(__file__).resolve().parents[2] / "static" / "help" / "default.md"
)


def _load_default_help_text() -> str:
    if not HELP_FILE_PATH.exists():
        raise RuntimeError(
            f"Default help markdown not found at {HELP_FILE_PATH}"
        )
    return HELP_FILE_PATH.read_text(encoding="utf-8")


def upgrade() -> None:
    help_text_type = sa.Text().with_variant(MEDIUMTEXT, "mysql")

    op.add_column(
        "tenant",
        sa.Column("help_text", help_text_type, nullable=True),
    )

    default_help_text = _load_default_help_text()
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE tenant SET help_text = :default_text"),
        {"default_text": default_help_text},
    )

    op.alter_column(
        "tenant",
        "help_text",
        existing_type=help_text_type,
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("tenant", "help_text")

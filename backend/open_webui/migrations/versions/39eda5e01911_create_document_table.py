"""create document table

Revision ID: 39eda5e01911
Revises: 76be63986ba6
Create Date: 2025-02-16 18:41:41.985188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '39eda5e01911'
down_revision: Union[str, None] = '76be63986ba6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "documentdb",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("file_name", sa.String()),
        sa.Column("file_id", sa.String()),
        sa.Column("collection_name", sa.String()),
        sa.Column("page_content", sa.Text()),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("documentdb")

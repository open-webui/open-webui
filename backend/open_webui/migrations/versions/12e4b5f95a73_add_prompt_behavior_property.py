"""add prompt_behavior property

Revision ID: 12e4b5f95a73
Revises: 242a2047eae0
Create Date: 2024-10-11 20:51:56.211753

"""
import enum
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '12e4b5f95a73'
down_revision: Union[str, None] = '242a2047eae0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type
    prompt_behavior_enum = postgresql.ENUM('inline', 'once-pinned', name='promptbehavior')
    prompt_behavior_enum.create(op.get_bind())

    # Add the column using the created enum type
    op.add_column("prompt", sa.Column("behavior", sa.Enum('inline', 'once-pinned', name='promptbehavior'), nullable=False, server_default='inline'))

def downgrade() -> None:
    # Drop the column
    op.drop_column("prompt", "behavior")

    # Drop the enum type
    prompt_behavior_enum = postgresql.ENUM('inline', 'once-pinned', name='promptbehavior')
    prompt_behavior_enum.drop(op.get_bind())

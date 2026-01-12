"""add hanyang user fields (department, user_status)

Revision ID: add_hanyang_user_fields
Revises: add_chapter_id_to_chat
Create Date: 2026-01-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_hanyang_user_fields"
down_revision: Union[str, None] = "add_tool_validation_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add department (소속) - e.g., "에듀테크혁신팀", "컴퓨터소프트웨어학부"
    op.add_column("user", sa.Column("department", sa.Text(), nullable=True))
    # Add user_status (상세 신분) - e.g., "학사", "석사", "박사", "교수", "직원"
    op.add_column("user", sa.Column("user_status", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "department")
    op.drop_column("user", "user_status")

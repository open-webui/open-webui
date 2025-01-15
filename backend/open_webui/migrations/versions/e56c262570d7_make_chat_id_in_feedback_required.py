"""make_chat_id_in_feedback_required

Revision ID: e56c262570d7
Revises: 96dcb0b3212f
Create Date: 2025-01-13 08:18:51.348376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

revision: str = 'e56c262570d7'
down_revision: Union[str, None] = '96dcb0b3212f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Check if there are feedbacks with NULL chat_ids, if not, make chat_id required
    conn = op.get_bind()
    feedback = sa.table('feedback', sa.column('chat_id', sa.Text))
    result = conn.execute(sa.select(feedback).where(feedback.c.chat_id.is_(None)))
    
    if result.first() is not None:
        raise Exception(
            "There are feedbacks with NULL chat_ids. Previous migration failed."
        )
    
    with op.batch_alter_table('feedback') as batch_op:
        batch_op.alter_column('chat_id',
                            existing_type=sa.Text(),
                            nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('feedback') as batch_op:
        batch_op.alter_column('chat_id',
                            existing_type=sa.Text(),
                            nullable=True)

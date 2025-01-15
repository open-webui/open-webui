"""migrate_chat_id_in_feedback

Revision ID: 96dcb0b3212f
Revises: 790ecce592df
Create Date: 2025-01-13 08:08:22.582335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

revision: str = '96dcb0b3212f'
down_revision: Union[str, None] = '790ecce592df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Migrate chat_id data from meta to new chat_id column
    conn = op.get_bind()
    feedback = sa.table(
        'feedback',
        sa.column('id', sa.String),
        sa.column('chat_id', sa.Text),
        sa.column('meta', sa.JSON)
    )
    
    result = conn.execute(
        sa.select(feedback.c.id, feedback.c.meta)
        .where(sa.and_(
            feedback.c.chat_id.is_(None),
            feedback.c.meta.isnot(None)
        ))
    )
    
    for row in result:
        if row.meta and 'chat_id' in row.meta:
            chat_id = row.meta['chat_id']
            conn.execute(
                feedback.update()
                .where(feedback.c.id == row.id)
                .values(chat_id=chat_id)
            )


def downgrade() -> None:
    pass

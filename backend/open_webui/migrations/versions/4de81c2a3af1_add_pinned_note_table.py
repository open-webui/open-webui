"""add pinned_note table

Revision ID: 4de81c2a3af1
Revises: 56359461a091
Create Date: 2026-05-09 04:29:27.651341

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '4de81c2a3af1'
down_revision: Union[str, None] = '56359461a091'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import uuid
import time
from sqlalchemy import select, update, insert
from sqlalchemy.sql import table, column


def upgrade() -> None:
    op.create_table(
        'pinned_note',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('note_id', sa.Text(), sa.ForeignKey('note.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'note_id', name='uq_pinned_note'),
    )

    conn = op.get_bind()

    note_table = table('note', column('id', sa.Text), column('user_id', sa.Text), column('is_pinned', sa.Boolean))

    pinned_note_table = table(
        'pinned_note',
        column('id', sa.Text),
        column('user_id', sa.Text),
        column('note_id', sa.Text),
        column('created_at', sa.BigInteger),
    )

    notes = conn.execute(select(note_table.c.id, note_table.c.user_id).where(note_table.c.is_pinned == True)).fetchall()

    if notes:
        now = int(time.time_ns())
        conn.execute(
            insert(pinned_note_table),
            [{'id': str(uuid.uuid4()), 'user_id': note[1], 'note_id': note[0], 'created_at': now} for note in notes],
        )

    with op.batch_alter_table('note', schema=None) as batch_op:
        batch_op.drop_column('is_pinned')


def downgrade() -> None:
    with op.batch_alter_table('note', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_pinned', sa.Boolean(), nullable=True))

    conn = op.get_bind()

    note_table = table('note', column('id', sa.Text), column('is_pinned', sa.Boolean))

    pinned_note_table = table('pinned_note', column('note_id', sa.Text))

    notes = conn.execute(select(pinned_note_table.c.note_id)).fetchall()

    for note in notes:
        conn.execute(update(note_table).where(note_table.c.id == note[0]).values(is_pinned=True))

    op.drop_table('pinned_note')

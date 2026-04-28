"""add calendar tables

Revision ID: 56359461a091
Revises: c1d2e3f4a5b6
Create Date: 2026-04-19 16:20:58.162045

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56359461a091'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create index if it does not exist
    result = conn.execute(sa.text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename='calendar' AND indexname='ix_calendar_user'"
    ))
    if result.fetchone() is None:
        op.create_index('ix_calendar_user', 'calendar', ['user_id'], unique=False)

    # Create calendar_event table if it does not exist
    if not conn.dialect.has_table(conn, 'calendar_event'):
        op.create_table(
            'calendar_event',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('calendar_id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('start_at', sa.BigInteger(), nullable=False),
            sa.Column('end_at', sa.BigInteger(), nullable=True),
            sa.Column('all_day', sa.Boolean(), nullable=False),
            sa.Column('rrule', sa.Text(), nullable=True),
            sa.Column('color', sa.Text(), nullable=True),
            sa.Column('location', sa.Text(), nullable=True),
            sa.Column('data', sa.JSON(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('is_cancelled', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )

    # Create indexes if they do not exist
    result = conn.execute(sa.text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename='calendar_event' AND indexname='ix_calendar_event_calendar'"
    ))
    if result.fetchone() is None:
        op.create_index(
            'ix_calendar_event_calendar',
            'calendar_event',
            ['calendar_id', 'start_at'],
            unique=False,
        )

    result = conn.execute(sa.text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename='calendar_event' AND indexname='ix_calendar_event_user_date'"
    ))
    if result.fetchone() is None:
        op.create_index(
            'ix_calendar_event_user_date',
            'calendar_event',
            ['user_id', 'start_at'],
            unique=False,
        )

    # Create calendar_event_attendee table if it does not exist
    if not conn.dialect.has_table(conn, 'calendar_event_attendee'):
        op.create_table(
            'calendar_event_attendee',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('event_id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('status', sa.Text(), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('event_id', 'user_id', name='uq_event_attendee'),
        )

    # Create index if it does not exist
    result = conn.execute(sa.text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename='calendar_event_attendee' "
        "AND indexname='ix_calendar_event_attendee_user'"
    ))
    if result.fetchone() is None:
        op.create_index(
            'ix_calendar_event_attendee_user',
            'calendar_event_attendee',
            ['user_id', 'status'],
            unique=False,
        )

def downgrade() -> None:
    op.drop_index('ix_calendar_event_attendee_user', table_name='calendar_event_attendee')
    op.drop_table('calendar_event_attendee')
    op.drop_index('ix_calendar_event_user_date', table_name='calendar_event')
    op.drop_index('ix_calendar_event_calendar', table_name='calendar_event')
    op.drop_table('calendar_event')
    op.drop_index('ix_calendar_user', table_name='calendar')
    op.drop_table('calendar')

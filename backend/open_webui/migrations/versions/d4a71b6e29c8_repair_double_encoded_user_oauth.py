"""Repair double-encoded user.oauth values

Revision ID: d4a71b6e29c8
Revises: 1ce6ade7d93b
Create Date: 2026-08-04 12:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op

revision = 'd4a71b6e29c8'
down_revision = '1ce6ade7d93b'
branch_labels = None
depends_on = None

_user = sa.table('user', sa.column('id', sa.Text), sa.column('oauth', sa.JSON))


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.select(_user.c.id, _user.c.oauth).where(_user.c.oauth.is_not(None))).fetchall()

    for uid, oauth in rows:
        # b10670c03dd5 used to serialize this column twice, leaving a JSON string instead of an object
        if isinstance(oauth, str):
            conn.execute(sa.update(_user).where(_user.c.id == uid).values(oauth=json.loads(oauth)))


def downgrade():
    pass

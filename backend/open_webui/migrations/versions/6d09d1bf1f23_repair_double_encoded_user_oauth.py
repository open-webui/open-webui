"""repair double encoded user oauth

Revision ID: 6d09d1bf1f23
Revises: 1ce6ade7d93b
Create Date: 2026-08-10 23:20:20.374826

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '6d09d1bf1f23'
down_revision: Union[str, None] = '1ce6ade7d93b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_user = sa.table(
    'user',
    sa.column('id', sa.Text),
    sa.column('oauth', sa.JSON),
)


def _decode_json_object(value: str) -> dict | None:
    try:
        decoded = json.loads(value)
    except Exception:
        return None
    return decoded if isinstance(decoded, dict) else None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'user' not in inspector.get_table_names():
        return

    user_columns = {c['name'] for c in inspector.get_columns('user')}
    if 'oauth' not in user_columns:
        return

    rows = conn.execute(sa.select(_user.c.id, _user.c.oauth).where(_user.c.oauth.is_not(None))).fetchall()

    for uid, oauth in rows:
        if not isinstance(oauth, str):
            continue

        decoded = _decode_json_object(oauth)
        if decoded is None:
            continue

        conn.execute(sa.update(_user).where(_user.c.id == uid).values(oauth=decoded))


def downgrade() -> None:
    pass

"""normalize user oauth sub to text

Revision ID: b7e4c19a2f83
Revises: e2b7a4c91f05
Create Date: 2026-08-15 19:40:11.204517

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4c19a2f83'
down_revision: Union[str, None] = 'e2b7a4c91f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_user = sa.table(
    'user',
    sa.column('id', sa.Text),
    sa.column('oauth', sa.JSON),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'user' not in inspector.get_table_names():
        return
    if 'oauth' not in {c['name'] for c in inspector.get_columns('user')}:
        return

    rows = conn.execute(sa.select(_user.c.id, _user.c.oauth).where(_user.c.oauth.is_not(None))).fetchall()

    for uid, oauth in rows:
        if not isinstance(oauth, dict):
            continue

        updated = {}
        changed = False
        for provider, entry in oauth.items():
            sub = entry.get('sub') if isinstance(entry, dict) else None
            if sub is None or isinstance(sub, str):
                updated[provider] = entry
                continue
            updated[provider] = {**entry, 'sub': str(sub)}
            changed = True

        if changed:
            conn.execute(sa.update(_user).where(_user.c.id == uid).values(oauth=updated))


def downgrade() -> None:
    pass
